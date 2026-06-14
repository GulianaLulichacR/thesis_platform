from pydantic import BaseModel, Field

from app.schemas.ai_detection import AIDetectionResponse
from app.schemas.analysis import (
    FormatAnalysisResponse,
    ReferencesAnalysisResponse,
    StructureAnalysisResponse,
)


class FullReviewRequest(BaseModel):
    thesis_id: str
    provider: str = "gemini"
    model: str = "gemini-1.5-flash"
    include_structure: bool = True
    include_references: bool = True
    include_format: bool = True
    include_similarity: bool = True
    similarity_provider: str | None = None
    include_ai_detection: bool = False
    ai_detection_provider: str | None = None


class SimilaritySource(BaseModel):
    source: str
    match_percentage: float = Field(..., ge=0.0, le=100.0)


class SimilarityResult(BaseModel):
    provider: str
    similarity_score: float = Field(..., ge=0.0, le=100.0)
    sources: list[SimilaritySource]
    ai_generated_probability: float = Field(0.0, ge=0.0, le=100.0)


# Backward compatibility for existing plagiarism providers.
SimilarityResponse = SimilarityResult


class ReviewSummary(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    structure_score: float = Field(..., ge=0.0, le=100.0)
    references_score: float = Field(..., ge=0.0, le=100.0)
    format_score: float = Field(..., ge=0.0, le=100.0)
    similarity_score: float = Field(0.0, ge=0.0, le=100.0)
    ai_detection_score: float = Field(0.0, ge=0.0, le=100.0)


class FullReviewResponse(BaseModel):
    thesis_id: str
    summary: ReviewSummary
    ai_review: dict
    structure_analysis: StructureAnalysisResponse | None = None
    references_analysis: ReferencesAnalysisResponse | None = None
    format_analysis: FormatAnalysisResponse | None = None
    similarity_analysis: SimilarityResult | None = None
    ai_detection_analysis: AIDetectionResponse | None = None
