import streamlit as st

from utils.formatting import as_percent


def render_score_cards(summary: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall", f"{summary.get('overall_score', 0):.1f}")
    c2.metric("Similarity", f"{summary.get('similarity_score', 0):.1f}")
    c3.metric("AI Prob.", as_percent(summary.get("ai_detection_score", 0)))
    c4.metric("Structure", f"{summary.get('structure_score', 0):.1f}")
