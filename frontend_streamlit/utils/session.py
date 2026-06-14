"""
frontend_streamlit/utils/session.py
─────────────────────────────────────
Session state initialisation helpers.

Changes vs original
────────────────────
• backend_url is resolved from st.secrets → env var → hardcoded default,
  in that priority order. The original only checked st.secrets.
• A separate `backend_status` key tracks the last known health-check result
  so the sidebar can show a live indicator without a new HTTP call on every
  Streamlit rerun.
• init_session() is idempotent — safe to call at the top of every page.
"""

from __future__ import annotations

import os

import streamlit as st


_DEFAULTS: dict = {
    "backend_url": None,        # resolved below
    "backend_status": None,     # "ok" | "error" | None
    "thesis_id": None,
    "upload_meta": None,
    "last_review": None,
    "review_history": [],
    "active_tab": "upload",
}


def _resolve_backend_url() -> str:
    """Priority: st.secrets → STREAMLIT_BACKEND_URL env → localhost."""
    try:
        return str(st.secrets["STREAMLIT_BACKEND_URL"]).rstrip("/")
    except Exception:
        pass
    env_url = os.getenv("STREAMLIT_BACKEND_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    return "http://127.0.0.1:8000"

def init_session() -> None:
    """Populate st.session_state with default values (no-op if already set)."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # Resolve backend URL separately so it can depend on st.secrets.
    if not st.session_state.get("backend_url"):
        st.session_state["backend_url"] = _resolve_backend_url()


def clear_thesis() -> None:
    """Reset all thesis-related state (call after a new upload)."""
    for key in ("thesis_id", "upload_meta", "last_review"):
        st.session_state[key] = None
    st.session_state["review_history"] = []