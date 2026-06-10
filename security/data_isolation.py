import os

# Import the canonical SecurityError so that all security modules raise the same class
from security.input_validator import SecurityError  # noqa: F401


def safe_path(base_dir: str, filename: str) -> str:
    """
    Prevents path traversal vulnerabilities.
    Resolves the full real path of base_dir/filename and ensures it
    stays within base_dir. Raises SecurityError if traversal is detected.
    """
    full_path = os.path.realpath(os.path.join(base_dir, filename))
    real_base = os.path.realpath(base_dir)
    if not full_path.startswith(real_base + os.sep) and full_path != real_base:
        raise SecurityError("Path traversal attempt detected")
    return full_path
