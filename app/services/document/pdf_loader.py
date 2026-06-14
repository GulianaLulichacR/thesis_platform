import io
from pathlib import Path

import aiofiles
import pypdf

from app.core.exceptions import DocumentLoadError
from app.core.logging import get_logger

logger = get_logger(__name__)


class PDFLoader:
    """Extracts text and metadata from PDF files."""

    async def load_from_path(self, path: Path) -> dict:
        """Load and extract a PDF from a filesystem path."""
        try:
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()
            return self._parse(content, filename=path.name)
        except Exception as exc:
            raise DocumentLoadError(f"Failed to load PDF '{path.name}': {exc}") from exc

    async def load_from_bytes(self, data: bytes, filename: str = "document.pdf") -> dict:
        """Load and extract a PDF from raw bytes."""
        try:
            return self._parse(data, filename=filename)
        except Exception as exc:
            raise DocumentLoadError(f"Failed to parse PDF '{filename}': {exc}") from exc

    def _parse(self, data: bytes, filename: str) -> dict:
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages: list[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")

        full_text = "\n\n".join(pages)
        meta = reader.metadata or {}

        return {
            "filename": filename,
            "pages": len(pages),
            "full_text": full_text,
            "pages_text": pages,
            "size_bytes": len(data),
            "title": meta.get("/Title"),
            "author": meta.get("/Author"),
            "word_count": len(full_text.split()),
        }
