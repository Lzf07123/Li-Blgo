import tempfile
import unittest
from pathlib import Path

from admin import security


class TestSecurity(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        stored = security.hash_password("Li&Blog@2026")
        self.assertTrue(security.verify_password("Li&Blog@2026", stored))

    def test_password_rejects_wrong(self):
        stored = security.hash_password("correct")
        self.assertFalse(security.verify_password("wrong", stored))

    def test_rate_limiter_window(self):
        limiter = security.RateLimiter()
        for _ in range(5):
            self.assertTrue(limiter.allow("ip:user", 5, 60))
        self.assertFalse(limiter.allow("ip:user", 5, 60))

    def test_csrf_token_compare(self):
        token = security.new_token()
        self.assertTrue(security.check_token(token, token))
        self.assertFalse(security.check_token(token, token + "x"))


if __name__ == "__main__":
    unittest.main()
