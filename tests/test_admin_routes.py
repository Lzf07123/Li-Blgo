import os
import re
import tempfile
import types
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

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

    def test_batch_import_rejects_empty_markdown(self):
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/import",
                data={"_csrf": csrf},
                files={"files": ("untitled.md", b"", "text/markdown")},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 200)
            self.assertIn("文件内容为空", r.text)
            self.assertFalse(
                (settings.content_root / "posts" / "untitled.md").exists()
            )

    def test_batch_import_page_lists_pending_files(self):
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts/import")
            self.assertEqual(r.status_code, 200)
            self.assertIn('id="import-pending"', r.text)
            self.assertIn('id="import-pending-list"', r.text)
            self.assertIn('addEventListener("change"', r.text)

    def test_custom_dropdown_referenced_on_list_and_base(self):
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts")
            self.assertEqual(r.status_code, 200)
            self.assertIn('data-custom-dropdown', r.text)
            self.assertIn('name="per_page" aria-label="每页条数" data-custom-dropdown', r.text)
            r = client.get("/admin/static/js/admin-dropdown.js")
            self.assertEqual(r.status_code, 200)
            self.assertIn("custom-select", r.text)

    def test_bulk_checkboxes_attached_to_bulk_form(self):
        store.write_markdown(
            "posts",
            "bulk-ui",
            {"title": "Bulk UI", "date": "2026-08-18", "status": "published"},
            "正文",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts")
            self.assertEqual(r.status_code, 200)
            self.assertIn('<form id="bulk-form"', r.text)
            self.assertIn('form="bulk-form"', r.text)

    def test_row_actions_confirm_use_data_attribute(self):
        store.write_markdown(
            "posts",
            "confirm-ui",
            {"title": "Confirm UI", "date": "2026-08-18", "status": "published"},
            "正文",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts")
            self.assertEqual(r.status_code, 200)
            self.assertIn('data-confirm="确定移入回收站', r.text)
            self.assertIn("form[data-confirm]", r.text)
            self.assertNotIn('onsubmit="return confirm', r.text)

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

    def test_trash_restore_cycle(self):
        store.write_markdown(
            "posts",
            "trash-me",
            {"title": "Trash", "date": "2026-08-18", "status": "published"},
            "正文",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/trash-me/trash",
                data={"_csrf": csrf},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            self.assertFalse((settings.content_root / "posts" / "trash-me.md").exists())
            self.assertEqual(len(store.list_trash()), 1)
            r = client.get("/admin/trash")
            self.assertIn("Trash", r.text)
            r = client.post(
                "/admin/trash/posts/trash-me/restore",
                data={"_csrf": csrf},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            self.assertTrue((settings.content_root / "posts" / "trash-me.md").exists())
            self.assertEqual(store.list_trash(), [])

    def test_duplicate_creates_draft(self):
        store.write_markdown(
            "posts",
            "source",
            {"title": "Source", "date": "2026-08-18", "status": "published"},
            "正文内容",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/source/duplicate",
                data={"_csrf": csrf},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, body = store.read_markdown("posts", "source-2")
        self.assertEqual(fm["status"], "draft")
        self.assertEqual(body.strip(), "正文内容")
        self.assertIn("副本", fm["title"])

    def test_slug_check_json(self):
        store.write_markdown(
            "posts",
            "exists",
            {"title": "E", "date": "2026-08-18"},
            "正文",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts/slug-check?slug=exists")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), {"valid": True, "exists": True})
            r = client.get("/admin/posts/slug-check?slug=free")
            self.assertEqual(r.json(), {"valid": True, "exists": False})
            r = client.get("/admin/posts/slug-check?slug=BAD SLUG")
            self.assertEqual(r.json(), {"valid": False, "exists": False})

    def test_bulk_add_remove_tag(self):
        for slug in ("a", "b"):
            store.write_markdown(
                "posts",
                slug,
                {"title": slug, "date": "2026-08-18", "tags": ["old"]},
                "正文",
            )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/bulk",
                data={"_csrf": csrf, "action": "add_tag", "tag": "new", "slugs": ["a", "b"]},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            fm, _ = store.read_markdown("posts", "a")
            self.assertIn("new", fm["tags"])
            r = client.post(
                "/admin/posts/bulk",
                data={"_csrf": csrf, "action": "remove_tag", "tag": "old", "slugs": ["a", "b"]},
                follow_redirects=False,
            )
            fm, _ = store.read_markdown("posts", "b")
            self.assertNotIn("old", fm["tags"])

    def test_media_unused_filter(self):
        (media.MEDIA_ROOT / "unused.png").write_bytes(b"png")
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/media?unused=1")
            self.assertEqual(r.status_code, 200)
            self.assertIn("unused.png", r.text)
            self.assertIn("可放心清理", r.text)
            self.assertIn("全部图片", r.text)

    def test_dashboard_widgets(self):
        store.write_markdown(
            "posts",
            "future",
            {"title": "未来文章", "date": "2099-01-01", "status": "published"},
            "正文",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/")
            self.assertIn("最近活动", r.text)
            self.assertIn("内容体检", r.text)
            self.assertIn("定时文章", r.text)
            self.assertIn("未来文章", r.text)

    def test_stats_path_maps_to_title(self):
        store.write_markdown(
            "posts",
            "mapped",
            {"title": "可读标题", "date": "2026-08-18"},
            "正文",
        )
        conn = connect()
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, 1)",
            ("/posts/mapped/", "2026-08-19"),
        )
        conn.commit()
        conn.close()
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/stats")
            self.assertIn("可读标题", r.text)
            self.assertIn("/posts/mapped/", r.text)

    def test_logs_kind_filter_and_pagination(self):
        conn = connect()
        for i in range(3):
            conn.execute(
                "INSERT INTO audit_log (at, kind, detail) VALUES (?, ?, ?)",
                (1000 + i, "content_save", f"posts/{i}"),
            )
        conn.commit()
        conn.close()
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/logs?kind=content_save")
            self.assertIn("posts/0", r.text)
            r = client.get("/admin/logs?kind=login_ok")
            self.assertNotIn("posts/0", r.text)

    def test_publish_now_sets_today(self):
        import datetime

        store.write_markdown(
            "posts",
            "future-now",
            {"title": "F", "date": "2099-01-01", "status": "published"},
            "正文",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/future-now/publish-now",
                data={"_csrf": csrf},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, _ = store.read_markdown("posts", "future-now")
        self.assertEqual(fm["date"], datetime.date.today().isoformat())

    def test_post_save_writes_cover_field(self):
        store.write_markdown(
            "posts",
            "cover-post",
            {"title": "C", "date": "2026-08-18", "status": "published"},
            "正文",
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
                    "slug": "cover-post",
                    "new_slug": "",
                    "action": "save_stay",
                    "title": "C2",
                    "date": "2026-08-18",
                    "status": "published",
                    "cover": "/img/2026/08/cover.webp",
                    "body": "正文",
                },
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, _ = store.read_markdown("posts", "cover-post")
        self.assertEqual(fm["cover"], "/img/2026/08/cover.webp")
        self.assertTrue(
            (settings.db_path.parent / "revisions" / "posts" / "cover-post").exists()
        )

    def test_save_draft_sets_hugo_draft_flag(self):
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/save",
                data={
                    "_csrf": csrf,
                    "slug": "",
                    "new_slug": "draft-flag",
                    "action": "save_stay",
                    "title": "D",
                    "date": "2026-08-20",
                    "status": "draft",
                    "body": "正文",
                },
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, _ = store.read_markdown("posts", "draft-flag")
        self.assertIs(fm["draft"], True)
        self.assertEqual(fm["status"], "draft")

    def test_publish_removes_hugo_draft_flag(self):
        store.write_markdown(
            "posts",
            "draft-flag-2",
            {"title": "D2", "date": "2026-08-20", "status": "draft"},
            "正文",
        )
        self.assertIs(store.read_markdown("posts", "draft-flag-2")[0]["draft"], True)
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/draft-flag-2/status",
                data={"_csrf": csrf, "status": "published"},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, _ = store.read_markdown("posts", "draft-flag-2")
        self.assertIs(fm["draft"], False)

    def test_posts_list_groups_rows_by_year(self):
        store.write_markdown(
            "posts", "old-post",
            {"title": "旧文", "date": "2025-03-01", "status": "published"},
            "正文",
        )
        store.write_markdown(
            "posts", "new-post",
            {"title": "新文", "date": "2026-08-18", "status": "published"},
            "正文",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/posts?sort=date&order=desc")
            self.assertEqual(r.status_code, 200)
            self.assertIn("table-group-row", r.text)
            self.assertIn("2026", r.text)
            self.assertIn("2025", r.text)

    def test_posts_bulk_publish_and_delete(self):
        store.write_markdown(
            "posts", "bulk-a",
            {"title": "A", "date": "2026-08-18", "status": "draft"},
            "正文",
        )
        store.write_markdown(
            "posts", "bulk-b",
            {"title": "B", "date": "2026-08-18", "status": "draft"},
            "正文",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/posts/bulk",
                data={"_csrf": csrf, "action": "publish", "slugs": ["bulk-a", "bulk-b"]},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            self.assertEqual(
                store.read_markdown("posts", "bulk-a")[0]["status"], "published"
            )
            r = client.post(
                "/admin/posts/bulk",
                data={"_csrf": csrf, "action": "delete", "slugs": ["bulk-a"]},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
            self.assertFalse((settings.content_root / "posts" / "bulk-a.md").exists())

    def test_tags_rename_updates_posts(self):
        store.write_markdown(
            "posts", "tag-a",
            {"title": "A", "date": "2026-08-18", "tags": ["old", "keep"]},
            "正文",
        )
        original = build.run_full
        build.run_full = lambda: (types.SimpleNamespace(returncode=0, stderr=""), 0.01)
        self.addCleanup(setattr, build, "run_full", original)
        with TestClient(app) as client:
            csrf = self._login(client)
            r = client.post(
                "/admin/tags/apply",
                data={
                    "_csrf": csrf,
                    "old_tag": "old",
                    "new_tag": "renamed",
                    "action": "rename",
                },
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 303)
        fm, _ = store.read_markdown("posts", "tag-a")
        self.assertEqual(fm["tags"], ["keep", "renamed"])

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

    def test_config_save_write_failure_redirects_not_500(self):
        with TestClient(app) as client:
            csrf = self._login(client)
            with mock.patch(
                "admin.content.save_yaml", side_effect=OSError("readonly fs")
            ):
                r = client.post(
                    "/admin/config/brand",
                    data={"_csrf": csrf},
                    follow_redirects=False,
                )
            self.assertEqual(r.status_code, 303)
            location = urllib.parse.unquote(r.headers.get("location", ""))
            self.assertIn("不可写", location)

    def test_profile_form_uses_row_indexed_input_names(self):
        (settings.config_root / "profile.yaml").write_text(
            "name: T\n"
            "skills:\n"
            "- name: A\n  icon: a\n"
            "- name: B\n  icon: b\n",
            encoding="utf-8",
        )
        with TestClient(app) as client:
            self._login(client)
            r = client.get("/admin/config/profile")
            self.assertEqual(r.status_code, 200)
            self.assertIn('name="skills[0][name]"', r.text)
            self.assertIn('name="skills[1][name]"', r.text)
            self.assertIn('name="skills[0][icon]"', r.text)
            self.assertNotIn('name="skills[2][name]"', r.text)

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
