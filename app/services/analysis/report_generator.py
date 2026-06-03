import json
from typing import Any

from app.core.logging import get_logger
from app.schemas.analysis import (
    FormatAnalysisResponse,
    FullReportResponse,
    ReferencesAnalysisResponse,
    ReportFormat,
    StructureAnalysisResponse,
)

logger = get_logger(__name__)


class ReportGenerator:
    """
    Assembles and renders full thesis review reports.
    Supports JSON, Markdown, and HTML output formats.
    Phase 2: add PDF export via WeasyPrint.
    """

    def generate(
        self,
        thesis_id: str,
        structure: StructureAnalysisResponse | None,
        references: ReferencesAnalysisResponse | None,
        format_result: FormatAnalysisResponse | None,
        report_format: ReportFormat,
    ) -> FullReportResponse:
        scores: list[float] = []
        if structure:
            scores.append(structure.score)
        if references:
            scores.append(references.score)
        if format_result:
            scores.append(format_result.score)

        overall = round(sum(scores) / len(scores), 1) if scores else 0.0
        executive_summary = self._make_executive_summary(overall, structure, references)

        report_content: Any = None
        if report_format == ReportFormat.JSON:
            report_content = self._as_json(thesis_id, overall, structure, references, format_result)
        elif report_format == ReportFormat.MARKDOWN:
            report_content = self._as_markdown(thesis_id, overall, structure, references, format_result)
        elif report_format == ReportFormat.HTML:
            report_content = self._as_html(thesis_id, overall, structure, references, format_result)

        return FullReportResponse(
            thesis_id=thesis_id,
            overall_score=overall,
            structure=structure,
            references=references,
            format=format_result,
            report_format=report_format,
            report_content=report_content,
            executive_summary=executive_summary,
        )

    def _make_executive_summary(self, overall: float, s: Any, r: Any) -> str:
        parts = [f"Overall score: {overall}/100."]
        if s:
            parts.append(f"Structure: {s.score}/100 — {len(s.sections_missing)} missing sections.")
        if r:
            parts.append(f"References: {r.score}/100 — {r.invalid_references} invalid entries.")
        return " | ".join(parts)

    def _as_json(self, thesis_id: str, overall: float, s: Any, r: Any, f: Any) -> dict:
        return {
            "thesis_id": thesis_id,
            "overall_score": overall,
            "structure": s.model_dump() if s else None,
            "references": r.model_dump() if r else None,
            "format": f.model_dump() if f else None,
        }

    def _as_markdown(self, thesis_id: str, overall: float, s: Any, r: Any, f: Any) -> str:
        lines = [
            f"# Thesis Review Report",
            f"**Thesis ID:** `{thesis_id}`  ",
            f"**Overall Score:** {overall}/100",
            "",
        ]
        if s:
            lines += [
                "## Structure Analysis",
                f"- **Score:** {s.score}/100",
                f"- **Sections found:** {', '.join(s.sections_found) or 'none'}",
                f"- **Missing:** {', '.join(s.sections_missing) or 'none'}",
                f"- {s.summary}",
                "",
            ]
        if r:
            lines += [
                "## References Analysis",
                f"- **Score:** {r.score}/100",
                f"- **Total:** {r.total_references} | Valid: {r.valid_references} | Invalid: {r.invalid_references}",
                f"- {r.summary}",
                "",
            ]
        return "\n".join(lines)

    def _as_html(self, thesis_id: str, overall: float, s: Any, r: Any, f: Any) -> str:
        md = self._as_markdown(thesis_id, overall, s, r, f)
        rows = "".join(f"<p>{line}</p>" for line in md.split("\n") if line.strip())
        return f"<html><body>{rows}</body></html>"
