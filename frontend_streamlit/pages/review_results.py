from __future__ import annotations

import streamlit as st

from components.api_client import APIClientError, ThesisAPIClient
from components.charts import render_summary_charts
from components.review_panels import render_review_panels
from components.score_cards import render_score_cards
from utils.session import init_session

init_session()

st.title("📋 Ejecución de Revisión y Resultados")

# ─────────────────────────────────────────────────────────────
# Protección: se requiere una tesis
# ─────────────────────────────────────────────────────────────
thesis_id: str | None = st.session_state.get("thesis_id")

if not thesis_id:
    st.warning("⬆️ Primero suba una tesis usando la página de Carga.")
    st.stop()

st.info(f"Tesis activa: `{thesis_id}`")

# ─────────────────────────────────────────────────────────────
# Formulario de revisión
# ─────────────────────────────────────────────────────────────
with st.form("review_form"):

    col1, col2 = st.columns(2)

    with col1:
        provider = st.selectbox(
            "Proveedor de Detección de IA",
            ["mock", "gptzero", "winston", "copyleaks"],
            help="'mock' funciona sin ninguna clave de API.",
        )

        llm_provider = st.selectbox(
            "Proveedor de LLM",
            ["gemini", "ollama"],
        )

    with col2:
        include_similarity = st.checkbox(
            "Incluir verificación de similitud",
            value=True,
        )

        include_ai_detection = st.checkbox(
            "Incluir detección de IA",
            value=True,
        )

    submitted = st.form_submit_button(
        "▶ Ejecutar revisión completa",
        type="primary",
        use_container_width=True,
    )

# ─────────────────────────────────────────────────────────────
# Ejecutar revisión
# ─────────────────────────────────────────────────────────────
if submitted:

    with st.spinner("Ejecutando revisión completa..."):

        try:
            client = ThesisAPIClient(
                base_url=st.session_state.backend_url
            )

            review_data = client.run_full_review(
                thesis_id=thesis_id,
                include_ai_detection=include_ai_detection,
                ai_detection_provider=provider,
                include_similarity=include_similarity,
                similarity_provider="mock",
            )

            st.session_state["last_review"] = review_data

            history = st.session_state.get(
                "review_history",
                [],
            )

            st.session_state["review_history"] = (
                [review_data] + history
            )[:20]

            st.success("Revisión completada exitosamente.")

            st.rerun()

        except APIClientError as exc:
            st.error(str(exc))
            st.stop()

        except Exception as exc:
            st.exception(exc)
            st.stop()

# ─────────────────────────────────────────────────────────────
# Resultados
# ─────────────────────────────────────────────────────────────

review_data: dict = st.session_state.get("last_review") or {}

if not review_data:
    st.info("Haga clic en **Ejecutar revisión completa** para iniciar el análisis.")
    st.stop()

render_score_cards(review_data.get("summary", {}))

tab_charts, tab_issues, tab_raw = st.tabs(
    ["📊 Gráficos", "🔍 Problemas y Recomendaciones", "🗂 JSON sin procesar"]
)

with tab_charts:
    render_summary_charts(review_data.get("summary", {}))

with tab_issues:
    render_review_panels(review_data)

with tab_raw:
    st.json(review_data)