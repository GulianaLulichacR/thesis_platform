import streamlit as st

st.title("Configuración")

backend_url = st.text_input("URL del Backend", value=st.session_state.get("backend_url", "http://localhost:8000"))
if st.button("Guardar"):
    st.session_state.backend_url = backend_url
    st.success("Configuración guardada.")