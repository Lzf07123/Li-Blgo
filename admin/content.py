"""内容读写层：Markdown/YAML 文件是唯一事实来源，路径一律防穿越。"""

import re
from pathlib import Path

import yaml

from admin.config import settings

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def safe_resolve(root: Path, rel: str) -> Path:
    root_r = root.resolve()
    p = (root_r / rel).resolve()
    if not p.is_relative_to(root_r):
        raise ValueError("path escape")
    return p


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                return {}
    return {}


def list_markdown(section: str, q: str = "", status: str = "") -> list[dict]:
    directory = settings.content_root / section
    if not directory.exists():
        return []
    items = []
    for p in sorted(directory.glob("*.md")):
        fm = _read_frontmatter(p)
        items.append(
            {
                "slug": p.stem,
                "title": fm.get("title", p.stem),
                "date": fm.get("date", ""),
                "status": fm.get("status", "published"),
                "tags": fm.get("tags") or [],
            }
        )
    if q:
        ql = q.lower()
        items = [
            it
            for it in items
            if ql in it["title"].lower()
            or ql in it["slug"].lower()
            or any(ql in str(t).lower() for t in it["tags"])
        ]
    if status and section == "posts":
        items = [it for it in items if it["status"] == status]
    return items


def read_markdown(section: str, slug: str) -> tuple[dict, str]:
    if not SLUG_RE.match(slug):
        raise ValueError("bad slug")
    p = safe_resolve(settings.content_root, f"{section}/{slug}.md")
    text = p.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) >= 3:
        try:
            return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")
        except yaml.YAMLError:
            return {}, text
    return {}, text


def write_markdown(section: str, slug: str, frontmatter: dict, body: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError("bad slug")
    fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    text = f"---\n{fm}\n---\n\n{body.strip()}\n"
    p = safe_resolve(settings.content_root, f"{section}/{slug}.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def read_page(name: str) -> tuple[dict, str]:
    """读取 content/<name>.md（根级单页，如 about/resources）。"""
    p = safe_resolve(settings.content_root, f"{name}.md")
    return _read_page_file(p)


def _read_page_file(p: Path) -> tuple[dict, str]:
    text = p.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) >= 3:
        try:
            return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")
        except yaml.YAMLError:
            return {}, text
    return {}, text


def write_page(name: str, frontmatter: dict, body: str) -> None:
    """写入 content/<name>.md（根级单页）。"""
    fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    text = f"---\n{fm}\n---\n\n{body.strip()}\n"
    p = safe_resolve(settings.content_root, f"{name}.md")
    p.write_text(text, encoding="utf-8")


def delete_markdown(section: str, slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError("bad slug")
    p = safe_resolve(settings.content_root, f"{section}/{slug}.md")
    if p.exists():
        p.unlink()


def load_yaml(name: str) -> dict:
    p = safe_resolve(settings.config_root, f"{name}.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def save_yaml(name: str, data: dict) -> None:
    p = safe_resolve(settings.config_root, f"{name}.yaml")
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    p.write_text(f"# {name}.yaml（后台保存生成）\n{text}", encoding="utf-8")
