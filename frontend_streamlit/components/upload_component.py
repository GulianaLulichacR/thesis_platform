"""
frontend_streamlit/components/upload_component.py
───────────────────────────────────────────────────
Upload widget.

Bugs fixed vs original
───────────────────────
1. asyncio.run() removed entirely — ThesisAPIClient is now synchronous.
2. httpx.Client is created once via context manager (not per-call).
3. File bytes read once from st.UploadedFile, not twice.
4. Session state is set atomically after a successful response — a failed
   request no longer leaves stale thesis_id from a previous upload.
5. A backend connectivity check runs before the expensive file upload so
   the user gets a clear message instead of a 60-second timeout.
6. File-size guard on the frontend reduces unnecessary network traffic.
7. st.rerun() called explicitly after state mutation to guarantee the UI
   refreshes without relying on Streamlit's implicit rerun heuristics.
"""

from __future__ import annotations

import streamlit as st

from components.api_client import APIClientError, ThesisAPIClient


# Max file size shown to the user (backend also enforces this).
_MAX_MB = 50


def render_upload_component() -> None:
    uploaded = st.file_uploader(
        "Upload thesis (.pdf / .docx)",
        type=["pdf", "docx"],
        help=f"Maximum file size: {_MAX_MB} MB",
    )

    if uploaded is None:
        return
        
    parent_thesis_id = st.text_input(
        "ID de Tesis Anterior (Opcional - para nueva versión)",
        help="Si estás subiendo una nueva versión de un avance anterior, ingresa el ID aquí."
    )
    parent_thesis_id = parent_thesis_id.strip() if parent_thesis_id else None

    # ── Client-side size guard ─────────────────────────────────────────────────
    file_bytes: bytes = uploaded.getvalue()
    size_mb = len(file_bytes) / (1024 * 1024)

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.caption(
            f"📄 **{uploaded.name}** — {size_mb:.2f} MB"
        )

    if size_mb > _MAX_MB:
        st.error(f"File exceeds the {_MAX_MB} MB limit. Please upload a smaller document.")
        return

    with col_btn:
        upload_clicked = st.button("Upload", type="primary", use_container_width=True, disabled=st.session_state.get("uploading", False),
    )

    if not upload_clicked:
        return

    # ── Upload flow ────────────────────────────────────────────────────────────
    # Use a context manager so the connection pool is properly released even
    # if an exception is raised mid-upload.
    with ThesisAPIClient(base_url=st.session_state.backend_url) as client:

        # 1. Quick connectivity check before sending the full file.
        with st.spinner("Checking backend connection…"):
            try:
                client.health()
            except APIClientError as exc:
                st.error(
                    f"Cannot reach the backend at `{st.session_state.backend_url}`.\n\n"
                    f"**Detail:** {exc}\n\n"
                    "Go to **Settings** and verify the Backend URL."
                )
                return

        # 2. Upload the file.
        with st.spinner(f"Uploading **{uploaded.name}** ({size_mb:.1f} MB)…"):
            try:
                result: dict = client.upload_thesis(uploaded.name, file_bytes)
            except APIClientError as exc:
                st.error(f"Upload failed: {exc}")
                return
            except Exception as exc:
                st.exception(exc)
                return

    # 3. Persist result to session state atomically (only on success).
    st.session_state["thesis_id"] = result["thesis_id"]
    st.session_state["upload_meta"] = result

    st.success(
        f"✅ Uploaded successfully!  "
        f"**Thesis ID:** `{result['thesis_id']}`  "
        f"— {result.get('pages') or '?'} pages"
    )

    # Explicit rerun so downstream pages that read thesis_id see the new value.
    st.rerun()