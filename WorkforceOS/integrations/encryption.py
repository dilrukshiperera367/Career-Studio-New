"""
Credential encryption utilities for integration credentials storage.

Uses AES-128 via cryptography.fernet (symmetric encryption).
Falls back to base64 if cryptography package is not installed
(dev convenience — never use fallback in production).

Usage:
    from integrations.encryption import encrypt_credentials, decrypt_credentials

    # Encrypt before saving
    encrypted = encrypt_credentials({'api_key': 'sk-...', 'secret': 'abc...'})

    # Decrypt after loading
    plaintext = decrypt_credentials(encrypted)
"""

import base64
import json
import logging
import os

logger = logging.getLogger(__name__)

_FALLBACK_WARNING_SHOWN = False


def _get_key() -> bytes:
    """
    Load the Fernet encryption key from settings.
    Key must be a 32-byte URL-safe base64-encoded string.
    Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    from django.conf import settings
    key = getattr(settings, 'INTEGRATION_ENCRYPTION_KEY', None) or os.environ.get('INTEGRATION_ENCRYPTION_KEY')
    if not key:
        raise ValueError(
            'INTEGRATION_ENCRYPTION_KEY is not set. '
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return key.encode() if isinstance(key, str) else key


def encrypt_credentials(data: dict) -> str:
    """
    Encrypt a credentials dict → base64-encoded ciphertext string for DB storage.
    Returns a string prefixed with 've1:' for versioning.
    """
    global _FALLBACK_WARNING_SHOWN
    plaintext = json.dumps(data).encode()
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_key())
        token = f.encrypt(plaintext)
        return 've1:' + base64.urlsafe_b64encode(token).decode()
    except ImportError:
        if not _FALLBACK_WARNING_SHOWN:
            logger.warning(
                'cryptography package not installed — credentials stored as base64 only. '
                'Install cryptography for production: pip install cryptography'
            )
            _FALLBACK_WARNING_SHOWN = True
        return 'vb64:' + base64.b64encode(plaintext).decode()
    except ValueError as exc:
        logger.error('Credential encryption failed (key misconfigured): %s', exc)
        raise


def decrypt_credentials(ciphertext: str) -> dict:
    """
    Decrypt a ciphertext string back to the original credentials dict.
    Handles both 've1:' (Fernet) and 'vb64:' (fallback) prefixes.
    Returns empty dict on failure.
    """
    if not ciphertext:
        return {}

    try:
        if ciphertext.startswith('ve1:'):
            from cryptography.fernet import Fernet, InvalidToken
            token = base64.urlsafe_b64decode(ciphertext[4:])
            f = Fernet(_get_key())
            plaintext = f.decrypt(token)
            return json.loads(plaintext)

        elif ciphertext.startswith('vb64:'):
            plaintext = base64.b64decode(ciphertext[5:])
            return json.loads(plaintext)

        else:
            # Legacy: plain JSON stored directly (migration path)
            try:
                return json.loads(ciphertext)
            except json.JSONDecodeError:
                return {}

    except Exception as exc:
        logger.error('Credential decryption failed: %s', exc)
        return {}


def is_encrypted(value: str) -> bool:
    """Return True if value was encrypted by this module."""
    return isinstance(value, str) and (value.startswith('ve1:') or value.startswith('vb64:'))
