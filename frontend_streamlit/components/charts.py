import plotly.graph_objects as go
import streamlit as st


def render_summary_charts(summary: dict) -> None:
    categories = ["Structure", "References", "Format", "Similarity"]
    values = [
        summary.get("structure_score", 0),
        summary.get("references_score", 0),
        summary.get("format_score", 0),
        summary.get("similarity_score", 0),
    ]
    fig = go.Figure(data=[go.Bar(x=categories, y=values)])
    fig.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig,  width=True)
