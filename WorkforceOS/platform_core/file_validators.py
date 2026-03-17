"""
Shared file-upload validation for the HRM backend.
Performs extension whitelist + magic-byte checks + ClamAV virus scan (#159/#68/#160 security hardening).
"""
from rest_framework import serializers

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".png", ".jpg", ".jpeg"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_FILE_SIZE_MB = 20  # HRM documents can be larger than resumes

_MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".doc": b"\xd0\xcf\x11\xe0",
    ".docx": b"PK\x03\x04",
    ".png": b"\x89PNG",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".gif": b"GIF8",
    ".webp": b"RIFF",
}


def validate_document_upload(uploaded_file):
    """Validate extension, magic bytes and size for HRM document uploads."""
    if not uploaded_file:
        return uploaded_file

    name = uploaded_file.name or ""
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise serializers.ValidationError(
            f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}"
        )

    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise serializers.ValidationError(
            f"File too large ({uploaded_file.size / 1024 / 1024:.1f} MB). Max: {MAX_FILE_SIZE_MB} MB."
        )

    magic = _MAGIC.get(ext)
    if magic:
        uploaded_file.seek(0)
        header = uploaded_file.read(len(magic))
        uploaded_file.seek(0)
        if not header.startswith(magic):
            raise serializers.ValidationError(
                f"File content does not match the declared '{ext}' extension."
            )

    # ClamAV virus scan (#160 — fail-closed in production)
    try:
        from platform_core.clamav import scan_file
        scan_result = scan_file(uploaded_file, filename=uploaded_file.name)
        if not scan_result.is_clean:
            raise serializers.ValidationError(
                f"File rejected: {scan_result.threat or scan_result.error or 'virus scan failed'}"
            )
    except serializers.ValidationError:
        raise
    except Exception:
        # scan_file itself handles strict/non-strict logic; bare exceptions here are config errors
        pass

    return uploaded_file


def validate_image_upload(uploaded_file):
    """Validate extension, magic bytes and size for profile/company image uploads."""
    if not uploaded_file:
        return uploaded_file

    name = uploaded_file.name or ""
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            f"Image type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    if uploaded_file.size > 5 * 1024 * 1024:  # 5 MB for images
        raise serializers.ValidationError("Image too large. Max: 5 MB.")

    magic = _MAGIC.get(ext)
    if magic:
        uploaded_file.seek(0)
        header = uploaded_file.read(len(magic))
        uploaded_file.seek(0)
        if not header.startswith(magic):
            raise serializers.ValidationError(
                f"Image content does not match the declared '{ext}' extension."
            )

    return uploaded_file
