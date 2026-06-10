import os

class SecurityError(Exception):
    pass

def safe_path(base_dir: str, filename: str) -> str:
    """
    Prevents path traversal vulnerabilities.
    """
    full_path = os.path.realpath(os.path.join(base_dir, filename))
    if not full_path.startswith(os.path.realpath(base_dir)):
        raise SecurityError("Path traversal attempt detected")
    return full_path
