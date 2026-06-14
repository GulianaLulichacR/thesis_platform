import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.ai_detection import AIDetectionResponse
from app.services.ai_detection.base import BaseAIDetectionService
from app.services.ai_detection.mock_ai_detector import MockAIDetectionService

settings = get_settings()
logger = get_logger(__name__)


class GPTZeroService(BaseAIDetectionService):
    async def analyze(self, text: str, filename: str | None = None) -> AIDetectionResponse:
        if not settings.GPTZERO_API_KEY:
            logger.warning("GPTZero API key missing, falling back to mock detector.")
            return await MockAIDetectionService().analyze(text=text, filename=filename)

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
                response = await client.post(
                    "https://api.gptzero.me/v2/predict/text",
                    headers={"x-api-key": settings.GPTZERO_API_KEY},
                    json={"document": text},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning(f"GPTZero failed, using mock fallback: {exc}")
            return await MockAIDetectionService().analyze(text=text, filename=filename)

        documents = payload.get("documents", [])
        if not documents:
            return await MockAIDetectionService().analyze(text=text, filename=filename)

        first_doc = documents[0]
        ai_probability = round(float(first_doc.get("completely_generated_prob", 0.0)) * 100, 2)
        human_probability = round(max(0.0, 100.0 - ai_probability), 2)

        verdict = "mostly_human"
        if ai_probability >= 70:
            verdict = "likely_ai"
        elif ai_probability >= 45:
            verdict = "mixed"

        return AIDetectionResponse(
            provider="gptzero",
            ai_probability=ai_probability,
            human_probability=human_probability,
            verdict=verdict,
            sentence_analysis=[],
        )
