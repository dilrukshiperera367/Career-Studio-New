"""Field-level encryption utilities using Fernet symmetric encryption.

Usage::

    from apps.shared.encryption import encrypt_value, decrypt_value

    # Encrypt before storing
    encrypted_password = encrypt_value(raw_password)

    # Decrypt before use
    raw_password = decrypt_value(encrypted_password)

Configuration
-------------
Set ``FIELD_ENCRYPTION_KEY`` env variable to a URL-safe base64-encoded 32-byte
Fernet key.  Generate one with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If the key is not set (e.g. local dev), values are stored/returned as-is with a
``plain:`` prefix so existing unencrypted values continue to work.
"""
from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger(__name__)

_FERNET_PREFIX = b"enc:"
_PLAIN_PREFIX = "plain:"


def _get_fernet():
    """Return a Fernet instance or None if no key is configured."""
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.error("Failed to initialise Fernet: %s", exc)
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt *plaintext* and return a base64-encoded ciphertext string.

    Returns the original value unchanged when no encryption key is configured.
    Already-encrypted values (prefixed with ``enc:``) are returned as-is.
    """
    if not plaintext:
        return plaintext
    if isinstance(plaintext, str) and plaintext.startswith(_PLAIN_PREFIX[:-1]):
        # Legacy plain storage — strip prefix and re-encrypt
        plaintext = plaintext[len(_PLAIN_PREFIX):]
    fernet = _get_fernet()
    if fernet is None:
        return plaintext  # No key: store plaintext (acceptable for local dev)
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return "enc:" + base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_value(value: str) -> str:
    """Decrypt a value previously encrypted with :func:`encrypt_value`.

    Returns the original value unchanged if it is not an encrypted token or
    if no encryption key is configured.
    """
    if not value:
        return value
    if not isinstance(value, str) or not value.startswith("enc:"):
        return value  # Plaintext or legacy unencrypted
    fernet = _get_fernet()
    if fernet is None:
        logger.warning("FIELD_ENCRYPTION_KEY not set — cannot decrypt value")
        return ""
    try:
        token = base64.urlsafe_b64decode(value[4:].encode("ascii"))
        return fernet.decrypt(token).decode("utf-8")
    except Exception as exc:
        logger.error("Failed to decrypt value: %s", exc)
        return ""
