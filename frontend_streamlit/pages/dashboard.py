import streamlit as st

from components.score_cards import render_score_cards

st.title("Panel de Control")
history = st.session_state.get("review_history", [])

if not history:
    st.info("Aún no hay historial de revisiones.")
else:
    latest = history[0]
    st.subheader("Última revisión")
    render_score_cards(latest.get("summary", {}))
    st.subheader("Historial de revisiones")
    for idx, item in enumerate(history, start=1):
        with st.expander(f"Revisión #{idx} - Tesis {item.get('thesis_id', 'desconocido')}"):
            st.json(item.get("summary", {}))