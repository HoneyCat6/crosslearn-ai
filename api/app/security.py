import hashlib
import secrets
from pwdlib import PasswordHash

passwords = PasswordHash.recommended()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, digest(token)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return passwords.verify(password, encoded)
    except Exception:
        return False
