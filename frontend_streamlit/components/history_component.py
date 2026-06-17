import streamlit as st
from datetime import datetime
from components.api_client import ThesisAPIClient


def render_thesis_history():
    """Renderiza el historial de tesis subidas"""
    
    st.subheader("📚 Historial de Tesis")
    
    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
        try:
            # Obtener lista de tesis
            thesis_list = client.list_thesis()
            
            if not thesis_list:
                st.info("💡 No hay tesis en el historial. Sube una nueva tesis para comenzar.")
                return None
            
            # Mostrar estadísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de tesis", len(thesis_list))
            with col2:
                completed = sum(1 for t in thesis_list if t.get("ai_analysis_status") == "completed")
                st.metric("Completadas", completed)
            with col3:
                pending = sum(1 for t in thesis_list if t.get("ai_analysis_status") == "pending")
                st.metric("Pendientes", pending)
            
            st.divider()
            
            # Lista de tesis
            selected_thesis = None
            
            for thesis in thesis_list:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{thesis['file_name']}**")
                        st.caption(f"ID: {thesis['id'][:8]}...")
                    
                    with col2:
                        # Estado del análisis
                        ai_status = thesis.get("ai_analysis_status", "pending")
                        status_icons = {
                            "pending": "⏳ Pendiente",
                            "processing": "🔄 Procesando",
                            "completed": "✅ Completado",
                            "failed": "❌ Error"
                        }
                        st.write(f"IA: {status_icons.get(ai_status, ai_status)}")
                        
                        # Estado de citas
                        cit_status = thesis.get("citation_check_status", "pending")
                        st.write(f"Citas: {status_icons.get(cit_status, cit_status)}")
                    
                    with col3:
                        # Fecha de subida
                        uploaded_at = thesis.get("uploaded_at")
                        if uploaded_at:
                            try:
                                date = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                                st.write(f"📅 {date.strftime('%d/%m/%Y')}")
                                st.caption(date.strftime('%H:%M'))
                            except:
                                st.write(uploaded_at[:10])
                    
                    with col4:
                        # Botones de acción
                        if st.button("📂 Cargar", key=f"load_{thesis['id']}", width="stretch"):
                            selected_thesis = thesis
                        
                        if st.button("🗑️", key=f"delete_{thesis['id']}", width="stretch"):
                            if st.session_state.get(f"confirm_delete_{thesis['id']}"):
                                try:
                                    client.delete_thesis(thesis['id'])
                                    st.success("Tesis eliminada")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al eliminar: {e}")
                            else:
                                st.session_state[f"confirm_delete_{thesis['id']}"] = True
                                st.rerun()
                    
                    st.divider()
            
            return selected_thesis
            
        except Exception as e:
            st.error(f"Error al cargar historial: {e}")
            return None


def render_thesis_selector():
    """Muestra un selector de tesis del historial"""
    
    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:
        try:
            thesis_list = client.list_thesis()
            
            if not thesis_list:
                return None
            
            # Crear opciones para el selectbox
            options = []
            for thesis in thesis_list:
                label = f"{thesis['file_name']} - {thesis.get('uploaded_at', '')[:10]}"
                options.append({
                    "label": label,
                    "id": thesis['id'],
                    "data": thesis
                })
            
            selected = st.selectbox(
                "📚 Seleccionar tesis del historial",
                options=options,
                format_func=lambda x: x["label"],
                index=None,
                placeholder="Elige una tesis existente..."
            )
            
            if selected:
                return selected["data"]
            
            return None
            
        except Exception as e:
            st.error(f"Error al cargar historial: {e}")
            return None
