import re
import magic
from typing import NamedTuple

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/tiff", "image/jpeg", "image/png",
    "image/vnd.djvu",
}
MAX_FILE_SIZE_MB = 500

class SecurityError(Exception):
    pass

class ValidationResult(NamedTuple):
    safe_filename: str
    mime: str

def validate_upload(file_bytes: bytes, filename: str) -> ValidationResult:
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise SecurityError(f"File too large: max {MAX_FILE_SIZE_MB}MB")
    
    detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise SecurityError(f"Forbidden file type: {detected_mime}")
    
    safe_name = re.sub(r'[^\w\-\.]', '_', filename)
    safe_name = safe_name[:255]
    
    if detected_mime == "application/zip":
        raise SecurityError("Archive files not allowed")
    
    return ValidationResult(safe_filename=safe_name, mime=detected_mime)

def validate_query(query: str) -> str:
    if len(query) > 2000:
        raise ValueError("Query too long: max 2000 characters")
    
    INJECTION_PATTERNS = [
        r'ignore previous instructions',
        r'system prompt',
        r'you are now',
        r'forget everything',
    ]
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise SecurityError("Invalid query content")
    return query.strip()
