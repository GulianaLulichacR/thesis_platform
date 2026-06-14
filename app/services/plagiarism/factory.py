from app.services.plagiarism.base import BasePlagiarismService
from app.services.plagiarism.copyleaks_service import CopyleaksService
from app.services.plagiarism.mock_service import MockPlagiarismService

class PlagiarismServiceFactory:
    @staticmethod
    def create_service(provider: str) -> BasePlagiarismService:
        normalized = (provider or "mock").lower()
        if normalized == "mock":
            return MockPlagiarismService()
        if normalized == "copyleaks":
            return CopyleaksService()
        # Safe fallback to avoid runtime crashes on missing/unknown provider.
        return MockPlagiarismService()
