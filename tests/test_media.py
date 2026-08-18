import tempfile
import unittest
import io
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from admin import media


def make_image(size, fmt="PNG", color=(0, 120, 109)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


class TestMedia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        media.MEDIA_ROOT = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_upload_allowed_and_listed(self):
        p = media.save_upload("截图.png", make_image((16, 16)))
        self.assertTrue(p.is_file())
        self.assertEqual(len(media.list_media()), 1)
        self.assertEqual(media.list_media()[0]["rel"].split("/")[-1], p.name)

    def test_upload_rejects_invalid_image(self):
        with self.assertRaises(ValueError):
            media.save_upload("bad.png", b"not an image")

    def test_upload_rejects_bad_extension(self):
        with self.assertRaises(ValueError):
            media.save_upload("evil.php", b"<?php")

    def test_upload_rejects_too_large(self):
        with self.assertRaises(ValueError):
            media.save_upload("big.png", b"x" * (media.MAX_SIZE + 1))

    def test_delete_media(self):
        p = media.save_upload("a.png", make_image((8, 8)))
        media.delete_media(p.relative_to(media.MEDIA_ROOT).as_posix())
        self.assertFalse(p.exists())
        self.assertEqual(media.list_media(), [])

    def test_delete_media_rejects_non_image(self):
        p = Path(media.MEDIA_ROOT) / "badge.svg"
        p.write_text("<svg/>", encoding="utf-8")
        with self.assertRaises(ValueError):
            media.delete_media("badge.svg")

    def test_large_image_downscaled(self):
        p = media.save_upload("huge.jpg", make_image((3200, 2400), fmt="JPEG"))
        with Image.open(p) as img:
            self.assertLessEqual(max(img.size), media.MAX_DIMENSION)

    def test_small_image_kept(self):
        p = media.save_upload("small.png", make_image((120, 80)))
        with Image.open(p) as img:
            self.assertEqual(img.size, (120, 80))

    def test_safe_path_rejects_escape(self):
        with self.assertRaises(ValueError):
            media.safe_media_path("../secret.png")

    def test_huge_dimensions_rejected_before_decode(self):
        class FakeImage:
            format = "PNG"
            is_animated = False
            size = (30000, 30000)

            def load(self):
                raise AssertionError("不应在尺寸校验前解码")

        with patch("admin.media.Image.open", return_value=FakeImage()):
            with self.assertRaises(ValueError):
                media._optimize_image(b"fake")


if __name__ == "__main__":
    unittest.main()
