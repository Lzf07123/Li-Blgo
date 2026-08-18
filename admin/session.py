"""服务端会话：Cookie 只存随机 id，内容在 SQLite。"""

import secrets
import time
from typing import Optional

from admin.config import settings
from admin.db import connect
from admin.security import new_token

COOKIE = "liblog_admin_session"


def create_session(kind: str, sub: Optional[str] = None, sid: Optional[str] = None) -> str:
    session_id = secrets.token_hex(24)
    now = int(time.time())
    conn = connect()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.execute(
        "INSERT INTO sessions (id, kind, sub, sid, csrf, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, kind, sub, sid, new_token(), now, now + settings.session_ttl),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND expires_at > ?",
        (session_id, int(time.time())),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(session_id: str) -> None:
    conn = connect()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def delete_by_oidc(sub: str, sid: str) -> None:
    conn = connect()
    conn.execute("DELETE FROM sessions WHERE sub = ? AND sid = ?", (sub, sid))
    conn.commit()
    conn.close()
