from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SupportedLanguage(str, Enum):
    ES = "es"
    EN = "en"
    PT = "pt"


# ─── Upload ───────────────────────────────────────────────────────────────────

class ThesisUploadResponse(BaseModel):
    thesis_id: str
    filename: str
    size_bytes: int
    pages: int | None = None
    language: SupportedLanguage = SupportedLanguage.ES
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = "Thesis uploaded successfully."


class TemplateUploadResponse(BaseModel):
    template_id: str
    filename: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = "Template uploaded successfully."


# ─── Metadata ─────────────────────────────────────────────────────────────────

class ThesisMetadata(BaseModel):
    thesis_id: str
    title: str | None = None
    author: str | None = None
    institution: str | None = None
    year: int | None = None
    pages: int | None = None
    word_count: int | None = None
    language: SupportedLanguage = SupportedLanguage.ES
    sections_found: list[str] = Field(default_factory=list)
    raw_text_preview: str | None = Field(None, description="First 500 characters of extracted text")


# ─── Sections ─────────────────────────────────────────────────────────────────

class ThesisSection(BaseModel):
    name: str
    found: bool
    page_hint: int | None = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    notes: str | None = None
