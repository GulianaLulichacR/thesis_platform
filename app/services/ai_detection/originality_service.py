from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.ai_detection import AIDetectionResponse
from app.services.ai_detection.base import BaseAIDetectionService
from app.services.ai_detection.mock_ai_detector import MockAIDetectionService

settings = get_settings()
logger = get_logger(__name__)


class OriginalityAIService(BaseAIDetectionService):
    async def analyze(self, text: str, filename: str | None = None) -> AIDetectionResponse:
        if not settings.ORIGINALITY_API_KEY:
            logger.warning("Originality API key missing, falling back to mock detector.")
            return await MockAIDetectionService().analyze(text=text, filename=filename)

        # Placeholder while keeping extension point for future free-tier support.
        return await MockAIDetectionService().analyze(text=text, filename=filename)
