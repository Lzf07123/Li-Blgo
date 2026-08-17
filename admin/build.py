"""Hugo 构建薄封装：全量发布与草稿预览。"""

import os
import subprocess
import sys
import time

from admin.config import ROOT


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
