import re

from app.core.logging import get_logger
from app.schemas.analysis import IssueItem, ReferenceItem, ReferencesAnalysisResponse, Severity

logger = get_logger(__name__)

# Rough APA 7 pattern: Author(s), (Year). Title. Journal/Publisher.
APA7_PATTERN = re.compile(
    r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:,\s[A-Z]\.)+(?:,\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:,\s[A-Z]\.)+)*"
    r"\s*\(\d{4}\)\.\s.+\."
)

REFERENCE_BLOCK_HEADERS = re.compile(
    r"(?:referencias|references|bibliograf[ií]a|bibliography|works cited)",
    re.IGNORECASE,
)


class ReferencesChecker:
    """
    Extracts and validates references using heuristic pattern matching.
    Phase 2: replace/augment with LLM-based reference extraction.
    """

    def __init__(self, citation_style: str = "APA7") -> None:
        self._style = citation_style

    def analyze(self, thesis_id: str, full_text: str) -> ReferencesAnalysisResponse:
        raw_refs = self._extract_references(full_text)
        items: list[ReferenceItem] = []

        for raw in raw_refs:
            issues: list[str] = []
            valid = False

            if self._style.upper().startswith("APA"):
                valid, issues = self._validate_apa7(raw)
            else:
                # For non-APA styles, basic checks only
                valid = len(raw.strip()) > 20
                if not valid:
                    issues.append("Reference too short or malformed.")

            items.append(
                ReferenceItem(
                    raw=raw,
                    valid=valid,
                    issues=issues,
                    suggested_fix=None,  # Phase 2: LLM suggestion
                )
            )

        valid_count = sum(1 for i in items if i.valid)
        total = len(items)
        score = round((valid_count / total) * 100, 1) if total else 0.0

        global_issues: list[IssueItem] = []
        if total == 0:
            global_issues.append(
                IssueItem(
                    code="NO_REFERENCES",
                    message="No reference section found in the document.",
                    severity=Severity.ERROR,
                    suggestion="Add a 'References' or 'Bibliografía' section at the end.",
                )
            )

        return ReferencesAnalysisResponse(
            thesis_id=thesis_id,
            citation_style=self._style,
            total_references=total,
            valid_references=valid_count,
            invalid_references=total - valid_count,
            score=score,
            references=items,
            issues=global_issues,
            summary=f"{valid_count}/{total} references pass {self._style} validation. Score: {score}/100.",
        )

    def _extract_references(self, text: str) -> list[str]:
        """Find the references section and split into individual entries."""
        match = REFERENCE_BLOCK_HEADERS.search(text)
        if not match:
            return []

        ref_block = text[match.end():]
        # Split on lines that start with an uppercase letter after a blank line
        entries = re.split(r"\n(?=[A-ZÁÉÍÓÚÑ])", ref_block)
        return [e.strip() for e in entries if len(e.strip()) > 15][:100]

    def _validate_apa7(self, ref: str) -> tuple[bool, list[str]]:
        issues: list[str] = []

        ref = ref.strip()

        # Validate year/date
        if not re.search(r"\(\d{4}(?:,[^)]+)?\)", ref):
            issues.append(
                "Missing valid year/date in parentheses."
            )
        # Basic length validation
        if len(ref) < 30:
            issues.append(
            "Reference seems too short to be complete."
        )
        # Detect URL or DOI at end
        has_url = re.search(
            r"(https?://\S+|doi\.org/\S+)$",
            ref,
            re.IGNORECASE,
        )
        # Validate final punctuation
        if not has_url and not ref.endswith("."):
            issues.append(
                "Reference should end with a period."
            )

        return len(issues) == 0, issues
