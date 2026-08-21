"""后台异步构建：保存/上传/批量等操作不再同步等待 Hugo 构建。

POST 只负责落盘并立即 303 跳转；全量构建由后台线程串行执行，
前端通过 /admin/build/status 轮询进度。连续多次触发会合并为一次 pending 重跑，
避免排队堆积；构建失败的错误尾部会保留在状态中供前端展示。

注意：状态保存在进程内存，适用于 compose 中 uvicorn 单进程部署；
多 worker 场景需要外置状态（如 SQLite/Redis）。
"""

import threading
import time
from typing import Optional

_lock = threading.Lock()
_state: dict = {
    "status": "idle",  # idle | queued | running | success | failed
    "started_at": None,
    "finished_at": None,
    "elapsed": None,  # 秒
    "ok": None,
    "error": None,  # 失败时的 stderr 尾部
    "pending": False,  # 构建期间又有新触发，跑完后再跑一次
    "pending_source": "",  # 合并触发时记录最新来源
    "source": "",
}
_worker: Optional[threading.Thread] = None

# 成功/失败结果在页面上保留展示的时长（秒）
SUCCESS_KEEP_SECONDS = 20
FAILURE_KEEP_SECONDS = 60


def snapshot() -> dict:
    """供 /build/status 返回；运行时 elapsed 实时计算。"""
    with _lock:
        s = dict(_state)
    if s["status"] == "running" and s["started_at"]:
        s["elapsed"] = round(time.time() - s["started_at"], 1)
    return s


def trigger_build(source: str = "") -> bool:
    """触发一次后台全量构建；已有构建进行中则合并为 pending 重跑。

    返回 True 表示本次调用启动了构建线程；False 表示已在进行/排队。
    """
    global _worker
    with _lock:
        if _state["status"] in ("queued", "running"):
            _state["pending"] = True
            if source:
                _state["pending_source"] = source
            return False
        _state.update(
            status="queued",
            started_at=time.time(),
            finished_at=None,
            elapsed=None,
            ok=None,
            error=None,
            pending=False,
            source=source,
        )
        _worker = threading.Thread(target=_run_loop, name="blog-build", daemon=True)
        _worker.start()
        return True


def _run_loop() -> None:
    """后台串行构建循环：跑完一次后若期间有新触发则再跑一次。"""
    from admin import build

    while True:
        with _lock:
            _state["status"] = "running"
            started = _state["started_at"]
        try:
            result, elapsed = build.run_full()
            ok = result.returncode == 0
            error = ""
            if not ok:
                tail = (result.stderr or result.stdout or "").strip()[-300:]
                error = tail or f"退出码 {result.returncode}"
        except Exception as exc:  # noqa: BLE001 - 后台构建失败只记录状态
            ok, elapsed, error = False, None, str(exc)
        with _lock:
            _state.update(
                status="success" if ok else "failed",
                finished_at=time.time(),
                elapsed=elapsed,
                ok=ok,
                error=error,
            )
            if _state["pending"]:
                _state["pending"] = False
                _state["status"] = "queued"
                _state["source"] = _state["pending_source"] or _state["source"]
                _state["pending_source"] = ""
                _state["started_at"] = time.time()
                _state["finished_at"] = None
                _state["elapsed"] = None
                _state["ok"] = None
                _state["error"] = None
                continue
        break
