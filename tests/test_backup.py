import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from admin import backup, media
from admin.config import settings


class TestBackup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        settings.content_root = root / "content"
        settings.config_root = root / "config"
        settings.db_path = root / "blog.db"
        media.MEDIA_ROOT = root / "img"
        (settings.content_root / "posts").mkdir(parents=True)
        settings.config_root.mkdir()
        media.MEDIA_ROOT.mkdir()
        (settings.content_root / "posts" / "a.md").write_text(
            "---\ntitle: A\n---\n", encoding="utf-8"
        )
        (settings.config_root / "brand.yaml").write_text(
            "name: Li&Blog\n", encoding="utf-8"
        )
        (media.MEDIA_ROOT / "x.png").write_bytes(b"png")
        conn = sqlite3.connect(settings.db_path)
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
        conn.close()

    def tearDown(self):
        self._tmp.cleanup()

    def test_backup_zip_contains_sources(self):
        data = backup.build_backup_zip()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
            self.assertIn("backup-manifest.json", names)
            self.assertIn("content/posts/a.md", names)
            self.assertIn("config/brand.yaml", names)
            self.assertIn("themes/blog-theme/static/img/x.png", names)
            self.assertIn("data/blog.db", names)
            manifest = json.loads(zf.read("backup-manifest.json"))
            self.assertEqual(manifest["sections"]["content"], 1)
            self.assertEqual(manifest["sections"]["config"], 1)
            self.assertEqual(manifest["sections"]["media"], 1)
            self.assertEqual(manifest["sections"]["database"], 1)


if __name__ == "__main__":
    unittest.main()
