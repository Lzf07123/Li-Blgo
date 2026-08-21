"""后台异步构建状态：触发、合并、失败与快照。"""

import threading
import time
import types
import unittest
from unittest import mock

from admin import build as build_mod
from admin import buildstate


def wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class BuildStateTest(unittest.TestCase):
    def setUp(self):
        # 等待上一测试遗留构建结束，保证状态干净
        wait_until(lambda: buildstate.snapshot()["status"] in ("idle", "success", "failed"))

    def tearDown(self):
        # 让可能仍在跑的构建结束，避免污染后续用例
        wait_until(lambda: buildstate.snapshot()["status"] in ("idle", "success", "failed"), 5.0)

    def test_trigger_success(self):
        with mock.patch.object(
            build_mod,
            "run_full",
            return_value=(types.SimpleNamespace(returncode=0, stderr=""), 0.42),
        ) as run:
            self.assertTrue(buildstate.trigger_build("test_success"))
            self.assertTrue(
                wait_until(lambda: buildstate.snapshot()["status"] == "success")
            )
            s = buildstate.snapshot()
            self.assertTrue(s["ok"])
            self.assertEqual(s["elapsed"], 0.42)
            self.assertEqual(s["source"], "test_success")
            run.assert_called_once_with()

    def test_trigger_failure_keeps_error_tail(self):
        stderr = "ERROR: boom\n" * 200
        with mock.patch.object(
            build_mod,
            "run_full",
            return_value=(types.SimpleNamespace(returncode=2, stderr=stderr, stdout=""), 1.1),
        ):
            buildstate.trigger_build("test_failure")
            self.assertTrue(
                wait_until(lambda: buildstate.snapshot()["status"] == "failed")
            )
            s = buildstate.snapshot()
            self.assertFalse(s["ok"])
            self.assertLessEqual(len(s["error"]), 300)
            self.assertIn("boom", s["error"])

    def test_trigger_while_running_merges_pending(self):
        gate = threading.Event()
        calls = []

        def fake_run_full():
            calls.append(time.time())
            gate.wait(10)  # 第一次构建挂起，模拟“进行中”
            return types.SimpleNamespace(returncode=0, stderr=""), 0.1

        with mock.patch.object(build_mod, "run_full", side_effect=fake_run_full):
            self.assertTrue(buildstate.trigger_build("first"))
            # 等待进入 running
            self.assertTrue(
                wait_until(lambda: buildstate.snapshot()["status"] == "running")
            )
            # 第二次触发不新起线程，仅标记 pending
            self.assertFalse(buildstate.trigger_build("second"))
            gate.set()  # 放行第一次
            self.assertTrue(
                wait_until(lambda: buildstate.snapshot()["status"] == "success")
            )
            # pending 合并后应再跑一次
            self.assertEqual(len(calls), 2)
            self.assertEqual(buildstate.snapshot()["source"], "second")

    def test_snapshot_elapsed_updates_while_running(self):
        gate = threading.Event()

        def fake_run_full():
            gate.wait(10)
            return types.SimpleNamespace(returncode=0, stderr=""), 0.1

        with mock.patch.object(build_mod, "run_full", side_effect=fake_run_full):
            buildstate.trigger_build("elapsed")
            self.assertTrue(
                wait_until(lambda: buildstate.snapshot()["status"] == "running")
            )
            time.sleep(0.15)
            s = buildstate.snapshot()
            self.assertGreaterEqual(s["elapsed"], 0.1)
            gate.set()


if __name__ == "__main__":
    unittest.main()
