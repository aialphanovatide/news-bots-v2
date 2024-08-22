import re

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by replacing all non-alphanumeric characters with underscores.
    """
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', filename)
    return sanitized