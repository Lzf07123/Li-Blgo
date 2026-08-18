import os
import re
import tempfile
import types
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("LIBLOG_BOOTSTRAP_BUILD", "0")

from admin import content as store, media, security
from admin.config import settings
from admin.db import connect, create_admin, init_db
from admin.main import app, build, rewrite_preview_html, safe_stats_href


class AdminRoutesTest(unittest.TestCase):
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
        r = client.get("/admin/")
        return re.search(r'name="_csrf" value="([^"]+)"', r.text).group(1)

    def test_preview_out_requires_login(self):
        target = settings.preview_root / "posts" / "draft" / "index.html"
        target.parent.mkdir(parents=True)
        target.write_text("<html>草稿</html>", encoding="utf-8")
        with TestClient(app) as client:
            r = client.get("/admin/preview-out/posts/draft/index.html", follow_redirects=False)
            self.assertEqual(r.status_code, 302)
            self._login(client)
            r = client.get("/admin/preview-out/posts/draft/index.html")
            self.assertEqual(r.status_code, 200)
            self.assertIn("草稿", r.text)

    def test_stats_javascript_href_sanitized(self):
        conn = connect()
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, 1)",
            ("javascript:alert(1)", "2026-08-18"),
        )
        conn.commit()
        conn.close()
        self.assertEqual(safe_stats_href("javascript:alert(1)"), "")
        self.assertEqual(safe_stats_href("/posts/ok/"), "/posts/ok/")
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/stats")
            self.assertNotIn('href="javascript:', r.text)

    def test_stats_csv_escapes_formula_and_quotes(self):
        conn = connect()
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, 1)",
            ('=HYPERLINK("https://evil")', "2026-08-18"),
        )
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, 1)",
            ('/posts/a"b', "2026-08-18"),
        )
        conn.commit()
        conn.close()
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/stats/export")
            self.assertEqual(r.status_code, 200)
            self.assertIn("'=HYPERLINK", r.text)
            self.assertIn('"/posts/a""b"', r.text)

    def test_rename_slug_removes_old_file(self):
        store.write_markdown(
            "posts", "old-slug", {"title": "Old", "date": "2026-08-18"}, "正文"
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/save",
                data={
                    "_csrf": csrf,
                    "slug": "old-slug",
                    "new_slug": "new-slug",
                    "action": "save_stay",
                    "title": "Renamed",
                    "date": "2026-08-18",
                    "status": "published",
                    "body": "新正文",
                },
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            self.assertFalse((settings.content_root / "posts" / "old-slug.md").exists())
            self.assertTrue((settings.content_root / "posts" / "new-slug.md").exists())

    def test_project_save_preserves_unknown_fields(self):
        store.write_markdown(
            "projects",
            "proj",
            {
                "title": "P",
                "date": "2026-08-18",
                "status": "active",
                "tech": [],
                "summary": "s",
                "badge": {"label": "B"},
                "show_on_home": False,
                "cover": "/img/x.png",
                "custom_field": "保留我",
            },
            "正文",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            client.post(
                "/admin/projects/save",
                data={
                    "_csrf": csrf,
                    "slug": "proj",
                    "new_slug": "",
                    "action": "save_stay",
                    "title": "P2",
                    "date": "2026-08-18",
                    "status": "active",
                    "repo": "",
                    "tech": "Docker",
                    "summary": "s2",
                    "badge_label": "B",
                    "badge_color": "",
                    "badge_href": "",
                    "body": "正文",
                },
                follow_redirects=False,
            )
        fm, _ = store.read_markdown("projects", "proj")
        self.assertEqual(fm["cover"], "/img/x.png")
        self.assertEqual(fm["custom_field"], "保留我")
        self.assertFalse(fm["show_on_home"])
        self.assertEqual(fm["tech"], ["Docker"])

    def test_logout_post_requires_csrf(self):
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post("/admin/logout", data={"_csrf": "bad"}, follow_redirects=False)
            self.assertEqual(r.status_code, 303)
            self.assertEqual(client.get("/admin/").status_code, 200)
            r = client.post("/admin/logout", data={"_csrf": csrf}, follow_redirects=False)
            self.assertEqual(r.status_code, 302)
            self.assertEqual(client.get("/admin/", follow_redirects=False).status_code, 302)

    def test_ip_whitelist_enforced(self):
        settings.ip_whitelist = ["203.0.113.10"]
        self.addCleanup(setattr, settings, "ip_whitelist", [])
        with TestClient(app) as client:
            r = client.get(
                "/admin/login", headers={"X-Forwarded-For": "203.0.113.9"}
            )
            self.assertEqual(r.status_code, 403)
            r = client.get(
                "/admin/login", headers={"X-Forwarded-For": "203.0.113.10"}
            )
            self.assertEqual(r.status_code, 200)

    def test_rewrite_preview_html_rewrites_assets(self):
        html = (
            '<link href="/css/style.css">'
            '<script src="/js/app.js"></script>'
            '<img src="/img/a.png">'
            '<div style="background:url(\'/img/b.png\')"></div>'
        )
        out = rewrite_preview_html(html, "admin")
        self.assertIn('href="/admin/static/css/style.css"', out)
        self.assertIn('src="/admin/static/js/app.js"', out)
        self.assertIn('src="/admin/preview-out/img/a.png"', out)
        self.assertIn("url('/admin/preview-out/img/b.png')", out)


if __name__ == "__main__":
    unittest.main()
