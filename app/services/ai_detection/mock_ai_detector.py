import random

from app.schemas.ai_detection import AIDetectionResponse, SentenceAIDetection
from app.services.ai_detection.base import BaseAIDetectionService


class MockAIDetectionService(BaseAIDetectionService):
    async def analyze(self, text: str, filename: str | None = None) -> AIDetectionResponse:
        ai_probability = round(random.uniform(20.0, 45.0), 2)
        human_probability = round(100.0 - ai_probability, 2)
        verdict = "mostly_human" if ai_probability < 50 else "possibly_ai"

        sentences = [s.strip() for s in text.split(".") if s.strip()][:5]
        sentence_analysis = [
            SentenceAIDetection(
                text=sentence,
                ai_probability=round(random.uniform(max(ai_probability - 15, 0), min(ai_probability + 15, 100)), 2),
            )
            for sentence in sentences
        ]

        return AIDetectionResponse(
            provider="mock",
            ai_probability=ai_probability,
            human_probability=human_probability,
            verdict=verdict,
            sentence_analysis=sentence_analysis,
        )
