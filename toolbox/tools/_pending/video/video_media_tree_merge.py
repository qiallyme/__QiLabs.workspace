import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

NUM_RE = re.compile(r"(\d+)")

def nsort_key(p: Path):
    # Natural sort: split digits so 0000, 0012, 0024… order correctly
    parts = NUM_RE.split(p.stem)
    return [int(s) if s.isdigit() else s.lower() for s in parts] + [p.suffix.lower()]

def run(cmd, timeout=300):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"

def check_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        code, out = run([tool, "-version"])
        if code != 0:
            sys.exit(f"[!] {tool} not found on PATH. Install ffmpeg and try again.")
    return True

def detect_available_encoders():
    """Detect which hardware encoders are available"""
    code, out = run(["ffmpeg", "-hide_banner", "-encoders"])
    if code != 0:
        return {"cpu": "libx264"}  # fallback
    
    encoders = {"cpu": "libx264"}  # always available
    
    # Check for NVIDIA NVENC
    if "h264_nvenc" in out:
        encoders["nvidia"] = "h264_nvenc"
    
    # Check for Intel Quick Sync
    if "h264_qsv" in out:
        encoders["intel"] = "h264_qsv"
    
    # Check for AMD AMF
    if "h264_amf" in out:
        encoders["amd"] = "h264_amf"
    
    return encoders

def test_encoder(encoder_name, verbose=False):
    """Test if an encoder actually works"""
    if verbose:
        print(f"[i] Testing encoder: {encoder_name}")
    
    test_cmd = [
        "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=duration=0.1:size=160x120:rate=1",
        "-c:v", encoder_name,
        "-t", "0.05",  # Very short test
        "-f", "null", "-"
    ]
    code, out = run(test_cmd)
    if verbose:
        print(f"[i] {encoder_name}: {'✓' if code == 0 else '✗'}")
    return code == 0

def encode_with_fallback(input_file, output_file, vf_arg, encoder, preset, quality_param, crf_value, verbose=False):
    """Try encoding with the specified encoder, fallback to CPU if it fails"""
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(input_file),
        "-map", "0",
        "-vf", vf_arg,
        "-c:v", encoder,
        "-preset", preset,
        quality_param, str(crf_value),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_file)
    ]
    
    if verbose:
        print(f"[i] Encoding with {encoder}...")
    
    code, out = run(cmd)
    
    # If encoding failed and we're not already using CPU, try CPU fallback
    if code != 0 and encoder != "libx264":
        if verbose:
            print(f"[!] {encoder} failed, falling back to CPU encoding...")
        
        # Retry with CPU encoder
        cmd_cpu = [
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(input_file),
            "-map", "0",
            "-vf", vf_arg,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(crf_value),
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_file)
        ]
        
        code, out = run(cmd_cpu)
        if code == 0 and verbose:
            print("[i] CPU fallback encoding succeeded")
    
    return code, out

def unique_name(base: str, root: Path, ext: str):
    # ensure unique filename in root
    candidate = root / f"{base}{ext}"
    if not candidate.exists():
        return candidate
    i = 2
    while True:
        cand = root / f"{base}__{i}{ext}"
        if not cand.exists():
            return cand
        i += 1

def write_concat_list(paths, list_path: Path):
    with list_path.open("w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{p.as_posix()}'\n")

def has_media_chunks(dir_path: Path):
    return any(p.suffix.lower() == ".media" for p in dir_path.glob("*.media"))

def gather_media_chunks(dir_path: Path):
    return sorted([p for p in dir_path.glob("*.media")], key=nsort_key)

