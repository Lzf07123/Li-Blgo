import tempfile
import unittest
from pathlib import Path

from admin import session
from admin.config import settings
from admin.db import connect, init_db


class TestSession(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings.db_path = Path(self._tmp.name) / "blog.db"
        init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def test_session_roundtrip(self):
        sid = session.create_session("local")
        row = session.get_session(sid)
        self.assertIsNotNone(row)
        self.assertEqual(row["kind"], "local")
        session.delete_session(sid)
        self.assertIsNone(session.get_session(sid))

    def test_delete_by_oidc(self):
        sid = session.create_session("oidc", sub="uuid-1", sid="portal-sess")
        session.delete_by_oidc("uuid-1", "portal-sess")
        self.assertIsNone(session.get_session(sid))


if __name__ == "__main__":
    unittest.main()
