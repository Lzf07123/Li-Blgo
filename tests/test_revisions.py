import tempfile
import unittest
from pathlib import Path

from admin.config import settings
from admin.revisions import list_revisions, read_revision, save_revision


class TestRevisions(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        settings.db_path = self.root / "data" / "blog.db"
        settings.db_path.parent.mkdir(parents=True)
        settings.revision_max = 5

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_list_read_roundtrip_and_prune(self):
        for i in range(8):
            save_revision(
                "posts",
                "hello",
                {"title": f"T{i}", "date": "2026-08-18"},
                f"正文 {i}",
            )
        revisions = list_revisions("posts", "hello")
        self.assertEqual(len(revisions), 5)
        fm, body = read_revision("posts", "hello", revisions[0])
        self.assertIn("正文", body)
        self.assertIn("title", fm)

    def test_non_posts_section_ignored(self):
        save_revision("projects", "proj", {"title": "P"}, "正文")
        self.assertEqual(list_revisions("projects", "proj"), [])


if __name__ == "__main__":
    unittest.main()
