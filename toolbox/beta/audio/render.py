import os
import json
import subprocess
import re
import argparse


def load_voice_map():
    with open("voice_map.json", "r") as f:
        return json.load(f)


def render_segment(text, voice_config, output_path, piper_path):
    # Using Piper CLI
    # piper --model model.onnx --output_file file.wav
    model_name = voice_config["voice"]
    model_path = os.path.join("bin", "models", f"{model_name}.onnx")

    if not os.path.exists(model_path):
        print(f"Error: Model {model_path} not found.")
        return False

    cmd = [piper_path, "--model", model_path, "--output_file", output_path]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input=text)

    if process.returncode != 0:
        print(f"Piper error: {stderr}")
        return False
    return True


def parse_segments(text):
    # Split text into segments based on [SPEAKER] tags
    # Returns list of (speaker, text)
    pattern = r"\[([A-Z0-9_]+)\]"
    parts = re.split(pattern, text)

    segments = []
    if not text.startswith("["):
        # Initial text with no tag (assume NARRATOR)
        if parts[0].strip():
            segments.append(("NARRATOR", parts[0].strip()))
        start_idx = 1
    else:
        start_idx = 1

    for i in range(start_idx, len(parts), 2):
        speaker = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            segments.append((speaker, content))

    return segments


def process_chapter(project_name, chapter_file, piper_path):
    project_path = os.path.join("book_projects", project_name)
    text_path = os.path.join(project_path, "text", chapter_file)
    raw_path = os.path.join(project_path, "audio_raw")
    final_path = os.path.join(project_path, "audio_final")

    chapter_name = os.path.splitext(chapter_file)[0]
    output_wav = os.path.join(raw_path, f"{chapter_name}.wav")
    output_mp3 = os.path.join(final_path, f"{chapter_name}.mp3")

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    segments = parse_segments(text)
    voice_map = load_voice_map()

    segment_files = []
    for i, (speaker, content) in enumerate(segments):
        if speaker not in voice_map:
            print(
                f"Warning: Speaker {speaker} not in voice_map.json. Falling back to NARRATOR."
            )
            speaker = "NARRATOR"

        voice_config = voice_map[speaker]
        seg_file = os.path.join(raw_path, f"{chapter_name}_seg_{i:03d}.wav")
        print(f"Rendering segment {i} for {speaker}...")
        if render_segment(content, voice_config, seg_file, piper_path):
            segment_files.append(seg_file)

    if not segment_files:
        return

    # Concatenate using FFmpeg
    # Create list file for ffmpeg
    list_file = os.path.join(raw_path, "list.txt")
    with open(list_file, "w") as f:
        for sf in segment_files:
            # FFmpeg concat needs forward slashes or escaped backslashes
            f.write(f"file '{os.path.abspath(sf).replace('\\', '/')}'\n")

    print("Concatenating segments...")
    concat_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
        "-c",
        "copy",
        output_wav,
    ]
    subprocess.run(concat_cmd, check=True)

    print("Normalizing and converting to MP3...")
    # Normalize loudness to -16 LUFS (audiobook standard)
    norm_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        output_wav,
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        output_mp3,
    ]
    subprocess.run(norm_cmd, check=True)

    # Cleanup segment files
    for sf in segment_files:
        os.remove(sf)
    os.remove(list_file)

    print(f"Finished {chapter_name} -> {output_mp3}")


def main():
    parser = argparse.ArgumentParser(description="QiOS Audio Factory Render Script")
    parser.add_argument("project", help="Project name (e.g. paid_in_full)")
    parser.add_argument("--chapter", help="Specific chapter file to render (optional)")
    args = parser.parse_args()

    piper_path = os.path.join("bin", "piper.exe")
    if not os.path.exists(piper_path):
        print(f"Error: {piper_path} not found. Please run setup_piper.ps1 first.")
        return

    project_text_dir = os.path.join("book_projects", args.project, "text")

    if args.chapter:
        process_chapter(args.project, args.chapter, piper_path)
    else:
        chapters = sorted(
            [f for f in os.listdir(project_text_dir) if f.endswith(".txt")]
        )
        for chapter in chapters:
            process_chapter(args.project, chapter, piper_path)


if __name__ == "__main__":
    main()
