"""Hugo 构建薄封装：全量发布与草稿预览。"""

import os
import subprocess
import sys
import time

from admin.config import ROOT
from scripts.build import verify_output


def _run(args, timeout=180):
    env = dict(os.environ)
    env.setdefault("GOMEMLIMIT", "256MiB")
    env.setdefault("HUGO_NUMWORKERMULTIPLIER", "0.5")
    env.setdefault("HUGO_BIN", "hugo")
    started = time.time()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py"), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result, round(time.time() - started, 2)


def run_full():
    return _run(["--full"])


def run_preview():
    return _run(["--preview"])


def output_info() -> dict:
    """返回 output/ 产物信息：体积、文件数、构建时间与完整性。"""
    from admin.config import settings

    out = settings.output_root
    index_file = out / "index.html"
    if not index_file.exists():
        return {}
    total = 0
    count = 0
    for p in out.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            count += 1
    issues = verify_output(out)
    return {
        "size_mb": round(total / 1024 / 1024, 2),
        "file_count": count,
        "mtime": index_file.stat().st_mtime,
        "ok": not issues,
    }
