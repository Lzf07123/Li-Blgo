"""站点备份：content/config/媒体/SQLite/hugo.toml 打包为 ZIP。"""

import io
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from admin import media
from admin.config import ROOT, settings


def build_backup_zip() -> bytes:
    buf = io.BytesIO()
    manifest = {
        "app": "Li&Blog",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sections": {},
    }
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest["sections"]["content"] = _add_dir(
            zf, "content", settings.content_root
        )
        manifest["sections"]["config"] = _add_dir(zf, "config", settings.config_root)
        manifest["sections"]["media"] = _add_dir(
            zf, "themes/blog-theme/static/img", media.MEDIA_ROOT
        )
        manifest["sections"]["database"] = _add_sqlite(
            zf, settings.db_path, "data/blog.db"
        )
        hugo = ROOT / "hugo.toml"
        if hugo.exists():
            zf.write(hugo, "hugo.toml")
        zf.writestr(
            "backup-manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    return buf.getvalue()


def _add_dir(zf: zipfile.ZipFile, arc_prefix: str, src: Path) -> int:
    count = 0
    if not src.exists():
        return count
    for p in sorted(src.rglob("*")):
        if p.is_file():
            zf.write(p, f"{arc_prefix}/{p.relative_to(src).as_posix()}")
            count += 1
    return count


def _add_sqlite(zf: zipfile.ZipFile, db_path: Path, arc_name: str) -> int:
    """用 SQLite backup API 导出一致性快照，避免拷贝过程中写入不一致。"""
    if not db_path.exists():
        return 0
    tmp = Path(tempfile.mkdtemp()) / "blog.db"
    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        zf.write(tmp, arc_name)
    finally:
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()
    return 1
