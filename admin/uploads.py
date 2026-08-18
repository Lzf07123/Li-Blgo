"""上传读取限制：流式读取，超过上限立即中止，避免整文件先载入内存。"""

from fastapi import UploadFile

CHUNK_SIZE = 64 * 1024


async def read_limited(file: UploadFile, limit: int) -> bytes:
    """最多读取 limit 字节，超出即抛 ValueError。"""
    if limit <= 0:
        raise ValueError("大小限制必须大于 0")
    chunks = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError("文件超过大小限制")
        chunks.append(chunk)
    return b"".join(chunks)