def main():
    ap = argparse.ArgumentParser(description="Merge per-subfolder .media chunks, convert to MP4, move outputs to root.")
    ap.add_argument("root", help="Root folder to scan")
    ap.add_argument("--filters", choices=["on", "off"], default="off", help="Apply light cleanup filters (requires re-encoding)")
    ap.add_argument("--crf", default="20", help="Quality setting for re-encoding (18–23 sweet spot)")
    ap.add_argument("--preset", default="auto", help="Encoder preset for re-encoding (auto, p1-p7 for NVENC, ultrafast-veryslow for x264)")
    ap.add_argument("--encoder", choices=["auto", "nvidia", "intel", "amd", "cpu"], default="auto", help="Force specific encoder for re-encoding")
    ap.add_argument("--skip-test", action="store_true", help="Skip encoder testing (faster startup)")
    ap.add_argument("--verbose", action="store_true", help="Show detailed progress")
    ap.add_argument("--dry-run", action="store_true", help="Show actions only")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        sys.exit(f"[!] Root folder not found: {root}")

    check_ffmpeg()
    
    print("[i] Detecting available encoders...")
    available_encoders = detect_available_encoders()
    if args.verbose:
        print(f"[i] Found encoders: {list(available_encoders.keys())}")
    
    if args.encoder == "auto":
        print("[i] Auto-selecting best encoder...")
        selected_encoder = None
        encoder_type = None
        
        # Try encoders in order: NVIDIA > Intel > AMD > CPU
        encoder_candidates = [
            ("nvidia", "h264_nvenc"),
            ("intel", "h264_qsv"), 
            ("amd", "h264_amf"),
            ("cpu", "libx264")
        ]
        
        for enc_type, enc_name in encoder_candidates:
            if enc_type in available_encoders:
                if args.skip_test:
                    selected_encoder = enc_name
                    encoder_type = enc_type
                    break
                else:
                    if test_encoder(enc_name, args.verbose):
                        selected_encoder = enc_name
                        encoder_type = enc_type
                        break
                    else:
                        print(f"[!] {enc_type.upper()} encoder test failed, trying next...")
        
        # Fallback to CPU if nothing worked
        if not selected_encoder:
            selected_encoder = "libx264"
            encoder_type = "cpu"
            print("[!] All GPU encoders failed, using CPU fallback")
    else:
        # User specified encoder
        if args.encoder in available_encoders:
            selected_encoder = available_encoders[args.encoder]
            encoder_type = args.encoder
            if not args.skip_test and encoder_type != "cpu":
                print(f"[i] Testing {encoder_type} encoder...")
                if not test_encoder(selected_encoder, args.verbose):
                    print(f"[!] {encoder_type} encoder test failed, falling back to CPU")
                    selected_encoder = "libx264"
                    encoder_type = "cpu"
        else:
            print(f"[!] Requested encoder '{args.encoder}' not available. Available: {list(available_encoders.keys())}")
            selected_encoder = "libx264"
            encoder_type = "cpu"
    
    # Set appropriate preset and quality parameter
    if encoder_type == "nvidia":
        quality_param = "-cq"
        if args.preset == "auto":
            preset = "p5"
        else:
            preset = args.preset
    elif encoder_type == "intel":
        quality_param = "-global_quality"
        if args.preset == "auto":
            preset = "medium"
        else:
            preset = args.preset
    elif encoder_type == "amd":
        quality_param = "-quality"
        if args.preset == "auto":
            preset = "balanced"
        else:
            preset = args.preset
    else:  # CPU
        quality_param = "-crf"
        if args.preset == "auto":
            preset = "medium"
        else:
            preset = args.preset
    
    if args.filters == "on":
        print(f"[i] Using {encoder_type.upper()} encoder: {selected_encoder} (preset: {preset}) - RE-ENCODING with filters")
    else:
        print(f"[i] Using stream copy (no re-encoding) - FASTEST option")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = root / f"_merge_log_{timestamp}.txt"
    actions = []

    # Walk all subdirs under root (excluding root itself)
    subdirs = [p for p in root.rglob("*") if p.is_dir() and p != root]

    for sub in sorted(subdirs):
        if not has_media_chunks(sub):
            continue

        chunks = gather_media_chunks(sub)
        if len(chunks) == 0:
            continue

        # Name base: <relative_path_flat>__<timestamp>
        # e.g. "10_03_1759549681_0602__20251010-134200"
        rel = sub.relative_to(root).as_posix().replace("/", "_")
        base = f"{rel}__{timestamp}"

        out_mp4 = unique_name(base, root, ".mp4")

        actions.append(f"[+] Found {len(chunks)} chunks in {sub}")
        actions.append(f"    -> mp4:    {out_mp4.name}")

        if args.dry_run:
            continue

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            list_file = td / "list.txt"
            write_concat_list(chunks, list_file)

            # Direct merge from .media chunks to .mp4
            if args.filters == "on":
                # Apply light filters if requested (requires re-encoding)
                vf = [
                    "format=yuv420p",
                    "eq=gamma=1.03:contrast=1.05:brightness=0.00:saturation=1.02",
                    "unsharp=3:3:0.2:3:3:0.0",
                    "atadenoise=0.2:0.2:6:6"
                ]
                vf_arg = ",".join(vf)
                
                # Merge and apply filters in one step
                cmd_merge = [
                    "ffmpeg", "-hide_banner", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-fflags", "+genpts",
                    "-vf", vf_arg,
                    "-c:v", selected_encoder,
                    "-preset", preset,
                    quality_param, str(args.crf),
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    str(out_mp4)
                ]
            else:
                # No filters - direct stream copy (fastest)
                cmd_merge = [
                    "ffmpeg", "-hide_banner", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-fflags", "+genpts",
                    "-c", "copy",  # Copy streams without re-encoding
                    "-movflags", "+faststart",
                    str(out_mp4)
                ]
            
            code, out = run(cmd_merge)
            if code != 0:
                # Fallback: convert each chunk to MP4 first, then concat
                actions.append(f"    ! direct concat failed. Converting chunks to MP4 first in {sub}.")
                inter_list = td / "inter_list.txt"
                inter_files = []
                for i, clip in enumerate(chunks):
                    inter = td / f"clip_{i:04d}.mp4"
                    # Convert .media to .mp4 using stream copy (no re-encoding)
                    cmd_convert = [
                        "ffmpeg", "-hide_banner", "-y",
                        "-i", str(clip),
                        "-c", "copy",  # Copy streams without re-encoding
                        "-movflags", "+faststart",
                        str(inter)
                    ]
                    c2, o2 = run(cmd_convert)
                    if c2 != 0:
                        sys.exit(f"[!] Convert failed on {clip}\n\n{o2}")
                    inter_files.append(inter)
                write_concat_list(inter_files, inter_list)
                
                # Now concat the MP4 files
                if args.filters == "on":
                    # Apply filters during final concat
                    cmd_merge = [
                        "ffmpeg", "-hide_banner", "-y",
                        "-f", "concat", "-safe", "0",
                        "-i", str(inter_list),
                        "-vf", vf_arg,
                        "-c:v", selected_encoder,
                        "-preset", preset,
                        quality_param, str(args.crf),
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        str(out_mp4)
                    ]
                else:
                    # Just concat with stream copy
                    cmd_merge = [
                        "ffmpeg", "-hide_banner", "-y",
                        "-f", "concat", "-safe", "0",
                        "-i", str(inter_list),
                        "-c", "copy",
                        "-movflags", "+faststart",
                        str(out_mp4)
                    ]
                
                code, out = run(cmd_merge)
                if code != 0:
                    sys.exit(f"[!] Fallback concat failed in {sub}\n\n{out}")
        
        if code != 0:
            sys.exit(f"[!] MP4 creation failed for {sub}\n\n{out}")

    # Write log
    with log_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(actions) if actions else "No .media chunks found.\n")

    if actions:
        print("\n".join(actions))
        print(f"\n[✓] Done. Log: {log_path}")
    else:
        print("[i] Nothing to do. No .media files found under given root.")

if __name__ == "__main__":
    main()
