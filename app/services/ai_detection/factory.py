from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ai_detection.base import BaseAIDetectionService
from app.services.ai_detection.copyleaks_ai_service import CopyleaksAIService
from app.services.ai_detection.gptzero_service import GPTZeroService
from app.services.ai_detection.mock_ai_detector import MockAIDetectionService
from app.services.ai_detection.originality_service import OriginalityAIService
from app.services.ai_detection.winston_service import WinstonAIService

settings = get_settings()
logger = get_logger(__name__)


class AIDetectionFactory:
    _registry: dict[str, type[BaseAIDetectionService]] = {
        "gptzero": GPTZeroService,
        "winston": WinstonAIService,
        "copyleaks": CopyleaksAIService,
        "originality": OriginalityAIService,
        "mock": MockAIDetectionService,
    }

    @classmethod
    def create_service(cls, provider: str | None = None) -> BaseAIDetectionService:
        requested = (provider or settings.AI_DETECTION_PROVIDER or "mock").lower()
        service_cls = cls._registry.get(requested)
        if service_cls:
            return service_cls()

        logger.warning(f"Unknown AI detection provider '{requested}', falling back to mock.")
        return MockAIDetectionService()
