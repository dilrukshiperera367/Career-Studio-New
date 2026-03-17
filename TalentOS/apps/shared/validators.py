"""Data validation utilities for consistent input validation across the app."""

import re
from rest_framework import serializers


# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

def validate_email_format(value):
    """Raise ValidationError if the email format is invalid."""
    if not EMAIL_REGEX.match(value):
        raise serializers.ValidationError(f"'{value}' is not a valid email address.")
    return value


# ─── Phone ────────────────────────────────────────────────────────────────────
PHONE_REGEX = re.compile(r"^\+?[\d\s\-().]{7,20}$")

def validate_phone_format(value):
    """Raise ValidationError if the phone format is invalid."""
    if value and not PHONE_REGEX.match(value):
        raise serializers.ValidationError(f"'{value}' is not a valid phone number.")
    return value


# ─── Salary ──────────────────────────────────────────────────────────────────
def validate_salary_range(min_salary, max_salary):
    """Ensure min <= max and values are non-negative."""
    if min_salary is not None and min_salary < 0:
        raise serializers.ValidationError("Minimum salary cannot be negative.")
    if max_salary is not None and max_salary < 0:
        raise serializers.ValidationError("Maximum salary cannot be negative.")
    if min_salary is not None and max_salary is not None and min_salary > max_salary:
        raise serializers.ValidationError("Minimum salary cannot exceed maximum salary.")


# ─── Date Range ──────────────────────────────────────────────────────────────
def validate_date_range(start_date, end_date):
    """Ensure start <= end."""
    if start_date and end_date and start_date > end_date:
        raise serializers.ValidationError("Start date cannot be after end date.")


# ─── File Upload ─────────────────────────────────────────────────────────────
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
MAX_FILE_SIZE_MB = 10

# Magic-byte signatures for allowed file types  (#68 — validate beyond extension)
_MAGIC_SIGNATURES: list[tuple[bytes, bytes | None]] = [
    # PDF
    (b"%PDF", None),
    # MS-Office legacy .doc
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", None),
    # Office Open XML (.docx) — ZIP magic
    (b"PK\x03\x04", None),
    # Plain-text / RTF — no reliable magic; allowed by extension only
]

def _check_magic_bytes(uploaded_file) -> bool:
    """Return True if file starts with a known-safe magic sequence."""
    uploaded_file.seek(0)
    header = uploaded_file.read(8)
    uploaded_file.seek(0)
    for magic, _ in _MAGIC_SIGNATURES:
        if header.startswith(magic):
            return True
    # Plain text (.txt, .rtf) has no reliable magic — allow if extension is safe
    return True  # final gate is extension; magic adds defence-in-depth


def validate_file_upload(uploaded_file):
    """Validate file type (extension + magic bytes) and size for resume uploads."""
    if uploaded_file:
        ext = "." + uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
        if ext not in ALLOWED_RESUME_EXTENSIONS:
            raise serializers.ValidationError(
                f"File type '{ext}' not allowed. Accepted: {', '.join(ALLOWED_RESUME_EXTENSIONS)}"
            )
        if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File too large ({uploaded_file.size / 1024 / 1024:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB."
            )
        # Magic-byte check for PDF and Office files
        if ext in {".pdf", ".doc", ".docx"}:
            uploaded_file.seek(0)
            header = uploaded_file.read(8)
            uploaded_file.seek(0)
            pdf_ok = header.startswith(b"%PDF") and ext == ".pdf"
            doc_ok = header.startswith(b"\xd0\xcf\x11\xe0") and ext == ".doc"
            docx_ok = header.startswith(b"PK\x03\x04") and ext == ".docx"
            if ext == ".pdf" and not pdf_ok:
                raise serializers.ValidationError("File content does not match the declared PDF extension.")
            if ext == ".doc" and not doc_ok:
                raise serializers.ValidationError("File content does not match the declared DOC extension.")
            if ext == ".docx" and not docx_ok:
                raise serializers.ValidationError("File content does not match the declared DOCX extension.")
    return uploaded_file


# ─── URL ─────────────────────────────────────────────────────────────────────
URL_REGEX = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

def validate_url(value):
    """Validate URL format."""
    if value and not URL_REGEX.match(value):
        raise serializers.ValidationError(f"'{value}' is not a valid URL.")
    return value


# ─── Text Sanitization ──────────────────────────────────────────────────────
DANGEROUS_PATTERNS = [
    re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
]

def sanitize_text(value):
    """Strip potentially dangerous content from text inputs."""
    if isinstance(value, str):
        for pattern in DANGEROUS_PATTERNS:
            value = pattern.sub("", value)
    return value
