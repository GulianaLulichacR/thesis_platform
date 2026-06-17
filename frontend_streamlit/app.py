import streamlit as st
import streamlit.components.v1 as components

from utils.session import init_session
from components.upload_component import render_upload_component
from components.api_client import ThesisAPIClient, APIClientError
from components.sidebar import render_sidebar

# Inicializar session
init_session()

st.set_page_config(
    page_title="Plataforma de Análisis de Tesis",
    page_icon="📄",
    layout="wide"
)
render_sidebar()

st.title("📄 Plataforma de Análisis de Tesis")

# ─────────────────────────────────────────────
# Pestañas: Subir nueva / Cargar del historial
# ─────────────────────────────────────────────
tab_upload, tab_history = st.tabs(["📤 Subir nueva tesis", "📚 Cargar del historial"])

with tab_upload:
    st.write("Sube un archivo PDF o DOCX para comenzar el análisis.")

    uploaded_file = st.file_uploader(
        "Selecciona tu archivo",
        type=["pdf", "docx"],
        help="Tamaño máximo: 50 MB",
        key="main_file_uploader",
    )

    if uploaded_file:
        st.success(f"✅ Archivo seleccionado: **{uploaded_file.name}**")
        st.info(f"Tamaño: {uploaded_file.size / 1024:.2f} KB")

        if st.button("📤 Subir tesis", type="primary", use_container_width=True):
            with st.spinner("Subiendo archivo al servidor..."):
                try:
                    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
                        result = client.upload_thesis(
                            file_name=uploaded_file.name,
                            file_bytes=uploaded_file.getvalue(),
                        )

                    # Guardar en session_state
                    thesis_id = result.get("thesis_id") or result.get("id")
                    st.session_state.thesis_id = thesis_id
                    st.session_state.upload_meta = result
                    st.session_state.uploaded_file_name = uploaded_file.name

                    st.success("✅ Tesis subida correctamente")
                    st.balloons()
                    st.rerun()

                except APIClientError as e:
                    st.error(f"❌ Error de API: {e}")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {e}")

with tab_history:
    st.write("Selecciona una tesis que ya hayas subido anteriormente.")
    # Importar aquí para evitar circular imports
    from components.history_component import render_thesis_history, render_thesis_selector

    selected = render_thesis_selector()
    if selected:
        st.divider()
        st.subheader("📄 Detalles de la tesis seleccionada")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Archivo:** {selected.get('file_name', 'N/A')}")
            size = selected.get("file_size", 0)
            st.write(f"**Tamaño:** {size / 1024:.2f} KB" if size else "**Tamaño:** N/A")
            st.write(f"**Tipo:** {selected.get('file_type', 'N/A').upper()}")
        with col2:
            st.write(f"**Estado IA:** {selected.get('ai_analysis_status', 'pending')}")
            st.write(f"**Estado Citas:** {selected.get('citation_check_status', 'pending')}")

        if st.button("📂 Cargar esta tesis", type="primary", use_container_width=True):
            st.session_state.thesis_id = selected["id"]
            st.session_state.upload_meta = selected
            st.success(f"✅ Tesis '{selected.get('file_name', '')}' cargada")
            st.rerun()

    st.divider()
    render_thesis_history()

# ─────────────────────────────────────────────
# Estado del documento activo
# ─────────────────────────────────────────────
if st.session_state.get("thesis_id"):
    thesis_id = st.session_state.thesis_id

    st.divider()
    st.subheader("📊 Estado del Documento Activo")

    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
        try:
            with st.spinner("Cargando información..."):
                meta = client.get_thesis(thesis_id)

            col1, col2 = st.columns(2)
            status_icons = {"pending": "⏳", "processing": "🔄", "completed": "✅", "failed": "❌"}

            with col1:
                ai_status = meta.get("ai_analysis_status", "pending")
                st.write(f"**Análisis IA:** {status_icons.get(ai_status, '❓')} {ai_status}")

            with col2:
                cit_status = meta.get("citation_check_status", "pending")
                st.write(f"**Verificación Citas:** {status_icons.get(cit_status, '❓')} {cit_status}")

            if ai_status == "processing" or cit_status == "processing":
                st.info("🔄 Procesando en segundo plano...")
                if st.button("🔄 Refrescar estado", use_container_width=True):
                    st.rerun()

            # Vista previa
            st.divider()
            st.subheader("👁️ Vista Previa")

            preview_info = client.get_thesis_preview(thesis_id)
            file_type = (preview_info.get("file_type") or "").lower()

            if file_type == "pdf":
                download_url = f"{st.session_state.backend_url}{preview_info['download_url']}"
                components.iframe(download_url, height=800, scrolling=True)
            else:
                with st.expander("📄 Vista Previa del Documento", expanded=True):
                    text_preview = meta.get("raw_text_preview", "No se pudo extraer texto.")
                    st.text(text_preview)

        except APIClientError as exc:
            st.error(f"❌ Error de API: {exc}")
        except Exception as exc:
            st.error(f"❌ Error inesperado: {exc}")
else:
    st.info("💡 Sube una tesis nueva o carga una del historial para comenzar")
