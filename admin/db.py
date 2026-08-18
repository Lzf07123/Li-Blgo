"""SQLite：管理员（唯一一行）、会话、回程登出 jti 缓存、统计。"""

import sqlite3
import time
from typing import Optional
from urllib.parse import quote, unquote

from admin.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_account (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  username TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  oidc_sub TEXT,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  sub TEXT,
  sid TEXT,
  csrf TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS jti_cache (
  jti TEXT PRIMARY KEY,
  exp INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS stats (
  path TEXT NOT NULL,
  day TEXT NOT NULL,
  views INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (path, day)
);
"""


def connect() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    normalize_stats_paths(conn)
    conn.commit()
    conn.close()


def canonical_stats_path(path: str) -> str:
    """把统计路径规范化为 Hugo 实际生成的 URL 路径。

    beacon 参数里斜杠被整体编码（%2f...），先解码一次；
    中文等非 ASCII 字符则编码回 %XX，保证存储值可直接作为站点链接。
    """
    decoded = unquote(path) if "%2f" in path.lower() else path
    if decoded and any(ord(ch) > 127 for ch in decoded) and "%" not in decoded:
        return quote(decoded, safe="/")
    return decoded


def normalize_stats_paths(conn) -> int:
    """把历史 stats 中整体编码的路径（%2fposts%2f...）修正为规范路径。

    仅在存在需要修正的行时执行，返回修正的旧路径数量。
    """
    rows = conn.execute("SELECT path, day, views FROM stats").fetchall()
    changed = set()
    groups: dict[tuple[str, str], int] = {}
    for r in rows:
        new_path = canonical_stats_path(r["path"])
        if new_path != r["path"]:
            changed.add(r["path"])
            key = (new_path, r["day"])
            groups[key] = groups.get(key, 0) + r["views"]
    if not changed:
        return 0
    for old in changed:
        conn.execute("DELETE FROM stats WHERE path = ?", (old,))
    for (new_path, day), total in groups.items():
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, ?) "
            "ON CONFLICT(path, day) DO UPDATE SET views = views + ?",
            (new_path, day, total, total),
        )
    return len(changed)


def get_admin(conn) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM admin_account WHERE id = 1").fetchone()


def create_admin(conn, username: str, password_hash: str) -> None:
    conn.execute(
        "INSERT INTO admin_account (id, username, password_hash, created_at) VALUES (1, ?, ?, ?)",
        (username, password_hash, int(time.time())),
    )
    conn.commit()


def set_oidc_sub(conn, sub: str) -> None:
    conn.execute("UPDATE admin_account SET oidc_sub = ? WHERE id = 1", (sub,))
    conn.commit()
