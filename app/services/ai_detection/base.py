from abc import ABC, abstractmethod

from app.schemas.ai_detection import AIDetectionResponse


class BaseAIDetectionService(ABC):
    @abstractmethod
    async def analyze(self, text: str, filename: str | None = None) -> AIDetectionResponse:
        raise NotImplementedError
