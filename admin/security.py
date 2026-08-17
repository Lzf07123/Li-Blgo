"""密码哈希（stdlib PBKDF2-HMAC-SHA256）、限速、CSRF 令牌。"""

import base64
import hashlib
import hmac
import secrets
import time

ITERATIONS = 600_000
KEYLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=KEYLEN)
    return f"pbkdf2${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, dk_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
            dklen=len(expected),
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int, window: float) -> bool:
        now = time.monotonic()
        queue = [t for t in self._events.get(key, []) if t > now - window]
        if len(queue) >= limit:
            self._events[key] = queue
            return False
        queue.append(now)
        self._events[key] = queue
        return True


def new_token() -> str:
    return secrets.token_hex(16)


def check_token(expected: str, given: str) -> bool:
    return hmac.compare_digest(expected or "", given or "")
