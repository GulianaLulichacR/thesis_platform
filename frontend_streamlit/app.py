import streamlit as st

from components.sidebar import render_sidebar
from utils.session import init_session

init_session()

st.set_page_config(
    page_title="Plataforma de Revisión de Tesis",
    page_icon="🎓",
    layout="wide",
)

st.title("Plataforma de Revisión de Tesis")
st.markdown(
    "Frontend en Streamlit para ejecutar y visualizar revisiones académicas "
    "consumiendo únicamente el backend FastAPI."
)
