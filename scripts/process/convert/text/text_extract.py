"""
Text extraction for different file types.
Supports: .md, .txt, .csv, .pdf (basic)
Skips: video, audio, images (for now)
"""
import csv
from pathlib import Path
from typing import Optional, Tuple

# Supported file types (priority order)
SUPPORTED_EXTENSIONS = {
    ".md": 1,   # Highest priority
    ".txt": 2,
    ".csv": 3,
    ".pdf": 4,  # Basic PDF support
}

# File types to skip (not supported yet)
SKIP_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm",  # Video
    ".mp3", ".wav", ".m4a", ".ogg", ".flac",  # Audio
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic",  # Images
    ".zip", ".tar", ".gz", ".7z",  # Archives
    ".exe", ".dll", ".so", ".dylib",  # Binaries
}


def get_file_priority(file_ext: str) -> int:
    """Get processing priority for file extension (lower = higher priority)."""
    ext_lower = file_ext.lower()
    return SUPPORTED_EXTENSIONS.get(ext_lower, 999)  # Unsupported files get low priority


def should_process_file(file_ext: str) -> Tuple[bool, str]:
    """
    Check if file should be processed.
    
    Returns:
        (should_process: bool, reason: str)
    """
    ext_lower = file_ext.lower()
    
    if ext_lower in SKIP_EXTENSIONS:
        return False, f"File type {ext_lower} not supported yet (video/audio/image/binary)"
    
    if ext_lower in SUPPORTED_EXTENSIONS:
        return True, "Supported file type"
    
    # Unknown extension - skip for now
    return False, f"Unknown file type {ext_lower}"


def extract_text_from_file(file_path: str, file_ext: str) -> Optional[str]:
    """
    Extract text from a file based on its extension.
    
    Args:
        file_path: Full path to the file
        file_ext: File extension (e.g., ".md", ".txt")
    
    Returns:
        Extracted text, or None if extraction failed
    """
    ext_lower = file_ext.lower()
    path = Path(file_path)
    
    if not path.exists():
        return None
    
    try:
        if ext_lower == ".md" or ext_lower == ".txt":
            # Plain text files
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif ext_lower == ".csv":
            # CSV files - convert to text representation
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = []
                for row in reader:
                    rows.append(" | ".join(row))
                return "\n".join(rows)
        
        elif ext_lower == ".pdf":
            # Basic PDF support - try to extract text
            try:
                import PyPDF2
                with open(path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text_parts = []
                    for page in pdf_reader.pages:
                        text_parts.append(page.extract_text())
                    return "\n\n".join(text_parts)
            except ImportError:
                # PyPDF2 not installed - skip PDF for now
                return None
            except Exception as e:
                print(f"[EXTRACT] PDF extraction failed for {file_path}: {e}")
                return None
        
        else:
            # Unknown type
            return None
    
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            print(f"[EXTRACT] Failed to read {file_path} with fallback encoding: {e}")
            return None
    
    except Exception as e:
        print(f"[EXTRACT] Failed to extract text from {file_path}: {e}")
        return None

