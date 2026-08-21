"""文章批量导入：多选 Markdown 或 ZIP，统一写入 content/posts 并返回统计。"""

import io
import hashlib
import re
import unicodedata
import zipfile
from datetime import date
from pathlib import PurePosixPath

import yaml

from admin import content
from admin.config import settings

MD_SUFFIXES = (".md", ".markdown")
SKIP_STEMS = {"_index", "index"}


def parse_document(filename: str, text: str) -> tuple[str, dict, str]:
    """解析单个 Markdown 文档，返回 (slug, frontmatter, body)。"""
    parts = text.split("---", 2)
    if len(parts) >= 3 and not parts[0].strip():
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"{filename}: frontmatter 解析失败") from exc
        body = parts[2].lstrip("\n")
    else:
        fm, body = {}, text
    if not isinstance(fm, dict):
        raise ValueError(f"{filename}: frontmatter 必须是键值对")
    explicit = str(fm.pop("slug", "")).strip("/")
    stem = PurePosixPath(filename).stem
    slug = _resolve_slug(explicit, stem, fm.get("title", ""), filename)
    if not fm.get("title"):
        fm["title"] = _infer_title(stem, body)
    if not fm.get("date"):
        fm["date"] = _infer_date(stem)
    fm.setdefault("status", "published")
    if isinstance(fm.get("tags"), str):
        fm["tags"] = [t.strip() for t in fm["tags"].split(",") if t.strip()]
    elif not isinstance(fm.get("tags"), list):
        fm["tags"] = []
    return slug, fm, body


def _resolve_slug(explicit: str, stem: str, title: str, filename: str) -> str:
    """按 显式 slug → 文件名 → 标题 → 稳定哈希 的顺序生成合法标识。"""
    if explicit:
        candidate = _slugify(explicit)
        if content.SLUG_RE.match(candidate):
            return candidate
        raise ValueError(f"{filename}: 非法标识 {explicit!r}（仅允许小写字母/数字/中划线）")
    for source in (stem, title):
        candidate = _slugify(source)
        if content.SLUG_RE.match(candidate):
            return candidate
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()[:10]
    return f"post-{digest}"


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug[:64].strip("-")


def _infer_title(stem: str, body: str) -> str:
    """无 frontmatter title 时，优先取首个 # 标题，否则用文件名。"""
    m = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    if m:
        return m.group(1).strip()
    cleaned = re.sub(r"^\d{4}[-_]?\d{2}[-_]?\d{2}[-_]?", "", stem).strip("- ")
    return cleaned or stem


def _infer_date(stem: str) -> str:
    """无 frontmatter date 时，从 YYYY-MM-DD / YYYYMMDD 前缀文件名推断。"""
    m = re.match(r"^(\d{4})[-_]?(\d{2})[-_]?(\d{2})", stem)
    if m:
        try:
            return date(
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            ).isoformat()
        except ValueError:
            pass
    return date.today().isoformat()


def extract_zip(data: bytes) -> tuple[list[tuple[str, bytes]], list[str]]:
    """从 ZIP 中取出全部 Markdown 文件（扁平化，校验路径安全与大小）。

    返回 (entries, errors)：不合规的单个条目直接跳过并记入 errors，
    不中断其余条目的提取；仅 ZIP 容器本身无法解析时抛 ValueError。
    """
    out: list[tuple[str, bytes]] = []
    errors: list[str] = []
    total = 0
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("ZIP 文件无法解析") from exc
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts:
                errors.append(f"ZIP 含非法路径，已跳过: {name}")
                continue
            if not name.lower().endswith(MD_SUFFIXES):
                continue
            if info.file_size > settings.import_max_file_bytes:
                errors.append(f"{name} 超过单文件大小限制，已跳过")
                continue
            if len(out) >= settings.import_max_files:
                errors.append(f"ZIP 内 Markdown 文件数量超过限制，其余已跳过")
                break
            total += info.file_size
            if total > settings.import_max_zip_bytes:
                errors.append("ZIP 解压后超过大小限制，后续文件已跳过")
                break
            try:
                out.append((p.name, zf.read(info)))
            except (RuntimeError, NotImplementedError) as exc:
                errors.append(f"{name}: 无法读取（加密或损坏），已跳过")
    return out, errors


def import_posts(
    entries: list[tuple[str, bytes]], overwrite: bool = False
) -> dict:
    """写入文章并返回 {imported, skipped, errors}。

    每个文件独立校验：不符合导入要求的条目逐项跳过并记入 errors，
    不中断其余文件的导入；超过单次数量上限时仅处理前 N 个并记录提示。
    """
    result = {"imported": 0, "skipped": 0, "errors": [], "files": []}
    if len(entries) > settings.import_max_files:
        result["errors"].append(
            f"超过单次导入数量上限（{settings.import_max_files}），其余文件已跳过"
        )
        entries = entries[: settings.import_max_files]
    seen = set()
    for filename, data in entries:
        if not filename.strip():
            result["errors"].append("缺少文件名")
            continue
        if not filename.lower().endswith(MD_SUFFIXES):
            result["errors"].append(f"{filename}: 不支持的文件类型")
            continue
        if PurePosixPath(filename).stem in SKIP_STEMS or filename.startswith("."):
            result["skipped"] += 1
            continue
        if len(data) > settings.import_max_file_bytes:
            result["errors"].append(f"{filename}: 超过单文件大小限制")
            continue
        try:
            text = data.decode("utf-8-sig", errors="replace")
            if not text.strip():
                result["errors"].append(f"{filename}: 文件内容为空，已跳过")
                continue
            slug, fm, body = parse_document(filename, text)
        except ValueError as exc:
            result["errors"].append(str(exc))
            continue
        if slug in seen:
            result["skipped"] += 1
            continue
        seen.add(slug)
        if content.markdown_exists("posts", slug) and not overwrite:
            result["skipped"] += 1
            continue
        try:
            content.write_markdown("posts", slug, fm, body)
        except ValueError as exc:
            result["errors"].append(f"{filename}: {exc}")
            continue
        result["imported"] += 1
        result["files"].append(
            {
                "filename": filename,
                "slug": slug,
                "title": fm.get("title", slug),
                "date": str(fm.get("date", "")),
                "tags": fm.get("tags") or [],
            }
        )
    return result
