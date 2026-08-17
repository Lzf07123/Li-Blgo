"""匿名打点日志导入：nginx 只记 时间|路径，admin 启动时导入 stats 表。"""

import pathlib
from typing import Optional

from admin.config import settings
from admin.db import connect


def import_beacon_log(path: Optional[str] = None) -> int:
    """解析 beacon 日志并写入 stats；成功后清空日志。返回导入行数。"""
    log_path = pathlib.Path(path or settings.beacon_log)
    if not log_path.exists():
        return 0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return 0
    rows = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        ts, uri = line.split("|", 1)
        if "?p=" not in uri:
            continue
        page = uri.split("?p=", 1)[1]
        day = ts[:10]
        rows.append((page, day))
    if not rows:
        return 0
    conn = connect()
    conn.executemany(
        "INSERT INTO stats (path, day, views) VALUES (?, ?, 1) "
        "ON CONFLICT(path, day) DO UPDATE SET views = views + 1",
        rows,
    )
    conn.commit()
    conn.close()
    log_path.write_text("", encoding="utf-8")
    return len(rows)
