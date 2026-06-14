import json


def to_markdown_report(review: dict) -> str:
    summary = review.get("summary", {})
    ai_block = review.get("ai_review", {})
    return (
        "# Thesis Review Report\n\n"
        f"- Thesis ID: `{review.get('thesis_id', '-')}`\n"
        f"- Overall score: **{summary.get('overall_score', 0):.1f}**\n"
        f"- Similarity score: **{summary.get('similarity_score', 0):.1f}**\n"
        f"- AI generation probability: **{summary.get('ai_detection_score', 0):.1f}%**\n\n"
        "## Gemini Recommendations\n\n"
        f"{ai_block.get('review_text', 'No AI recommendations available.')}\n"
    )


def to_json_report(review: dict) -> str:
    return json.dumps(review, indent=2, ensure_ascii=False)
