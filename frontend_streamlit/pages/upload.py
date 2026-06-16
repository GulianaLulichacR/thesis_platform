import streamlit as st
import streamlit.components.v1 as components
import time

from utils.session import init_session
from components.upload_component import render_upload_component
from components.api_client import ThesisAPIClient


# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(
    page_title="Subir Tesis",
    page_icon="📄",
    layout="wide"
)

# Inicializar session_state
init_session()


# ==================== FUNCIONES AUXILIARES ====================
def get_status_icon(status: str) -> str:
    """Retorna un icono según el estado del proceso."""
    icons = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌"
    }
    return icons.get(status, "❓")


def get_status_color(status: str) -> str:
    """Retorna un color según el estado."""
    colors = {
        "pending": "blue",
        "running": "orange",
        "completed": "green",
        "failed": "red"
    }
    return colors.get(status, "gray")


def render_status_badge(label: str, status: str):
    """Renderiza un badge con el estado del proceso."""
    icon = get_status_icon(status)
    st.markdown(f"#### {label}: {icon} **{status.upper()}**")


def render_pdf_preview(download_url: str):
    """Renderiza la vista previa de un PDF."""
    try:
        components.iframe(download_url, height=800, scrolling=True)
    except Exception as e:
        st.error(f"Error al cargar el PDF: {e}")
        st.markdown(f"[Descargar PDF]({download_url})")


def render_docx_preview(text_preview: str):
    """Renderiza la vista previa de un DOCX."""
    with st.expander("📄 Vista Previa del Documento (DOCX)", expanded=True):
        st.text(text_preview or "No se pudo extraer texto.")


def auto_refresh_if_processing(ai_status: str, cit_status: str, interval: int = 5):
    """Auto-refresca si hay procesos en ejecución."""
    if ai_status == "running" or cit_status == "running":
        st.info(f"🔄 Procesando en segundo plano... Refrescando automáticamente cada {interval}s")
        time.sleep(interval)
        st.rerun()


# ==================== COMPONENTE PRINCIPAL ====================
st.title("📄 Subir Tesis")

# Renderizar componente de subida
render_upload_component()

# ==================== ESTADO DEL DOCUMENTO ====================
thesis_id = st.session_state.get("thesis_id")

if thesis_id:
    st.divider()
    st.subheader("📊 Estado del Documento")
    
    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
        try:
            # Obtener datos con spinner
            with st.spinner("Cargando información del documento..."):
                meta = client.get_thesis_metadata(thesis_id)
                preview_info = client.get_thesis_preview(thesis_id)
            
            # Extraer estados
            ai_status = meta.get("ai_analysis_status", "pending")
            cit_status = meta.get("citation_check_status", "pending")
            
            # Auto-refresh si está procesando
            auto_refresh_if_processing(ai_status, cit_status)
            
            # Botón de refresh manual
            if st.button("🔄 Refrescar Estado", width="content"):
                st.rerun()
            
            # ==================== VISTA PREVIA ====================
            st.divider()
            st.subheader("👁️ Vista Previa")
            
            file_type = preview_info.get("file_type", "").lower()
            
            if file_type == "pdf":
                download_url = f"{st.session_state.backend_url}{preview_info['download_url']}"
                render_pdf_preview(download_url)
            elif file_type in ["docx", "doc"]:
                text_preview = meta.get("raw_text_preview", "")
                render_docx_preview(text_preview)
            else:
                st.warning(f"Tipo de archivo no soportado para vista previa: {file_type}")
            
            # ==================== METADATOS (DEBUG) ====================
            with st.expander("🔍 Metadatos Completos (Debug)", expanded=False):
                st.json(meta)
                
        except Exception as exc:
            st.error(f"❌ Error al cargar información del documento: {exc}")
            
            # Botón para reintentar
            if st.button("🔁 Reintentar"):
                st.rerun()
else:
    st.info("💡 Sube un documento para ver su estado y vista previa.")