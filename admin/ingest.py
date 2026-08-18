"""匿名打点日志导入：nginx 只记 时间|路径，admin 启动时导入 stats 表。"""

import pathlib
from typing import Optional
from urllib.parse import parse_qs, unquote

from admin.config import settings
from admin.db import canonical_stats_path, connect


MAX_BEACON_PATH = 512


def valid_site_path(path: str) -> bool:
    """只放行站内相对路径，拒绝 scheme 注入、控制字符与超长路径。"""
    if not path or not path.startswith("/"):
        return False
    if ":" in path:
        return False
    if len(path) > MAX_BEACON_PATH:
        return False
    if any(ord(ch) < 32 or ch.isspace() for ch in path):
        return False
    return True


def beacon_page(uri: str) -> Optional[str]:
    """从 nginx 原始 request_uri 中取出 ?p= 页面路径并解码一次。

    Hugo 输出时已把路径整体 URL 编码（如 %2fposts%2f...），
    这里解码一次得到可直接作为站点路径使用的规范值。
    """
    if "?" not in uri:
        return None
    query = uri.split("?", 1)[1]
    pages = parse_qs(query, keep_blank_values=False).get("p")
    if not pages:
        return None
    page = canonical_stats_path(pages[0].strip())
    decoded = unquote(page) if page else ""
    if not valid_site_path(page) or not valid_site_path(decoded):
        return None
    return page


def import_beacon_log(path: Optional[str] = None) -> int:
    """解析 beacon 日志并写入 stats；成功后清空日志。返回导入行数。"""
    log_path = pathlib.Path(path or settings.beacon_log)
    if not log_path.exists():
        return 0
    try:
        with log_path.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        print(f"[beacon] 跳过导入：beacon 日志不可写（{exc}）")
        return 0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return 0
    rows = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        ts, uri = line.split("|", 1)
        page = beacon_page(uri)
        if page is None:
            continue
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
    try:
        log_path.write_text("", encoding="utf-8")
    except OSError as exc:
        print(f"[beacon] warning: 已导入但无法清空日志（{exc}）")
    return len(rows)
