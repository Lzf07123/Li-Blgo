"""文章修订历史：每次保存快照到 data/revisions/，支持查看与恢复。"""

import re
import time
from pathlib import Path

import yaml

from admin.config import settings

TS_RE = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")


def _revision_root() -> Path:
    return settings.db_path.parent / "revisions"


def save_revision(section: str, slug: str, frontmatter: dict, body: str) -> None:
    """保存当前版本快照（仅文章栏目），并按上限清理最旧快照。"""
    if section != "posts":
        return
    directory = _revision_root() / section / slug
    directory.mkdir(parents=True, exist_ok=True)
    base_ts = time.strftime("%Y%m%d-%H%M%S")
    target = directory / f"{base_ts}.md"
    index = 1
    while target.exists():
        target = directory / f"{base_ts}-{index}.md"
        index += 1
    text = (
        f"---\n"
        f"{yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()}\n"
        f"---\n\n{body.strip()}\n"
    )
    target.write_text(text, encoding="utf-8")
    files = sorted(directory.glob("*.md"))
    for old in files[: -max(settings.revision_max, 1)]:
        old.unlink()


def list_revisions(section: str, slug: str) -> list[str]:
    if section != "posts":
        return []
    directory = _revision_root() / section / slug
    if not directory.exists():
        return []
    return sorted((p.stem for p in directory.glob("*.md")), reverse=True)


def read_revision(section: str, slug: str, ts: str) -> tuple[dict, str]:
    if section != "posts" or not TS_RE.match(ts):
        raise ValueError("bad revision")
    root = settings.db_path.parent.resolve()
    target = (root / "revisions" / section / slug / f"{ts}.md").resolve()
    if not target.is_relative_to(root / "revisions"):
        raise ValueError("path escape")
    text = target.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return (yaml.safe_load(parts[1]) or {}), parts[2].lstrip("\n")
    return {}, text
