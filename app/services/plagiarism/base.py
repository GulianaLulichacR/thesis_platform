from abc import ABC, abstractmethod
from app.schemas.review import SimilarityResponse

class BasePlagiarismService(ABC):
    @abstractmethod
    async def analyze(self, text: str, filename: str | None = None) -> SimilarityResponse:
        pass
