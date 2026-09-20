from __future__ import annotations

import mimetypes
from pathlib import Path


class LocalStorage:
    """Filesystem storage that only persists normalized relative keys."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents:
            raise ValueError("storage key escapes the configured storage root")
        return candidate

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    @staticmethod
    def key_for(content_hash: str, filename: str | None, mime_type: str) -> str:
        suffix = Path(filename or "").suffix.lower()
        if not suffix:
            suffix = mimetypes.guess_extension(mime_type) or ".bin"
        suffix = suffix if suffix.startswith(".") else f".{suffix}"
        return f"{content_hash[:2]}/{content_hash}{suffix}"
