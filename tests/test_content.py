import tempfile
import unittest
from pathlib import Path

from admin import content
from admin.config import settings


class TestContent(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        settings.content_root = self.root / "content"
        settings.config_root = self.root / "config"
        (settings.content_root / "posts").mkdir(parents=True)
        settings.config_root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            content.safe_resolve(self.root, "../secret")

    def test_write_read_roundtrip(self):
        content.write_markdown(
            "posts",
            "hello-world",
            {"title": "你好", "date": "2026-08-18", "tags": ["Hugo"]},
            "正文内容",
        )
        fm, body = content.read_markdown("posts", "hello-world")
        self.assertEqual(fm["title"], "你好")
        self.assertIn("正文内容", body)

    def test_bad_slug_rejected(self):
        with self.assertRaises(ValueError):
            content.write_markdown("posts", "../evil", {"title": "x"}, "y")

    def test_yaml_save_load(self):
        content.save_yaml("brand", {"name": "Li&Blog", "icp": ""})
        self.assertEqual(content.load_yaml("brand")["name"], "Li&Blog")

    def test_list_markdown_filter(self):
        content.write_markdown(
            "posts",
            "hello",
            {"title": "Hello Hugo", "date": "2026-08-18", "status": "published", "tags": ["hugo"]},
            "正文",
        )
        content.write_markdown(
            "posts",
            "draft-note",
            {"title": "未完成草稿", "date": "2026-08-18", "status": "draft", "tags": []},
            "正文",
        )
        self.assertEqual(len(content.list_markdown("posts", q="hugo")), 1)
        self.assertEqual(len(content.list_markdown("posts", status="draft")), 1)
        self.assertEqual(len(content.list_markdown("posts", q="不存在")), 0)


if __name__ == "__main__":
    unittest.main()
