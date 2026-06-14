from app.core.logging import get_logger
from app.schemas.ai_detection import AIDetectionResponse
from app.services.ai_detection.base import BaseAIDetectionService
from app.services.ai_detection.mock_ai_detector import MockAIDetectionService

logger = get_logger(__name__)


class CopyleaksAIService(BaseAIDetectionService):
    async def analyze(self, text: str, filename: str | None = None) -> AIDetectionResponse:
        # Copyleaks free credits are account-dependent.
        # Use mock fallback unless a stable free-tier integration is configured.
        logger.info("Copyleaks AI detector uses mock fallback for free-tier safety.")
        return await MockAIDetectionService().analyze(text=text, filename=filename)
