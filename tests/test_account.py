import re
import tempfile
import unittest
import urllib.parse
from pathlib import Path

from fastapi.testclient import TestClient

from admin import content as store, media, security
from admin.config import settings
from admin.db import connect, create_admin, get_admin, init_db
from admin.main import app


class AccountRoutesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        settings.db_path = root / "blog.db"
        settings.content_root = root / "content"
        settings.config_root = root / "config"
        settings.output_root = root / "output"
        settings.preview_root = root / "preview"
        settings.beacon_log = root / "beacon.log"
        settings.ip_whitelist = []
        media.MEDIA_ROOT = root / "img"
        (settings.content_root / "posts").mkdir(parents=True)
        (settings.content_root / "projects").mkdir(parents=True)
        settings.config_root.mkdir(parents=True)
        settings.preview_root.mkdir(parents=True)
        media.MEDIA_ROOT.mkdir(parents=True)
        (settings.config_root / "brand.yaml").write_text(
            "name: Audit\nlogo: ''\n", encoding="utf-8"
        )
        init_db()
        conn = connect()
        create_admin(conn, "admin", security.hash_password("Li&Blog@2026"))
        conn.commit()
        conn.close()

    def tearDown(self):
        self._tmp.cleanup()

    def _login(self, client: TestClient) -> str:
        r = client.get("/admin/login")
        csrf0 = re.search(r'name="_csrf" value="([^"]+)"', r.text).group(1)
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "Li&Blog@2026", "_csrf": csrf0},
            follow_redirects=False,
        )
        r = client.get("/admin/settings/account")
        return re.search(r'name="_csrf" value="([^"]+)"', r.text).group(1)

    def test_change_username_and_password(self):
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/settings/account",
                data={
                    "_csrf": csrf,
                    "current_password": "Li&Blog@2026",
                    "new_username": "newadmin",
                    "new_password": "NewPass@2026",
                    "confirm": "NewPass@2026",
                },
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            conn = connect()
            admin = get_admin(conn)
            conn.close()
            self.assertEqual(admin["username"], "newadmin")
            self.assertTrue(security.verify_password("NewPass@2026", admin["password_hash"]))

    def test_wrong_current_password_rejected(self):
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/settings/account",
                data={
                    "_csrf": csrf,
                    "current_password": "wrong",
                    "new_username": "newadmin",
                    "new_password": "",
                    "confirm": "",
                },
                follow_redirects=False,
            )
            location = urllib.parse.unquote(r.headers.get("location", ""))
            self.assertIn("当前密码不正确", location)

    def test_logs_page_records_login(self):
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/logs")
            self.assertEqual(r.status_code, 200)
            self.assertIn("登录成功", r.text)


if __name__ == "__main__":
    unittest.main()
