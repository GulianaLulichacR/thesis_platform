from app.services.plagiarism.base import BasePlagiarismService
from app.schemas.review import SimilarityResponse

class GrammarlyService(BasePlagiarismService):
    async def analyze(self, text: str, filename: str | None = None) -> SimilarityResponse:
        # Placeholder for future Grammarly integration
        return SimilarityResponse(
            provider="grammarly",
            similarity_score=0.0,
            sources=[],
            ai_generated_probability=0.0
        )
