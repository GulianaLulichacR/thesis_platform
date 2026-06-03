import re

from app.core.logging import get_logger
from app.schemas.analysis import IssueItem, Severity, StructureAnalysisResponse

logger = get_logger(__name__)

# Default thesis sections to look for (in Spanish and English)
DEFAULT_SECTIONS = [
    "introducción",
    "introduction",
    "marco teórico",
    "theoretical framework",
    "metodología",
    "methodology",
    "resultados",
    "results",
    "discusión",
    "discussion",
    "conclusiones",
    "conclusions",
    "referencias",
    "references",
    "bibliografía",
    "bibliography",
]


class StructureChecker:
    """
    Checks whether a thesis document contains the expected structural sections.
    This is a heuristic-based implementation for Phase 1.
    Phase 2 will add LLM-assisted section detection.
    """

    def __init__(
        self,
        expected_sections: list[str] | None = None,
    ) -> None:
        self._expected = [s.lower() for s in (expected_sections or DEFAULT_SECTIONS)]

    def analyze(self, thesis_id: str, full_text: str) -> StructureAnalysisResponse:
        text_lower = full_text.lower()
        found: list[str] = []
        missing: list[str] = []
        issues: list[IssueItem] = []

        for section in self._expected:
            pattern = rf"\b{re.escape(section)}\b"
            if re.search(pattern, text_lower):
                found.append(section)
            else:
                missing.append(section)
                issues.append(
                    IssueItem(
                        code="MISSING_SECTION",
                        message=f"Section '{section}' not found in the document.",
                        severity=Severity.WARNING,
                        suggestion=f"Add a clearly labelled '{section.title()}' section.",
                    )
                )

        score = round((len(found) / len(self._expected)) * 100, 1) if self._expected else 100.0

        summary = (
            f"Found {len(found)}/{len(self._expected)} expected sections. "
            f"Score: {score}/100."
        )

        return StructureAnalysisResponse(
            thesis_id=thesis_id,
            score=score,
            sections_found=found,
            sections_missing=missing,
            issues=issues,
            summary=summary,
        )
