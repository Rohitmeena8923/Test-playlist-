import re
import os

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from a filename."""
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.strip()
    return filename[:100]  # Limit length to 100 characters

def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(path)