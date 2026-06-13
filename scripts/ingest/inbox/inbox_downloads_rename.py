import os
import re
import datetime

# Configuration
TARGET_DIR = os.path.expanduser("~/Downloads")

def rename_files():
    # Regex to match: YYYY-MM-DD-hhmmss_ (to prevent double-renaming)
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}_")

    for filename in os.listdir(TARGET_DIR):
        file_path = os.path.join(TARGET_DIR, filename)

        # Skip directories and hidden files
        if not os.path.isfile(file_path) or filename.startswith('.'):
            continue

        # Check if already renamed
        if pattern.match(filename):
            print(f"Skipping: {filename} (Already formatted)")
            continue

        try:
            # Get creation time (platform dependent, falls back to mtime)
            stat = os.stat(file_path)
            try:
                created_time = stat.st_birthtime # macOS/FreeBSD
            except AttributeError:
                created_time = stat.st_mtime # Linux/Windows

            dt = datetime.datetime.fromtimestamp(created_time)
            timestamp = dt.strftime("%Y-%m-%d-%H%M%S")

            # Clean original filename: replace spaces with underscores
            clean_name = filename.replace(" ", "_")
            new_filename = f"{timestamp}_{clean_name}"
            new_file_path = os.path.join(TARGET_DIR, new_filename)

            os.rename(file_path, new_file_path)
            print(f"Renamed: {filename} -> {new_filename}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    rename_files()