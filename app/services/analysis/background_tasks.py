import asyncio
from pathlib import Path

from google.genai import types

from app.core.logging import get_logger
from app.schemas.thesis import ProcessingStatus
from app.services.llm.gemini_service import GeminiService
from app.services.storage.local_storage import LocalStorageService

logger = get_logger(__name__)

_storage = LocalStorageService()
_gemini = GeminiService()


async def _update_status(thesis_id: str, field: str, status: ProcessingStatus) -> None:
    try:
        await _storage.update_metadata(thesis_id, {field: status.value})
    except Exception as exc:
        logger.error(f"Failed to update {field} to {status} for {thesis_id}: {exc}")


async def run_ai_analysis(thesis_id: str, ext: str, pattern_path: str | None = None) -> None:
    """
    Compares the uploaded thesis with a pattern template using Gemini.
    """
    await _update_status(thesis_id, "ai_analysis_status", ProcessingStatus.RUNNING)
    
    try:
        thesis_path = _storage.get_path(thesis_id, ext)
        
        # In a real scenario, you might upload both the thesis and the pattern to Gemini.
        # Here we do the thesis and ask it to evaluate structure.
        
        uploaded_thesis = _gemini.client.files.upload(
            file=Path(thesis_path),
            config=types.UploadFileConfig(mime_type="application/pdf" if ext == "pdf" else "text/plain") # Simplified mime
        )
        
        prompt = (
            "Analiza el documento proporcionado. "
            "Indica: estructura faltante, capítulos incompletos, formato incorrecto, recomendaciones. "
            "Evalúa si cumple con el estándar de tesis."
        )
        
        contents = [uploaded_thesis, prompt]
        
        # If pattern exists, we could upload it and add to contents
        if pattern_path and Path(pattern_path).exists():
            uploaded_pattern = _gemini.client.files.upload(
                file=Path(pattern_path),
                config=types.UploadFileConfig(mime_type="application/pdf")
            )
            contents.insert(0, uploaded_pattern)
            contents[-1] = "Analiza el documento de tesis proporcionado y compáralo con la plantilla. Indica: estructura faltante, capítulos incompletos, formato incorrecto, recomendaciones."
            
        # Call Gemini
        response = _gemini.client.models.generate_content(
            model=_gemini.default_model,
            contents=contents,
        )
        
        logger.info(f"AI Analysis completed for {thesis_id}")
        
        # Save results (you might want to save to a separate DB table/file later)
        await _storage.update_metadata(thesis_id, {
            "ai_analysis_result": response.text,
            "ai_analysis_status": ProcessingStatus.COMPLETED.value
        })
        
    except Exception as exc:
        logger.exception(f"AI Analysis failed for {thesis_id}")
        await _update_status(thesis_id, "ai_analysis_status", ProcessingStatus.FAILED)


async def run_citation_validation(thesis_id: str, ext: str) -> None:
    """
    Uses Gemini to validate citations and academic integrity.
    """
    await _update_status(thesis_id, "citation_check_status", ProcessingStatus.RUNNING)
    
    try:
        thesis_path = _storage.get_path(thesis_id, ext)
        
        uploaded_thesis = _gemini.client.files.upload(
            file=Path(thesis_path),
            config=types.UploadFileConfig(mime_type="application/pdf" if ext == "pdf" else "text/plain")
        )
        
        prompt = (
            "Revisa las citas y la bibliografía de este documento. "
            "Valida si el formato (APA, IEEE, etc.) es correcto y detecta posibles inconsistencias o problemas de integridad académica."
        )
        
        response = _gemini.client.models.generate_content(
            model=_gemini.default_model,
            contents=[uploaded_thesis, prompt],
        )
        
        logger.info(f"Citation validation completed for {thesis_id}")
        
        await _storage.update_metadata(thesis_id, {
            "citation_check_result": response.text,
            "citation_check_status": ProcessingStatus.COMPLETED.value
        })
        
    except Exception as exc:
        logger.exception(f"Citation validation failed for {thesis_id}")
        await _update_status(thesis_id, "citation_check_status", ProcessingStatus.FAILED)
