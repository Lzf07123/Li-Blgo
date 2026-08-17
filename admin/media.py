"""媒体库：上传 / 列出 / 删除主题静态图片（themes/blog-theme/static/img/）。

上传后触发一次全量重建，使文件立即出现在公开站 /img/ 路径。
"""

import re
import secrets
import unicodedata
import os
from datetime import date
from pathlib import Path

from admin.config import ROOT

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}
MAX_SIZE = 5 * 1024 * 1024
MEDIA_ROOT = Path(
    os.getenv("MEDIA_ROOT", str(ROOT / "themes" / "blog-theme" / "static" / "img"))
)
_SAFE_RE = re.compile(r"[^a-z0-9-]+")


def slugify(name: str) -> str:
    stem = Path(name or "image").stem.lower()
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = _SAFE_RE.sub("-", stem).strip("-")
    return stem or "image"


def safe_media_path(rel: str) -> Path:
    root = MEDIA_ROOT.resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise ValueError("非法路径")
    return p


def list_media() -> list[dict]:
    items = []
    for p in sorted(MEDIA_ROOT.rglob("*")):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
            rel = p.relative_to(MEDIA_ROOT).as_posix()
            items.append(
                {
                    "rel": rel,
                    "url": f"/img/{rel}",
                    "admin_url": f"/{rel}",
                    "size": p.stat().st_size,
                }
            )
    items.sort(key=lambda x: x["rel"], reverse=True)
    return items


def save_upload(filename: str, data: bytes) -> Path:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("仅支持 png / jpg / jpeg / gif / webp / avif")
    if len(data) > MAX_SIZE:
        raise ValueError("图片不能超过 5MB")
    if not data:
        raise ValueError("文件为空")
    folder = MEDIA_ROOT / date.today().strftime("%Y/%m")
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{slugify(filename)}-{secrets.token_hex(3)}{ext}"
    p.write_bytes(data)
    return p


def delete_media(rel: str) -> None:
    p = safe_media_path(rel)
    if not p.is_file():
        raise FileNotFoundError("文件不存在")
    p.unlink()
    for d in sorted(p.parents, key=lambda x: len(x.parts), reverse=True):
        if d == MEDIA_ROOT:
            break
        try:
            d.rmdir()
        except OSError:
            break
