from fastapi import APIRouter, status

from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.schemas.analysis import (
    FormatAnalysisRequest,
    FormatAnalysisResponse,
    FullReportRequest,
    FullReportResponse,
    IssueItem,
    ReferencesAnalysisRequest,
    ReferencesAnalysisResponse,
    Severity,
    StructureAnalysisRequest,
    StructureAnalysisResponse,
)
from app.services.analysis.references_checker import ReferencesChecker
from app.services.analysis.report_generator import ReportGenerator
from app.services.analysis.structure_checker import StructureChecker
from app.services.document.docx_loader import DOCXLoader
from app.services.document.pdf_loader import PDFLoader
from app.services.storage.local_storage import LocalStorageService

router = APIRouter(tags=["Analysis"])
logger = get_logger(__name__)

_storage = LocalStorageService()
_pdf_loader = PDFLoader()
_docx_loader = DOCXLoader()
_report_gen = ReportGenerator()


async def _load_thesis_text(thesis_id: str) -> str:
    """Helper: loads full text from storage regardless of file type."""
    import aiofiles
    for ext in ("pdf", "docx"):
        try:
            path = _storage.get_path(thesis_id, ext)
            async with aiofiles.open(path, "rb") as f:
                data = await f.read()
            if ext == "pdf":
                doc = await _pdf_loader.load_from_bytes(data)
            else:
                doc = await _docx_loader.load_from_bytes(data)
            return doc["full_text"]
        except StorageError:
            continue
    raise StorageError(f"Thesis '{thesis_id}' not found.")


@router.post(
    "/structure",
    response_model=StructureAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze the structural completeness of a thesis",
)
async def analyze_structure(body: StructureAnalysisRequest) -> StructureAnalysisResponse:
    text = await _load_thesis_text(body.thesis_id)
    checker = StructureChecker(expected_sections=body.expected_sections)
    return checker.analyze(body.thesis_id, text)


@router.post(
    "/references",
    response_model=ReferencesAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate references and citation style",
)
async def analyze_references(body: ReferencesAnalysisRequest) -> ReferencesAnalysisResponse:
    text = await _load_thesis_text(body.thesis_id)
    checker = ReferencesChecker(citation_style=body.citation_style)
    return checker.analyze(body.thesis_id, text)


@router.post(
    "/format",
    response_model=FormatAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Check formatting against a template (stub — Phase 2 will expand this)",
)
async def analyze_format(body: FormatAnalysisRequest) -> FormatAnalysisResponse:
    # Phase 1 stub — full implementation in Phase 2 with template comparison
    return FormatAnalysisResponse(
        thesis_id=body.thesis_id,
        score=75.0,
        issues=[
            IssueItem(
                code="FORMAT_STUB",
                message="Format analysis not yet fully implemented.",
                severity=Severity.INFO,
                suggestion="Upload a template via POST /api/v1/thesis/template/upload for comparison.",
            )
        ],
        summary="Format analysis is a stub in Phase 1. Score is placeholder.",
    )


@router.post(
    "/full-report",
    response_model=FullReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a full analysis report for a thesis",
)
async def full_report(body: FullReportRequest) -> FullReportResponse:
    text = await _load_thesis_text(body.thesis_id)

    structure = None
    if body.include_structure:
        checker = StructureChecker()
        structure = checker.analyze(body.thesis_id, text)

    references = None
    if body.include_references:
        checker = ReferencesChecker(citation_style=body.citation_style)
        references = checker.analyze(body.thesis_id, text)

    format_result = None
    if body.include_format:
        format_result = FormatAnalysisResponse(
            thesis_id=body.thesis_id,
            score=75.0,
            issues=[],
            summary="Format analysis stub — Phase 2.",
        )

    return _report_gen.generate(
        thesis_id=body.thesis_id,
        structure=structure,
        references=references,
        format_result=format_result,
        report_format=body.report_format,
    )
