"""SHA-256 checksums for ingested files — read in fixed-size chunks so
even large datasets never have to be loaded fully into memory just to be
hashed.
"""
import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_of_file(path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_size_bytes(path) -> int:
    return Path(path).stat().st_size
