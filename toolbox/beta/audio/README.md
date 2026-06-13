# QiOS Audio Factory

The cleanest free pipeline for audiobook production.

## Project Structure
- `voice_map.json`: Maps speaker tags to specific TTS voices.
- `book_projects/`: Individual folders for each audiobook project.
  - `text/`: Cleaned plaintext files (chapter-by-chapter).
  - `audio_raw/`: Unprocessed wav files from TTS.
  - `audio_final/`: Normalized and mastered MP3/M4B chapters.
  - `music_sfx/`: Background tracks and sound effects.
  - `licenses/`: Attribution notes and license files.
  - `logs/`: Render logs and tracking.

## Pipeline
1. **Prepare Text**: Export chapters as `.txt` files with speaker tagging.
2. **TTS Generation**: Render segments using Piper or local neural TTS.
3. **Mastering**: Normalize loudness and combine segments/music using FFmpeg.
4. **Assembly**: Final concatenation into audiobook format.

## Speaker Tagging Convention
Use the following format for multi-voice chapters:
```
[NARRATOR] Once upon a time...
[CHARACTER_NAME] "I can't believe it."
```

## Setup (Local Rendering)
- **Piper**: Fast, local TTS (CPU-friendly).
- **FFmpeg**: Audio utility for mastering and conversion.
