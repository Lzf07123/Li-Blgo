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
    """解析 beacon 日志并写入 stats；admin 只读日志，用 data 卷偏移去重。

    beacon 卷由 nginx 写入，admin 不再要求写权限；卷可写时仍尽力清空日志。
    返回导入行数。
    """
    log_path = pathlib.Path(path or settings.beacon_log)
    if not log_path.exists():
        return 0
    state_path = pathlib.Path(settings.db_path).with_name("beacon_import.offset")
    try:
        offset = int(state_path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        offset = 0
    try:
        size = log_path.stat().st_size
    except OSError as exc:
        print(f"[beacon] 跳过导入：beacon 日志不可读（{exc}）")
        return 0
    if size < offset:
        offset = 0  # 日志被截断/轮转：从头导入剩余内容
    try:
        with log_path.open("rb") as fh:
            fh.seek(offset)
            raw = fh.read()
    except OSError as exc:
        print(f"[beacon] 跳过导入：beacon 日志不可读（{exc}）")
        return 0
    if not raw:
        return 0
    text = raw.decode("utf-8", errors="replace")
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
    new_offset = offset + len(raw)
    try:
        state_path.write_text(str(new_offset), encoding="utf-8")
    except OSError as exc:
        print(f"[beacon] warning: 已导入但无法记录偏移（{exc}）")
    try:
        log_path.write_text("", encoding="utf-8")
        state_path.write_text("0", encoding="utf-8")
    except OSError:
        pass  # 卷不可写时保留日志，偏移量已防止重复导入
    return len(rows)
