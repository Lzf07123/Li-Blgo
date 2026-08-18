"""媒体库：上传 / 列出 / 删除主题静态图片（themes/blog-theme/static/img/）。

主流光栅格式（png/jpg/jpeg/gif/webp/avif）均可上传；尺寸或体积超过阈值时
自动缩放到合适范围并优化编码。
"""

import io
import re
import secrets
import unicodedata
import os
from datetime import date
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from admin.config import ROOT

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}
MAX_SIZE = 5 * 1024 * 1024
MAX_DIMENSION = 1600
OPTIMIZE_BYTES = 1_500_000
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


def _optimize_image(data: bytes) -> bytes:
    """过大/过重的静态图片自动缩放到 MAX_DIMENSION 内并优化体积。"""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except UnidentifiedImageError:
        raise ValueError("无法识别的图片文件")
    fmt = (img.format or "").upper()
    if getattr(img, "is_animated", False):
        return data
    too_large = max(img.size) > MAX_DIMENSION
    too_heavy = len(data) > OPTIMIZE_BYTES
    if not too_large and not too_heavy:
        return data
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    if fmt in ("JPEG", "JPG"):
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=88, optimize=True)
    elif fmt == "PNG":
        img.save(out, format="PNG", optimize=True)
    elif fmt == "WEBP":
        img.save(out, format="WEBP", quality=88, method=6)
    elif fmt == "GIF":
        img.save(out, format="GIF", optimize=True)
    elif fmt == "AVIF":
        try:
            img.save(out, format="AVIF", quality=80)
        except Exception:
            return data
    else:
        return data
    result = out.getvalue()
    if not result:
        return data
    if too_large:
        return result
    return result if len(result) < len(data) else data


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
    p.write_bytes(_optimize_image(data))
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
