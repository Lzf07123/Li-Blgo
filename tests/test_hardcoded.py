import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from scripts.check_hardcoded import check


class TestNoHardcodedColors(unittest.TestCase):
    def test_public_templates_have_no_hardcoded_colors(self):
        self.assertEqual(check(), [])


if __name__ == "__main__":
    unittest.main()
