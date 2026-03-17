"""
ClamAV antivirus integration for file scanning.

Scans file streams before storing to S3/MinIO.

Usage:
    from apps.shared.clamav import scan_file, ScanResult

    result = scan_file(file_obj)
    if not result.is_clean:
        raise ValidationError(f"File rejected: {result.threat}")
"""

import socket
import struct
import logging
import io
from dataclasses import dataclass
from typing import BinaryIO, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# ClamAV INSTREAM protocol constants
CHUNK_SIZE = 4096
MAX_STREAM_SIZE = 10 * 1024 * 1024  # 10 MB hard cap


@dataclass
class ScanResult:
    is_clean: bool
    threat: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


def scan_file(file_obj: BinaryIO, filename: str = "upload") -> ScanResult:
    """
    Scan a file-like object for viruses using ClamAV daemon (clamd).

    Returns a ScanResult indicating whether the file is clean.
    On connection/timeout errors, logs a warning and returns is_clean=True
    (fail-open) to avoid blocking uploads when ClamAV is unavailable.
    Set CLAMAV_ENABLED=True to enable strict mode.
    """
    if not getattr(settings, "CLAMAV_ENABLED", False):
        return ScanResult(is_clean=True)

    host = getattr(settings, "CLAMAV_HOST", "clamav")
    port = getattr(settings, "CLAMAV_PORT", 3310)
    timeout = getattr(settings, "CLAMAV_TIMEOUT", 30)

    try:
        # Save file position so caller's cursor is not affected
        original_pos = file_obj.tell() if hasattr(file_obj, "tell") else None
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))

        # Send INSTREAM command
        sock.sendall(b"zINSTREAM\0")

        # Stream file data in chunks, each prefixed with big-endian uint32 length
        while True:
            chunk = file_obj.read(CHUNK_SIZE)
            if not chunk:
                break
            size = struct.pack("!I", len(chunk))
            sock.sendall(size + chunk)

        # Terminate stream with 0-length chunk
        sock.sendall(struct.pack("!I", 0))

        # Read response
        response = b""
        while True:
            data = sock.recv(1024)
            if not data:
                break
            response += data
        sock.close()

        # Restore file position
        if original_pos is not None and hasattr(file_obj, "seek"):
            file_obj.seek(original_pos)

        response_str = response.decode("utf-8", errors="replace").strip().rstrip("\0")
        logger.debug("ClamAV scan response for %s: %s", filename, response_str)

        if response_str.endswith("OK"):
            return ScanResult(is_clean=True)
        elif "FOUND" in response_str:
            # e.g. "stream: Eicar-Signature FOUND"
            parts = response_str.split(":")
            threat = parts[-1].strip().replace(" FOUND", "") if len(parts) > 1 else "Unknown"
            logger.warning("ClamAV: threat detected in %s — %s", filename, threat)
            return ScanResult(is_clean=False, threat=threat)
        else:
            logger.error("ClamAV: unexpected response for %s: %s", filename, response_str)
            # Unexpected response — treat as error; reject in strict mode
            strict_mode = getattr(settings, "CLAMAV_STRICT_MODE", not getattr(settings, "DEBUG", False))
            return ScanResult(is_clean=not strict_mode, error=f"Unexpected response: {response_str}")

    except (socket.timeout, socket.error, OSError) as exc:
        strict_mode = getattr(settings, "CLAMAV_STRICT_MODE", not getattr(settings, "DEBUG", False))
        if strict_mode:
            logger.error(
                "ClamAV: connection error scanning %s (host=%s port=%d): %s — rejecting file (strict mode)",
                filename, host, port, exc
            )
            return ScanResult(is_clean=False, error=str(exc))
        logger.warning(
            "ClamAV: connection error scanning %s (host=%s port=%d): %s — scan skipped (non-strict)",
            filename, host, port, exc
        )
        return ScanResult(is_clean=True, error=str(exc))


def scan_bytes(data: bytes, filename: str = "upload") -> ScanResult:
    """Convenience wrapper to scan raw bytes."""
    return scan_file(io.BytesIO(data), filename=filename)
