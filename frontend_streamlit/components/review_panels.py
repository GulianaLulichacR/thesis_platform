import streamlit as st


def render_review_panels(review: dict) -> None:
    ai_review = review.get("ai_review", {})
    ai_detection = review.get("ai_detection_analysis") or {}
    similarity = review.get("similarity_analysis") or {}

    with st.expander("Gemini Recommendations", expanded=True):
        st.write(ai_review.get("review_text", "No recommendations available."))

    with st.expander("AI-Generated Content Detection", expanded=True):
        st.write(f"Provider: `{ai_detection.get('provider', 'n/a')}`")
        st.progress(int(ai_detection.get("ai_probability", 0)))
        st.caption(f"Verdict: **{ai_detection.get('verdict', 'unknown')}**")

    with st.expander("Plagiarism Similarity", expanded=False):
        st.write(f"Provider: `{similarity.get('provider', 'n/a')}`")
        st.progress(int(similarity.get("similarity_score", 0)))
        for src in similarity.get("sources", []):
            st.write(f"- {src.get('source', 'unknown')} ({src.get('match_percentage', 0):.1f}%)")
