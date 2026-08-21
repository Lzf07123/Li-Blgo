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

    def _cleanup(self, now: float, window: float) -> None:
        if len(self._events) > 1000:
            # 周期性清理：先剔除已过期时间戳，再移除空队列，避免长期运行后内存增长
            self._events = {
                k: [t for t in v if t > now - window]
                for k, v in self._events.items()
                if any(t > now - window for t in v)
            }

    def peek(self, key: str, limit: int, window: float) -> bool:
        """只读判断是否已达上限（不消耗次数），供登录成功后不占用配额。"""
        now = time.monotonic()
        self._cleanup(now, window)
        queue = [t for t in self._events.get(key, []) if t > now - window]
        return len(queue) >= limit

    def mark(self, key: str) -> None:
        """记录一次失败尝试。"""
        self.mark_at(key, time.monotonic())

    def mark_at(self, key: str, now: float) -> None:
        self._events.setdefault(key, []).append(now)
        self._cleanup(now, 0)

    def allow(self, key: str, limit: int, window: float) -> bool:
        now = time.monotonic()
        if self.peek(key, limit, window):
            return False
        self.mark_at(key, now)
        return True


def new_token() -> str:
    return secrets.token_hex(16)


def check_token(expected: str, given: str) -> bool:
    return hmac.compare_digest(expected or "", given or "")
