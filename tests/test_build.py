import pathlib
import tempfile
import unittest

from scripts.build import publish, validate_content


class TestBuild(unittest.TestCase):
    def test_validate_rejects_bad_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "content").mkdir()
            bad = root / "content" / "bad.md"
            bad.write_text("---\ntitle: [broken\n---\n", encoding="utf-8")
            errors = validate_content(root)
            self.assertTrue(any("frontmatter" in e for e in errors))

    def test_validate_accepts_good_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "content").mkdir()
            good = root / "content" / "good.md"
            good.write_text("---\ntitle: 正常\n---\n正文\n", encoding="utf-8")
            self.assertEqual(validate_content(root), [])

    def test_publish_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            src = base / "src"
            src.mkdir()
            (src / "a.html").write_text("x", encoding="utf-8")
            dst = base / "dst"
            dst.mkdir()
            (dst / "old.html").write_text("y", encoding="utf-8")
            publish(src, dst)
            self.assertTrue((dst / "a.html").exists())
            self.assertFalse((dst / "old.html").exists())


if __name__ == "__main__":
    unittest.main()
