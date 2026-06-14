from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported FREE LLM providers only."""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: ChatMessageRole
    content: str


class ChatRequest(BaseModel):
    thesis_id: str
    question: str = Field(..., min_length=3, max_length=2000)
    provider: LLMProvider = LLMProvider.GEMINI
    model: str | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=64, le=8192)
    system_prompt: str | None = None
    use_fallback: bool = True  # Automatically try next provider on failure


class ChatResponse(BaseModel):
    thesis_id: str
    answer: str
    provider: LLMProvider
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    used_fallback: bool = False  # True if the primary provider failed


class LLMGenerateRequest(BaseModel):
    provider: LLMProvider = LLMProvider.GEMINI
    model: str | None = None
    prompt: str
    system_prompt: str | None = None
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=64, le=8192)
    extra_params: dict[str, Any] = Field(default_factory=dict)
    use_fallback: bool = True  # Allow fallback chain


class LLMGenerateResponse(BaseModel):
    text: str
    provider: LLMProvider
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    used_fallback: bool = False
    cache_hit: bool = False
