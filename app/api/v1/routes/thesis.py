from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from datetime import datetime

from app.core.exceptions import UnsupportedFileTypeError
from app.core.logging import get_logger
from app.schemas.thesis import ProcessingStatus, ThesisMetadata, ThesisUploadResponse, TemplateUploadResponse
from app.services.document.docx_loader import DOCXLoader
from app.services.document.pdf_loader import PDFLoader
from app.services.storage.local_storage import LocalStorageService
from app.services.tasks import FastAPITaskService
from app.services.analysis.background_tasks import run_ai_analysis, run_citation_validation

router = APIRouter(tags=["Thesis"])
logger = get_logger(__name__)

_storage = LocalStorageService()
_pdf_loader = PDFLoader()
_docx_loader = DOCXLoader()


async def _extract_metadata(thesis_id: str, ext: str, filename: str) -> None:
    try:
        path = _storage.get_path(thesis_id, ext)
        import aiofiles
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()

        if ext == "pdf":
            doc = await _pdf_loader.load_from_bytes(data)
        else:
            doc = await _docx_loader.load_from_bytes(data)
            
        updates = {
            "title": doc.get("title"),
            "author": doc.get("author"),
            "pages": doc.get("pages"),
            "word_count": doc.get("word_count"),
            "raw_text_preview": (doc.get("full_text") or "")[:500]
        }
        await _storage.update_metadata(thesis_id, updates)
    except Exception as exc:
        logger.error(f"Error extracting metadata for {thesis_id}: {exc}")


@router.post(
    "/upload",
    response_model=ThesisUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a thesis document (PDF or DOCX)",
)
async def upload_thesis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parent_thesis_id: str | None = Form(None),
) -> ThesisUploadResponse:
    data = await file.read()
    meta = await _storage.save_upload(file.filename or "thesis", data)

    ext = meta["extension"]
    if ext not in ("pdf", "docx"):
        raise UnsupportedFileTypeError(ext)
        
    version = 1
    if parent_thesis_id:
        try:
            parent_meta = await _storage.get_metadata(parent_thesis_id)
            version = parent_meta.get("version", 1) + 1
        except Exception:
            pass # fallback to 1 if parent not found or metadata corrupted

    # Initialize metadata sidecar
    initial_metadata = {
        "id": meta["file_id"],
        "thesis_id": meta["file_id"],
        "parent_thesis_id": parent_thesis_id,
        "version": version,
        "ai_analysis_status": ProcessingStatus.PENDING.value,
        "citation_check_status": ProcessingStatus.PENDING.value,
        "file_name": meta["original_filename"],
        "file_size": meta["size_bytes"],
        "file_type": ext,
        "uploaded_at": datetime.utcnow().isoformat() + "Z"
    }
    await _storage.save_metadata(meta["file_id"], initial_metadata)

    task_service = FastAPITaskService(background_tasks)
    
    # Enqueue metadata extraction
    task_service.enqueue(_extract_metadata, meta["file_id"], ext, meta["original_filename"])
    
    # Enqueue AI analysis
    task_service.enqueue(run_ai_analysis, meta["file_id"], ext)
    
    # Enqueue citation check
    task_service.enqueue(run_citation_validation, meta["file_id"], ext)

    return ThesisUploadResponse(
        thesis_id=meta["file_id"],
        filename=meta["original_filename"],
        size_bytes=meta["size_bytes"],
        pages=None,
    )


@router.get("/", summary="List all uploaded theses")
async def list_thesis():
    """Listar todas las tesis"""
    return await _storage.list_metadata()


@router.delete("/{thesis_id}", summary="Delete a thesis")
async def delete_thesis(thesis_id: str):
    """Eliminar tesis"""
    try:
        # Get metadata to find extension
        meta = await _storage.get_metadata(thesis_id)
        ext = meta.get("file_type", "pdf")
        
        # Delete file
        _storage.delete(thesis_id, ext)
        
        # Delete metadata
        meta_path = _storage.get_metadata_path(thesis_id)
        if meta_path.exists():
            meta_path.unlink()
            
        return {"message": "Tesis eliminada", "id": thesis_id}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))

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
    try:
        data = await _storage.get_metadata(thesis_id)
        return ThesisMetadata(**data)
    except Exception as exc:
        from app.core.exceptions import StorageError
        raise StorageError(f"Thesis '{thesis_id}' metadata not found.") from exc


@router.get(
    "/{thesis_id}/preview",
    summary="Get preview information for a thesis",
)
async def get_thesis_preview(thesis_id: str):
    """Returns preview URL and file type"""
    for ext in ("pdf", "docx"):
        try:
            path = _storage.get_path(thesis_id, ext)
            return {
                "thesis_id": thesis_id,
                "file_type": ext,
                "download_url": f"/api/v1/thesis/{thesis_id}/download",
            }
        except Exception:
            continue
    from app.core.exceptions import StorageError
    raise StorageError(f"Thesis '{thesis_id}' not found.")


@router.get(
    "/{thesis_id}/download",
    summary="Download the raw thesis file",
)
async def download_thesis(thesis_id: str):
    """Returns the actual file"""
    for ext in ("pdf", "docx"):
        try:
            path = _storage.get_path(thesis_id, ext)
            meta = await _storage.get_metadata(thesis_id)
            original_filename = meta.get("filename", f"thesis_{thesis_id}.{ext}")
            return FileResponse(
                path=path,
                filename=original_filename,
                media_type="application/pdf" if ext == "pdf" else "application/octet-stream",
                content_disposition_type="inline" if ext == "pdf" else "attachment",
            )
        except Exception:
            continue
            
    from app.core.exceptions import StorageError
    raise StorageError(f"Thesis '{thesis_id}' not found.")
