import os
import pathlib
import tempfile
import types
import unittest
from unittest import mock

from scripts.build import (
    build,
    build_tmp_root,
    clear_tree,
    preview_output_root,
    publish,
    validate_content,
    validate_content_links,
    verify_output,
    write_fingerprint,
)


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

    def test_content_links_validate(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "content" / "posts").mkdir(parents=True)
            (root / "themes" / "blog-theme" / "static" / "img").mkdir(parents=True)
            (root / "content" / "posts" / "hello.md").write_text(
                "---\ntitle: H\n---\n"
                "![图](/img/ok.png)\n"
                "[坏链](/posts/nope/)\n"
                "[好链](/posts/hello/)\n"
                "[外链](https://example.com)\n",
                encoding="utf-8",
            )
            (root / "themes" / "blog-theme" / "static" / "img" / "ok.png").write_bytes(
                b"png"
            )
            errors = validate_content_links(root)
            self.assertTrue(any("/posts/nope/" in e for e in errors))
            self.assertFalse(any("ok.png" in e for e in errors))
            self.assertFalse(any("https://example.com" in e for e in errors))
            self.assertFalse(any("/posts/hello/" in e for e in errors))

    def test_verify_output_detects_missing_and_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            errors = verify_output(out, expect_absolute_urls=True)
            self.assertTrue(any("index.html" in e for e in errors))
            (out / "index.html").write_text(
                '<a href="https://example.com/">x</a>', encoding="utf-8"
            )
            (out / "robots.txt").write_text("User-agent: *", encoding="utf-8")
            errors = verify_output(out, expect_absolute_urls=True)
            self.assertTrue(any("example.com" in e for e in errors))
            (out / "index.html").write_text("<html></html>", encoding="utf-8")
            errors = verify_output(out, expect_absolute_urls=True)
            self.assertFalse(any("example.com" in e for e in errors))

    def test_verify_output_checks_json_and_sitemap(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            (out / "index.html").write_text("<html></html>", encoding="utf-8")
            (out / "index.xml").write_text("<rss></rss>", encoding="utf-8")
            (out / "robots.txt").write_text("User-agent: *", encoding="utf-8")
            (out / "llms.txt").write_text("# site", encoding="utf-8")
            (out / "404.html").write_text("404", encoding="utf-8")
            (out / "search").mkdir()
            (out / "search" / "index.json").write_text("[broken", encoding="utf-8")
            (out / "sitemap.xml").write_text("<xml/>", encoding="utf-8")
            errors = verify_output(out)
            self.assertTrue(any("合法 JSON" in e for e in errors))
            self.assertTrue(any("urlset" in e for e in errors))

    def test_verify_output_rejects_draft_and_future_leak(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            content = root / "content" / "posts"
            content.mkdir(parents=True)
            (content / "draft-post.md").write_text(
                "---\ntitle: D\nstatus: draft\n---\n正文\n", encoding="utf-8"
            )
            (content / "future-post.md").write_text(
                "---\ntitle: F\ndate: 2099-01-01\n---\n正文\n", encoding="utf-8"
            )
            out = root / "out"
            for rel in ("posts/draft-post/index.html", "posts/future-post/index.html"):
                target = out / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("<html>leak</html>", encoding="utf-8")
            errors = verify_output(out, content_root=root / "content")
            self.assertTrue(any("草稿泄漏" in e for e in errors))
            self.assertTrue(any("未来日期" in e for e in errors))

    def test_verify_output_rejects_draft_in_sitemap(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            content = root / "content" / "posts"
            content.mkdir(parents=True)
            (content / "hidden.md").write_text(
                "---\ntitle: H\nstatus: draft\n---\n正文\n", encoding="utf-8"
            )
            out = root / "out"
            out.mkdir()
            (out / "sitemap.xml").write_text(
                "<urlset><loc>https://x/posts/hidden/</loc></urlset>", encoding="utf-8"
            )
            errors = verify_output(out, content_root=root / "content")
            self.assertTrue(any("sitemap 包含草稿" in e for e in errors))

    def test_write_fingerprint_creates_build_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            css = root / "themes" / "blog-theme" / "static" / "css"
            css.mkdir(parents=True)
            (css / "tokens.css").write_text(":root{}", encoding="utf-8")
            (css / "style.css").write_text("body{}", encoding="utf-8")
            target = write_fingerprint(root)
            self.assertTrue(target.exists())
            text = target.read_text(encoding="utf-8")
            self.assertIn("tokens:", text)
            self.assertIn("built_at:", text)

    def test_clear_tree_tolerates_mountpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            mount = root / "mnt"
            mount.mkdir()
            (mount / "x.html").write_text("x", encoding="utf-8")
            with mock.patch(
                "shutil.rmtree",
                side_effect=OSError(16, "Device or resource busy"),
            ):
                clear_tree(mount)
            self.assertTrue(mount.exists())
            self.assertFalse((mount / "x.html").exists())

    def test_build_tmp_and_preview_env_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self.assertEqual(build_tmp_root(root), root / ".build-tmp")
            self.assertEqual(preview_output_root(root), root / ".preview-out")
            with mock.patch.dict(
                os.environ,
                {"BUILD_TMP_ROOT": "/x/tmp", "PREVIEW_ROOT": "/x/preview"},
            ):
                self.assertEqual(build_tmp_root(root), pathlib.Path("/x/tmp"))
                self.assertEqual(preview_output_root(root), pathlib.Path("/x/preview"))

    def test_build_failure_cleans_tmp_and_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            with mock.patch("scripts.build.ROOT", root), mock.patch(
                "scripts.build.run_build", side_effect=RuntimeError("boom")
            ):
                args = types.SimpleNamespace(
                    preview=False, full=False, keep_tmp=False, metrics=False, report=None
                )
                with self.assertRaises(SystemExit) as cm:
                    build(args)
            self.assertEqual(cm.exception.code, 2)
            self.assertFalse((root / ".build-tmp").exists())


class TestBootstrapBuild(unittest.TestCase):
    def test_bootstrap_always_runs_full_build_even_if_index_exists(self):
        from admin import main as main_mod

        with tempfile.TemporaryDirectory() as d:
            output = pathlib.Path(d)
            (output / "index.html").write_text("x", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LIBLOG_BOOTSTRAP_BUILD": "1"}):
                with mock.patch.object(main_mod.settings, "output_root", output):
                    with mock.patch.object(
                        main_mod.build,
                        "run_full",
                        return_value=(types.SimpleNamespace(returncode=0), 0.1),
                    ) as run:
                        main_mod._bootstrap_build()
            run.assert_called_once_with()

    def test_bootstrap_can_be_disabled(self):
        from admin import main as main_mod

        with mock.patch.dict(os.environ, {"LIBLOG_BOOTSTRAP_BUILD": "0"}):
            with mock.patch.object(main_mod.build, "run_full") as run:
                main_mod._bootstrap_build()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
