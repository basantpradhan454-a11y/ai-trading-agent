"""
API keys are NEVER stored in plain text.
Every exchange API key/secret is encrypted with Fernet (AES-128-CBC + HMAC)
before it touches the database, using a server-side key that only the
backend/app process holds (ENCRYPTION_KEY env var / Streamlit secret).
"""
import os
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one locally with:\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "and set it as an environment variable / Streamlit secret. Never hardcode it in source."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plain: str) -> str:
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    if not token:
        return ""
    return _get_fernet().decrypt(token.encode()).decode()


def mask(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    return "•" * max(0, len(value) - keep) + value[-keep:]
