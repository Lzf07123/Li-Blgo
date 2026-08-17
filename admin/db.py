"""SQLite：管理员（唯一一行）、会话、回程登出 jti 缓存、统计。"""

import sqlite3
import time
from typing import Optional

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
    conn.commit()
    conn.close()


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
