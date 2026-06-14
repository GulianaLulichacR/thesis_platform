from app.services.plagiarism.base import BasePlagiarismService
from app.schemas.review import SimilarityResponse

class OriginalityService(BasePlagiarismService):
    async def analyze(self, text: str, filename: str | None = None) -> SimilarityResponse:
        # Placeholder for future Originality.ai integration
        return SimilarityResponse(
            provider="originality",
            similarity_score=0.0,
            sources=[],
            ai_generated_probability=0.0
        )
