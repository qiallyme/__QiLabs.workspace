import os
import shlex
import subprocess
import datetime
import json
import sys

def which(cmd):
    from shutil import which as _which
    return _which(cmd) is not None

def ffprobe_resolution(path):
    """Return (width, height) using ffprobe, or (None, None) if unknown."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json", path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        stream = data.get("streams", [{}])[0]
        return stream.get("width"), stream.get("height")
    except Exception:
        return None, None

def build_filter_chain(width, height):
    """
    Conservative, natural-looking chain:
      - hqdn3d: light denoise to kill sensor and lighting noise
      - unsharp: tiny crisp back to avoid soapiness
      - eq: slight contrast & saturation lift
      - scale (if needed): upscale to 1080p with lanczos, maintain aspect
    """
    vf_parts = [
        "hqdn3d=1.5:1.5:6:6",
        "unsharp=5:5:1.0",
        "eq=contrast=1.08:saturation=1.08"  # tiny bump, not neon
    ]

    # Only upscale if shorter than 1080p. Keep width divisible by 2.
    if height and isinstance(height, int) and height < 1080:
        vf_parts.append("scale=-2:1080:flags=lanczos")

    return ",".join(vf_parts)

def prettify():
    # Safety checks for ffmpeg/ffprobe
    if not which("ffmpeg") or not which("ffprobe"):
        print("FFmpeg/ffprobe not found. Install them and make sure they're on your PATH.")
        sys.exit(1)

    src = input("Drop your video path here: ").strip().strip('"').strip()
    if not src:
        print("You gave me nothing. Try again with an actual file.")
        return
    if not os.path.isfile(src):
        print("That path is not a file. Try again.")
        return

    # Probe resolution to decide on upscale
    w, h = ffprobe_resolution(src)
    vf = build_filter_chain(w, h)

    # Output path with timestamp in same directory
    folder = os.path.dirname(src)
    base, ext = os.path.splitext(os.path.basename(src))
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_ext = ".mkv"  # stay in container that plays nice with streams
    out_name = f"{base}_prettified_{ts}{out_ext}"
    out_path = os.path.join(folder, out_name)

    # Build ffmpeg command
    # -c:v libx264 -preset slow -crf 18 for visually lossless-ish, natural look
    # -af afftdn for hiss reduction; re-encode audio to AAC 192k
    cmd = [
        "ffmpeg",
        "-y",
        "-i", src,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-af", "afftdn=nf=-25",
        "-c:a", "aac",
        "-b:a", "192k",
        out_path
    ]

    print("\nFilters:", vf)
    print("Working... grab water, not vibes.\n")
    try:
        subprocess.run(cmd, check=True)
        print(f"Done. Saved:\n{out_path}")
    except subprocess.CalledProcessError as e:
        print("FFmpeg choked on something. Details below so you can scowl at them:\n")
        print(e)
    except KeyboardInterrupt:
        print("\nCanceled. Dramatic, but valid.")

if __name__ == "__main__":
    prettify()
