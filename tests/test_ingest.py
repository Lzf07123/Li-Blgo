import tempfile
import unittest
from pathlib import Path

from admin.config import settings
from admin.db import canonical_stats_path, connect, init_db, normalize_stats_paths
from admin.ingest import beacon_page, import_beacon_log, valid_site_path


class TestBeaconParsing(unittest.TestCase):
    def test_beacon_page_decodes_encoded_path(self):
        uri = "/api/beacon?p=%2fposts%2fmarkdown-guide%2f"
        self.assertEqual(beacon_page(uri), "/posts/markdown-guide/")

    def test_beacon_page_keeps_plain_path(self):
        uri = "/api/beacon?p=/posts/plain/"
        self.assertEqual(beacon_page(uri), "/posts/plain/")

    def test_beacon_page_decodes_cjk_once(self):
        uri = "/api/beacon?p=%2ftags%2f%25E5%2586%2599%25E4%25BD%259C%2f"
        self.assertEqual(beacon_page(uri), "/tags/%E5%86%99%E4%BD%9C/")

    def test_canonical_stats_path_encodes_cjk(self):
        self.assertEqual(canonical_stats_path("/tags/约定/"), "/tags/%E7%BA%A6%E5%AE%9A/")
        self.assertEqual(canonical_stats_path("/tags/%E7%BA%A6%E5%AE%9A/"), "/tags/%E7%BA%A6%E5%AE%9A/")

    def test_beacon_page_ignores_missing_p(self):
        self.assertIsNone(beacon_page("/api/beacon"))
        self.assertIsNone(beacon_page("/api/beacon?x=1"))

    def test_beacon_rejects_scheme_injection(self):
        self.assertIsNone(beacon_page("/api/beacon?p=javascript:alert(1)"))
        self.assertIsNone(beacon_page("/api/beacon?p=/javascript:alert(1)"))
        self.assertIsNone(beacon_page("/api/beacon?p=data:text/html,<script>1</script>"))
        self.assertIsNone(beacon_page("/api/beacon?p=%2fjavascript%3Aalert(1)"))

    def test_beacon_rejects_control_and_oversize(self):
        self.assertIsNone(beacon_page("/api/beacon?p=/a%0ab"))
        self.assertIsNone(beacon_page("/api/beacon?p=/" + "a" * 600))

    def test_valid_site_path_accepts_normal_paths(self):
        self.assertTrue(valid_site_path("/"))
        self.assertTrue(valid_site_path("/posts/hello/"))
        self.assertTrue(valid_site_path("/tags/%E7%BA%A6%E5%AE%9A/"))


class TestBeaconImport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        settings.db_path = root / "blog.db"
        settings.beacon_log = root / "beacon.log"
        init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def test_import_writes_decoded_paths(self):
        settings.beacon_log.write_text(
            "2026-08-18T10:00:00+08:00|/api/beacon?p=%2fposts%2fmarkdown-guide%2f\n"
            "2026-08-18T10:01:00+08:00|/api/beacon?p=%2f\n",
            encoding="utf-8",
        )
        self.assertEqual(import_beacon_log(), 2)
        conn = connect()
        rows = conn.execute("SELECT path, views FROM stats ORDER BY path").fetchall()
        conn.close()
        self.assertEqual(
            [dict(r) for r in rows],
            [
                {"path": "/", "views": 1},
                {"path": "/posts/markdown-guide/", "views": 1},
            ],
        )
        self.assertEqual(settings.beacon_log.read_text(encoding="utf-8"), "")


class TestStatsNormalization(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings.db_path = Path(self._tmp.name) / "blog.db"
        init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def test_normalize_merges_encoded_paths(self):
        conn = connect()
        conn.executemany(
            "INSERT INTO stats (path, day, views) VALUES (?, ?, ?)",
            [
                ("%2fposts%2fmarkdown-guide%2f", "2026-08-18", 3),
                ("%2fposts%2fmarkdown-guide%2f", "2026-08-17", 1),
                ("/posts/markdown-guide/", "2026-08-17", 2),
                ("%2f", "2026-08-17", 5),
            ],
        )
        conn.commit()
        changed = normalize_stats_paths(conn)
        conn.commit()
        self.assertEqual(changed, 2)
        rows = conn.execute(
            "SELECT path, views FROM stats WHERE day = '2026-08-17' ORDER BY path"
        ).fetchall()
        self.assertEqual(
            [dict(r) for r in rows],
            [
                {"path": "/", "views": 5},
                {"path": "/posts/markdown-guide/", "views": 3},
            ],
        )
        row = conn.execute(
            "SELECT views FROM stats WHERE path = '/posts/markdown-guide/' AND day = '2026-08-18'"
        ).fetchone()
        self.assertEqual(row["views"], 3)
        conn.close()

    def test_normalize_idempotent(self):
        conn = connect()
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES ('/posts/a/', '2026-08-18', 2)"
        )
        conn.commit()
        self.assertEqual(normalize_stats_paths(conn), 0)
        conn.close()

    def test_normalize_cjk_canonical_and_idempotent(self):
        conn = connect()
        conn.execute(
            "INSERT INTO stats (path, day, views) VALUES ('/tags/约定/', '2026-08-18', 1)"
        )
        conn.commit()
        self.assertEqual(normalize_stats_paths(conn), 1)
        row = conn.execute("SELECT path FROM stats").fetchone()
        self.assertEqual(row["path"], "/tags/%E7%BA%A6%E5%AE%9A/")
        self.assertEqual(normalize_stats_paths(conn), 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
