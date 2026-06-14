from fastapi import APIRouter

from app.core.exceptions import ThesisPlatformError
from app.core.logging import get_logger
from app.schemas.review import FullReviewRequest, FullReviewResponse
from app.services.review.review_orchestrator import ReviewOrchestrator

router = APIRouter()
logger = get_logger(__name__)

@router.post("/full", response_model=FullReviewResponse)
async def full_review(review_request: FullReviewRequest):
    orchestrator = ReviewOrchestrator()
    try:
        result = await orchestrator.perform_review(review_request)
        return result
    except ThesisPlatformError:
        raise
    except Exception as exc:
        logger.exception("Unexpected full review error")
        raise ThesisPlatformError(f"Could not complete review: {exc}")

from fastapi import UploadFile, File, Form, Depends, HTTPException, status
from typing import Optional

@router.post("/review/full", status_code=status.HTTP_200_OK)
async def post_full_review(
    file: UploadFile = File(...),
    include_ai_detection: bool = Form(default=False),
    ai_detection_provider: Optional[str] = Form(default="mock")
):
    """
    Endpoint principal unificado para análisis global de avances de tesis universitarias.
    Incluye análisis de autoría por IA.
    """
    if not file.filename.endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Solo se admite .docx y .pdf")
    
    file_bytes = await file.read()
    orchestrator = ReviewOrchestrator() 
    
    analysis_report = await orchestrator.run_full_review(
        file_bytes=file_bytes,
        filename=file.filename,
        include_ai_detection=include_ai_detection,
        ai_detection_provider=ai_detection_provider
    )
    
    return analysis_report
