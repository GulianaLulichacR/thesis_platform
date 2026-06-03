import uuid
from pathlib import Path

import aiofiles

from app.core.config import get_settings
from app.core.exceptions import StorageError, UnsupportedFileTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LocalStorageService:
    """Handles secure saving and retrieval of uploaded files."""

    def __init__(self) -> None:
        self._base_dir = settings.UPLOAD_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_extension(self, filename: str) -> str:
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(ext)
        return ext

    def _generate_id(self) -> str:
        return uuid.uuid4().hex

    def _safe_filename(self, file_id: str, ext: str) -> str:
        return f"{file_id}.{ext}"

    async def save_upload(self, filename: str, data: bytes) -> dict:
        """Save uploaded bytes to disk and return storage metadata."""
        size = len(data)
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size > max_bytes:
            raise StorageError(
                f"File exceeds max size of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        ext = self._validate_extension(filename)
        file_id = self._generate_id()
        safe_name = self._safe_filename(file_id, ext)
        dest = self._base_dir / safe_name

        try:
            async with aiofiles.open(dest, "wb") as f:
                await f.write(data)
            logger.info(
                f"File saved: {filename}",
                extra={"file_id": file_id}
            )
        except OSError as exc:
            raise StorageError(f"Could not write file: {exc}") from exc

        return {
            "file_id": file_id,
            "original_filename": filename,
            "stored_path": dest,
            "extension": ext,
            "size_bytes": size,
        }

    def get_path(self, file_id: str, ext: str) -> Path:
        path = self._base_dir / self._safe_filename(file_id, ext)
        if not path.exists():
            raise StorageError(f"File '{file_id}' not found in storage.")
        return path

    def delete(self, file_id: str, ext: str) -> None:
        path = self._base_dir / self._safe_filename(file_id, ext)
        if path.exists():
            path.unlink()
