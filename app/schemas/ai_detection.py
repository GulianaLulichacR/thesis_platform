from pydantic import BaseModel, Field


class SentenceAIDetection(BaseModel):
    text: str
    ai_probability: float = Field(..., ge=0.0, le=100.0)


class AIDetectionResponse(BaseModel):
    provider: str
    ai_probability: float = Field(..., ge=0.0, le=100.0)
    human_probability: float = Field(..., ge=0.0, le=100.0)
    verdict: str
    sentence_analysis: list[SentenceAIDetection] = Field(default_factory=list)
