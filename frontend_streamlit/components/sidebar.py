import streamlit as st


def render_sidebar() -> None:
    st.sidebar.title("Thesis Review")
    st.sidebar.caption("Academic QA Dashboard")
    st.sidebar.info("Use the pages menu to upload, review and export reports.")
