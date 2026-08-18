import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from admin import importer
from admin.config import settings


class TestImporter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        settings.content_root = root / "content"
        (settings.content_root / "posts").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_parse_document_defaults(self):
        slug, fm, body = importer.parse_document(
            "hello.md", "---\ntitle: Hello\ntags: a, b\n---\n正文"
        )
        self.assertEqual(slug, "hello")
        self.assertEqual(fm["tags"], ["a", "b"])
        self.assertEqual(fm["status"], "published")
        self.assertEqual(body, "正文")

    def test_parse_document_normalizes_slug(self):
        slug, fm, body = importer.parse_document(
            "Bad Name.md", "---\ntitle: x\n---\n"
        )
        self.assertEqual(slug, "bad-name")
        self.assertEqual(fm["title"], "x")

    def test_parse_document_chinese_filename_falls_back_to_hash(self):
        slug, fm, _ = importer.parse_document("我的第一篇博客.md", "---\ntitle: 我的博客\n---\n")
        self.assertRegex(slug, r"^post-[a-f0-9]{10}$")
        self.assertEqual(fm["title"], "我的博客")

    def test_parse_document_explicit_slug_normalized(self):
        slug, _, _ = importer.parse_document(
            "a.md", "---\ntitle: A\nslug: My Post\n---\n"
        )
        self.assertEqual(slug, "my-post")

    def test_import_skips_index_files(self):
        result = importer.import_posts(
            [
                ("_index.md", "---\ntitle: 文章\n---\n".encode("utf-8")),
                ("index.md", "---\ntitle: 索引\n---\n".encode("utf-8")),
            ]
        )
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 2)

    def test_import_rejects_non_markdown(self):
        result = importer.import_posts([("a.txt", b"hello")])
        self.assertEqual(result["imported"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("不支持的文件类型", result["errors"][0])

    def test_limits_read_from_settings(self):
        original_files = settings.import_max_files
        original_bytes = settings.import_max_file_bytes
        try:
            settings.import_max_files = 1
            with self.assertRaises(ValueError):
                importer.import_posts([("a.md", b"x"), ("b.md", b"y")])
            settings.import_max_files = original_files
            settings.import_max_file_bytes = 3
            result = importer.import_posts([("a.md", b"1234")])
            self.assertEqual(result["imported"], 0)
            self.assertIn("超过单文件大小限制", result["errors"][0])
        finally:
            settings.import_max_files = original_files
            settings.import_max_file_bytes = original_bytes

    def test_import_posts_counts(self):
        entries = [
            ("a.md", b"---\ntitle: A\n---\nAAA"),
            ("b.md", b"---\ntitle: B\n---\nBBB"),
        ]
        result = importer.import_posts(entries)
        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["files"]), 2)
        self.assertTrue((settings.content_root / "posts" / "a.md").exists())

    def test_import_nested_folder_paths(self):
        entries = [
            ("docs/2026/a.md", b"---\ntitle: A\n---\n"),
            ("notes/sub/b.md", b"---\ntitle: B\n---\n"),
        ]
        result = importer.import_posts(entries)
        self.assertEqual(result["imported"], 2)
        self.assertTrue((settings.content_root / "posts" / "a.md").exists())
        self.assertTrue((settings.content_root / "posts" / "b.md").exists())

    def test_import_infers_metadata_without_frontmatter(self):
        result = importer.import_posts(
            [("2026-08-18-my-post.md", "# 自动标题\n\n正文".encode("utf-8"))]
        )
        self.assertEqual(result["imported"], 1)
        meta = result["files"][0]
        self.assertEqual(meta["slug"], "2026-08-18-my-post")
        self.assertEqual(meta["title"], "自动标题")
        self.assertEqual(meta["date"], "2026-08-18")
        self.assertEqual(meta["tags"], [])

    def test_infer_date_falls_back_on_invalid_date(self):
        slug, fm, _ = importer.parse_document("2026-99-99-bad.md", "正文")
        self.assertEqual(slug, "2026-99-99-bad")
        self.assertRegex(fm["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_import_posts_skips_existing(self):
        (settings.content_root / "posts" / "a.md").write_text(
            "---\ntitle: Old\n---\nold", encoding="utf-8"
        )
        result = importer.import_posts([("a.md", b"---\ntitle: New\n---\nnew")])
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertIn(
            "Old", (settings.content_root / "posts" / "a.md").read_text(encoding="utf-8")
        )

    def test_import_posts_overwrite(self):
        (settings.content_root / "posts" / "a.md").write_text(
            "---\ntitle: Old\n---\nold", encoding="utf-8"
        )
        result = importer.import_posts(
            [("a.md", b"---\ntitle: New\n---\nnew")], overwrite=True
        )
        self.assertEqual(result["imported"], 1)
        self.assertIn(
            "New", (settings.content_root / "posts" / "a.md").read_text(encoding="utf-8")
        )

    def test_import_posts_collects_errors(self):
        result = importer.import_posts(
            [("a.md", "---\ntitle: x\nslug: !!!\n---\n".encode("utf-8"))]
        )
        self.assertEqual(result["imported"], 0)
        self.assertEqual(len(result["errors"]), 1)

    def test_extract_zip_rejects_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.md", "---\ntitle: x\n---\n")
        with self.assertRaises(ValueError):
            importer.extract_zip(buf.getvalue())

    def test_extract_zip_returns_markdown_only(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("posts/a.md", "---\ntitle: A\n---\n")
            zf.writestr("ignore.txt", "x")
        entries = importer.extract_zip(buf.getvalue())
        self.assertEqual([n for n, _ in entries], ["a.md"])


if __name__ == "__main__":
    unittest.main()
