import streamlit as st

from utils.helpers import to_json_report, to_markdown_report

st.title("Informes")
review = st.session_state.get("last_review")
if not review:
    st.info("Primero ejecute una revisión.")
    st.stop()

json_report = to_json_report(review)
md_report = to_markdown_report(review)

st.download_button("Descargar informe JSON", data=json_report, file_name="thesis_review_report.json", mime="application/json")
st.download_button("Descargar informe Markdown", data=md_report, file_name="thesis_review_report.md", mime="text/markdown")

st.subheader("Vista previa")
st.code(md_report)