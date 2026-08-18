import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from scripts.check_contrast import verify


class TestContrast(unittest.TestCase):
    def test_key_text_pairs_meet_wcag_aa(self):
        css = (ROOT / "themes" / "blog-theme" / "static" / "css" / "tokens.css").read_text(
            encoding="utf-8"
        )
        failures = verify(css)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
