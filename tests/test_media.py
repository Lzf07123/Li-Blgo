import tempfile
import unittest
from pathlib import Path

from admin import media


class TestMedia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        media.MEDIA_ROOT = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_upload_allowed_and_listed(self):
        p = media.save_upload("截图.png", b"\x89PNG\r\n\x1a\n")
        self.assertTrue(p.is_file())
        self.assertEqual(len(media.list_media()), 1)
        self.assertEqual(media.list_media()[0]["rel"].split("/")[-1], p.name)

    def test_upload_rejects_bad_extension(self):
        with self.assertRaises(ValueError):
            media.save_upload("evil.php", b"<?php")

    def test_upload_rejects_too_large(self):
        with self.assertRaises(ValueError):
            media.save_upload("big.png", b"x" * (media.MAX_SIZE + 1))

    def test_delete_media(self):
        p = media.save_upload("a.png", b"data")
        media.delete_media(p.relative_to(media.MEDIA_ROOT).as_posix())
        self.assertFalse(p.exists())
        self.assertEqual(media.list_media(), [])

    def test_safe_path_rejects_escape(self):
        with self.assertRaises(ValueError):
            media.safe_media_path("../secret.png")


if __name__ == "__main__":
    unittest.main()
