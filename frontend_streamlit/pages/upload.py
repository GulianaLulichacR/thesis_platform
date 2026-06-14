import streamlit as st
import streamlit.components.v1 as components  # <--- FIX: Importar explícitamente

from utils.session import init_session
from components.upload_component import render_upload_component
from components.api_client import ThesisAPIClient


# Inicializar session_state
init_session()

st.title("Subir Tesis")

render_upload_component()

import time

if st.session_state.get("thesis_id"):
    thesis_id = st.session_state.thesis_id
    st.subheader("Estado del Documento")
    
    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
        try:
            meta = client.get_thesis_metadata(thesis_id)
            preview_info = client.get_thesis_preview(thesis_id) # Asegúrate de que este método exista en api_client.py
            
            # Show Statuses
            ai_status = meta.get("ai_analysis_status", "pending")
            cit_status = meta.get("citation_check_status", "pending")
            
            col1, col2 = st.columns(2)
            col1.metric("Análisis IA (Plantilla)", ai_status.upper())
            col2.metric("Validación de Citas", cit_status.upper())
            
            # Action if running
            if ai_status == "running" or cit_status == "running":
                st.info("Procesando en segundo plano... Refresca la página para ver actualizaciones.")
                if st.button("Refrescar"):
                    st.rerun()
            
            # Preview Document
            st.subheader("Vista Previa")
            file_type = preview_info.get("file_type")
            
            if file_type == "pdf":
                download_url = f"{st.session_state.backend_url}{preview_info['download_url']}"
                # <--- FIX: Usar el módulo importado directamente
                components.iframe(download_url, height=800, scrolling=True) 
            else:
                with st.expander("Vista Previa del Documento (DOCX)", expanded=True):
                    text_preview = meta.get("raw_text_preview", "No se pudo extraer texto.")
                    st.text(text_preview)
                    
            st.json(meta)
        except Exception as exc:
            st.error(f"Error al cargar información del documento: {exc}")