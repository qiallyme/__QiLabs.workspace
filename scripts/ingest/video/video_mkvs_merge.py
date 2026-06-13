import os
import re
import sys
import json
import time
import shutil
import datetime
import subprocess
from pathlib import Path

# ---------------------------
# Config: tweak if you must
# ---------------------------
TARGET_HEIGHT = 1080          # normalize to 1080p
TARGET_FPS = 30               # normalize framerate
CRF = 20                      # visual quality (lower = better; 18-23 sane)
PRESET = "slow"               # x264 speed/quality tradeoff: ultrafast..placebo
AUDIO_BITRATE = "192k"
# ---------------------------

VIDEO_EXTS = {".mkv", ".mp4", ".mov", ".avi", ".wmv", ".m4v", ".webm", ".mts", ".m2ts", ".ts", ".3gp"}

def have(cmd):
    from shutil import which
    return which(cmd) is not None

def natural_key(s: str):
    # Natural sort so clip2 comes before clip10
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def probe(path: Path):
    try:
        cmd = ["ffprobe", "-v", "error",
               "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate,pix_fmt,codec_name",
               "-of", "json", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(r.stdout)
        s = data.get("streams", [{}])[0]
        return {
            "width": int(s.get("width") or 0),
            "height": int(s.get("height") or 0),
            "r_frame_rate": s.get("r_frame_rate") or "0/0",
            "pix_fmt": s.get("pix_fmt") or "",
            "codec": s.get("codec_name") or "",
        }
    except Exception:
        return {"width":0, "height":0, "r_frame_rate":"0/0", "pix_fmt":"", "codec":""}

def normalize_one(src: Path, dst: Path):
    """
    Re-encode to uniform, concat-friendly stream:
      - H.264 video, yuv420p, 1080p tall, 30 fps
      - AAC audio 192k
      - Lanczos scaling
    """
    vf = f"scale=-2:{TARGET_HEIGHT}:flags=lanczos,fps={TARGET_FPS},format=yuv420p"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-movflags", "+faststart",
        str(dst)
    ]
    subprocess.run(cmd, check=True)

def concat_many(list_file: Path, out_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path)
    ]
    subprocess.run(cmd, check=True)

def main():
    if not have("ffmpeg") or not have("ffprobe"):
        print("Install FFmpeg (ffmpeg + ffprobe) and add them to PATH.")
        sys.exit(1)

    folder_in = input("Folder with your media files: ").strip().strip('"')
    if not folder_in:
        print("I need a folder path, not psychic vibes.")
        sys.exit(1)

    root = Path(folder_in)
    if not root.is_dir():
        print("That path is not a folder. Try again.")
        sys.exit(1)

    # Collect media files in the top level only (no recursion). Sort naturally.
    files = sorted(
        [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS],
        key=lambda p: natural_key(p.name)
    )
    if not files:
        print("No media files found here. Try a different folder.")
        sys.exit(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    norm_dir = root / f"_normalized_{ts}"
    norm_dir.mkdir(exist_ok=True)

    print(f"\nNormalizing {len(files)} file(s) to MKV H.264/AAC @ {TARGET_HEIGHT}p{TARGET_FPS} in:\n{norm_dir}\n")

    normalized = []
    for idx, src in enumerate(files, 1):
        dst = norm_dir / f"{idx:04d}_{src.stem}.mkv"
        try:
            normalize_one(src, dst)
        except subprocess.CalledProcessError as e:
            print(f"\nFailed on: {src.name}\n{e}\nStopping.")
            sys.exit(1)
        normalized.append(dst)
        print(f"[{idx}/{len(files)}] -> {dst.name}")

    # Build concat list
    list_path = norm_dir / "mylist.txt"
    with list_path.open("w", encoding="utf-8") as f:
        for p in normalized:
            # Use absolute paths to be safe
            f.write(f"file '{str(p).replace('\\', '/')}'\n")

    # Final combined output in the original folder
    out_path = root / f"combined_{ts}.mkv"
    print("\nConcatenating normalized files...")
    try:
        concat_many(list_path, out_path)
    except subprocess.CalledProcessError as e:
        print("\nConcat failed. Details:\n", e)
        sys.exit(1)

    # Housekeeping: keep the normalized folder so you have the per-file outputs if needed.
    print(f"\nDone. Combined file:\n{out_path}\n")
    print(f"Normalized pieces kept here (delete if you don’t need them):\n{norm_dir}")

if __name__ == "__main__":
    main()
