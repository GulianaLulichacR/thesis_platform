from app.services.plagiarism.base import BasePlagiarismService
from app.schemas.review import SimilarityResponse
import random

class MockPlagiarismService(BasePlagiarismService):
    async def analyze(self, text: str, filename: str | None = None) -> SimilarityResponse:
        # Simulate similarity score
        similarity_score = random.uniform(0, 100)
        sources = [
            {"source": "https://example.com/paper1", "match_percentage": random.uniform(0, 20)},
            {"source": "https://example.com/paper2", "match_percentage": random.uniform(0, 20)}
        ]
        return SimilarityResponse(
            provider="mock",
            similarity_score=similarity_score,
            sources=sources,
            ai_generated_probability=random.uniform(0, 10)
        )
