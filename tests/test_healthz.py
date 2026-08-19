import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from admin.config import settings
from admin.main import app


class TestHealthz(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings.db_path = Path(self._tmp.name) / "blog.db"
        settings.beacon_log = Path(self._tmp.name) / "beacon.log"

    def tearDown(self):
        self._tmp.cleanup()

    def test_healthz_ok(self):
        with TestClient(app) as client:
            resp = client.get("/healthz")
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
        self.assertIn("build", resp.json())


if __name__ == "__main__":
    unittest.main()
