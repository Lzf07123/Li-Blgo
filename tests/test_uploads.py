import asyncio
import io
import unittest

from fastapi import UploadFile

from admin.uploads import read_limited


def _upload(data: bytes) -> UploadFile:
    return UploadFile(filename="x.bin", file=io.BytesIO(data))


class TestReadLimited(unittest.TestCase):
    def test_reads_within_limit(self):
        data = b"a" * 100
        self.assertEqual(asyncio.run(read_limited(_upload(data), 200)), data)

    def test_rejects_over_limit(self):
        with self.assertRaises(ValueError):
            asyncio.run(read_limited(_upload(b"a" * 200), 100))

    def test_exact_limit_ok(self):
        data = b"b" * 64
        self.assertEqual(asyncio.run(read_limited(_upload(data), 64)), data)


if __name__ == "__main__":
    unittest.main()
