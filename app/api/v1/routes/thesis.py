from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status

from app.core.exceptions import UnsupportedFileTypeError
from app.core.logging import get_logger
from app.schemas.thesis import ThesisMetadata, ThesisUploadResponse, TemplateUploadResponse
from app.services.document.docx_loader import DOCXLoader
from app.services.document.pdf_loader import PDFLoader
from app.services.storage.local_storage import LocalStorageService

router = APIRouter(prefix="/thesis", tags=["Thesis"])
logger = get_logger(__name__)

_storage = LocalStorageService()
_pdf_loader = PDFLoader()
_docx_loader = DOCXLoader()


@router.post(
    "/upload",
    response_model=ThesisUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a thesis document (PDF or DOCX)",
)
async def upload_thesis(file: UploadFile = File(...)) -> ThesisUploadResponse:
    data = await file.read()
    meta = await _storage.save_upload(file.filename or "thesis", data)

    ext = meta["extension"]
    if ext == "pdf":
        doc = await _pdf_loader.load_from_bytes(data, meta["original_filename"])
    elif ext == "docx":
        doc = await _docx_loader.load_from_bytes(data, meta["original_filename"])
    else:
        raise UnsupportedFileTypeError(ext)

    return ThesisUploadResponse(
        thesis_id=meta["file_id"],
        filename=meta["original_filename"],
        size_bytes=meta["size_bytes"],
        pages=doc.get("pages"),
    )


@router.post(
    "/template/upload",
    response_model=TemplateUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a formatting template (PDF or DOCX)",
)
async def upload_template(file: UploadFile = File(...)) -> TemplateUploadResponse:
    data = await file.read()
    meta = await _storage.save_upload(file.filename or "template", data)
    return TemplateUploadResponse(
        template_id=meta["file_id"],
        filename=meta["original_filename"],
        size_bytes=meta["size_bytes"],
    )


@router.get(
    "/{thesis_id}/metadata",
    response_model=ThesisMetadata,
    summary="Get extracted metadata for an uploaded thesis",
)
async def get_thesis_metadata(thesis_id: str) -> ThesisMetadata:
    """
    Returns metadata extracted at upload time.
    Phase 2: persist metadata in DB and retrieve from there.
    """
    # Phase 1: re-read from disk to demonstrate the flow
    import os
    for ext in ("pdf", "docx"):
        try:
            path = _storage.get_path(thesis_id, ext)
            import aiofiles
            async with aiofiles.open(path, "rb") as f:
                data = await f.read()

            if ext == "pdf":
                doc = await _pdf_loader.load_from_bytes(data)
            else:
                doc = await _docx_loader.load_from_bytes(data)

            return ThesisMetadata(
                thesis_id=thesis_id,
                title=doc.get("title"),
                author=doc.get("author"),
                pages=doc.get("pages"),
                word_count=doc.get("word_count"),
                raw_text_preview=(doc.get("full_text") or "")[:500],
            )
        except Exception:
            continue

    from app.core.exceptions import StorageError
    raise StorageError(f"Thesis '{thesis_id}' not found.")
