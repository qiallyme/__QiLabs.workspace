import whisper
import os
import sys

def transcribe():
    audio_path = r"C:\Users\codyr\Videos\Screen Recordings\audio_track.mp3"
    print(f"Loading model and transcribing {audio_path}...")
    
    # Use base model for a balance of speed and accuracy
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    
    output_path = r"C:\Users\codyr\Videos\Screen Recordings\transcription.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    print(f"Transcription complete. Saved to {output_path}")

if __name__ == "__main__":
    transcribe()
