from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class IssueItem(BaseModel):
    code: str
    message: str
    severity: Severity
    location: str | None = None
    suggestion: str | None = None


# ─── Structure Analysis ───────────────────────────────────────────────────────

class StructureAnalysisRequest(BaseModel):
    thesis_id: str
    expected_sections: list[str] | None = Field(
        None,
        description="Override default expected sections. If None, uses platform defaults.",
        examples=[["introduction", "methodology", "results", "conclusions", "references"]],
    )


class StructureAnalysisResponse(BaseModel):
    thesis_id: str
    score: float = Field(..., ge=0.0, le=100.0, description="Structure completeness score 0-100")
    sections_found: list[str]
    sections_missing: list[str]
    issues: list[IssueItem]
    summary: str


# ─── References Analysis ─────────────────────────────────────────────────────

class ReferencesAnalysisRequest(BaseModel):
    thesis_id: str
    citation_style: str = Field("APA7", examples=["APA7", "APA6", "IEEE", "MLA"])


class ReferenceItem(BaseModel):
    raw: str
    valid: bool
    issues: list[str] = Field(default_factory=list)
    suggested_fix: str | None = None


class ReferencesAnalysisResponse(BaseModel):
    thesis_id: str
    citation_style: str
    total_references: int
    valid_references: int
    invalid_references: int
    score: float = Field(..., ge=0.0, le=100.0)
    references: list[ReferenceItem]
    issues: list[IssueItem]
    summary: str


# ─── Format Analysis ─────────────────────────────────────────────────────────

class FormatAnalysisRequest(BaseModel):
    thesis_id: str
    template_id: str | None = None


class FormatAnalysisResponse(BaseModel):
    thesis_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    issues: list[IssueItem]
    summary: str


# ─── Full Report ─────────────────────────────────────────────────────────────

class ReportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class FullReportRequest(BaseModel):
    thesis_id: str
    include_structure: bool = True
    include_references: bool = True
    include_format: bool = True
    citation_style: str = "APA7"
    report_format: ReportFormat = ReportFormat.JSON
    template_id: str | None = None


class FullReportResponse(BaseModel):
    thesis_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    structure: StructureAnalysisResponse | None = None
    references: ReferencesAnalysisResponse | None = None
    format: FormatAnalysisResponse | None = None
    report_format: ReportFormat
    report_content: str | dict[str, Any] | None = None
    executive_summary: str
