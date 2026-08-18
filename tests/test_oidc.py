import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from admin import oidc
from admin.config import settings
from admin.db import connect, init_db


class _FakeRequest:
    def __init__(self, form=None):
        self._form = form or {}

    async def form(self):
        return self._form


class TestOidc(unittest.TestCase):
    def test_disabled_when_env_missing(self):
        settings.lipass_issuer = ""
        settings.lipass_client_id = ""
        settings.lipass_client_secret = ""
        self.assertFalse(oidc.enabled())

    def test_at_hash_roundtrip(self):
        token = "access-token-123"
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(token.encode("utf-8")).digest()[:16]
        ).rstrip(b"=").decode()
        self.assertTrue(oidc._check_at_hash(token, expected))
        self.assertFalse(oidc._check_at_hash(token, expected[:-1] + ("A" if expected[-1] != "A" else "B")))

    def test_backchannel_empty_form_rejected(self):
        import asyncio

        self.assertFalse(asyncio.run(oidc.backchannel_logout(_FakeRequest())))

    def test_jti_replay_is_rejected(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings.db_path = Path(tmp.name) / "blog.db"
        init_db()
        self.assertFalse(oidc._jti_seen("jti-1", 9999999999))
        self.assertTrue(oidc._jti_seen("jti-1", 9999999999))


if __name__ == "__main__":
    unittest.main()
