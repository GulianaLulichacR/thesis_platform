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
• Added persistent storage for uploaded files and their metadata
• Added helper functions to manage data across tabs
"""

from __future__ import annotations

import os
from typing import Any, Optional

import streamlit as st


# ==================== CONFIGURACIÓN POR DEFECTO ====================
_DEFAULTS: dict[str, Any] = {
    # Backend
    "backend_url": None,
    "backend_status": None,
    
    # Tesis actual
    "thesis_id": None,
    "upload_meta": None,
    "uploaded_file_name": None,
    "uploaded_file_size": None,
    
    # Historial y revisiones
    "last_review": None,
    "review_history": [],
    
    # Navegación
    "active_tab": "upload",
    
    # Archivos subidos (persistencia entre pestañas)
    "uploaded_files": [],
    "file_contents": {},
    
    # Estados de procesamiento
    "ai_analysis_status": "pending",
    "citation_check_status": "pending",
    
    # Mensajes y notificaciones
    "last_message": None,
    "message_type": None,  # "success", "error", "info", "warning"
}


# ==================== FUNCIONES DE INICIALIZACIÓN ====================
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


# ==================== FUNCIONES DE GESTIÓN DE DATOS ====================
def set_thesis_data(
    thesis_id: str, 
    meta: dict[str, Any], 
    file_name: Optional[str] = None, 
    file_size: Optional[int] = None
) -> None:
    """Store thesis data in session state (persists across tabs).
    
    Args:
        thesis_id: ID único de la tesis
        meta: Metadatos de la tesis
        file_name: Nombre del archivo (opcional)
        file_size: Tamaño del archivo en bytes (opcional)
    """
    st.session_state["thesis_id"] = thesis_id
    st.session_state["upload_meta"] = meta
    st.session_state["uploaded_file_name"] = file_name
    st.session_state["uploaded_file_size"] = file_size
    
    # Reset processing statuses
    st.session_state["ai_analysis_status"] = meta.get("ai_analysis_status", "pending")
    st.session_state["citation_check_status"] = meta.get("citation_check_status", "pending")


def update_thesis_status(
    ai_status: Optional[str] = None, 
    cit_status: Optional[str] = None
) -> None:
    """Update processing statuses without losing other data.
    
    Args:
        ai_status: Nuevo estado del análisis IA (opcional)
        cit_status: Nuevo estado de verificación de citas (opcional)
    """
    if ai_status is not None:
        st.session_state["ai_analysis_status"] = ai_status
    if cit_status is not None:
        st.session_state["citation_check_status"] = cit_status


def add_uploaded_file(
    file_name: str, 
    file_size: int, 
    file_content: Optional[bytes] = None
) -> None:
    """Add a file to the uploaded files list (persists across tabs).
    
    Args:
        file_name: Nombre del archivo
        file_size: Tamaño en bytes
        file_content: Contenido del archivo (opcional)
    """
    file_info: dict[str, Any] = {
        "name": file_name,
        "size": file_size,
        "uploaded_at": st.session_state.get("thesis_id"),
    }
    
    # Add to list if not already there
    existing_names = [f["name"] for f in st.session_state["uploaded_files"]]
    if file_name not in existing_names:
        st.session_state["uploaded_files"].append(file_info)
    
    # Store content if provided
    if file_content is not None:
        st.session_state["file_contents"][file_name] = file_content


def get_current_thesis() -> Optional[dict[str, Any]]:
    """Get current thesis data (returns None if no thesis uploaded).
    
    Returns:
        Diccionario con datos de la tesis o None si no hay tesis activa
    """
    thesis_id = st.session_state.get("thesis_id")
    if not thesis_id:
        return None
    
    return {
        "thesis_id": thesis_id,
        "meta": st.session_state.get("upload_meta"),
        "file_name": st.session_state.get("uploaded_file_name"),
        "file_size": st.session_state.get("uploaded_file_size"),
        "ai_status": st.session_state.get("ai_analysis_status"),
        "cit_status": st.session_state.get("citation_check_status"),
    }


def set_message(message: str, msg_type: str = "info") -> None:
    """Set a message to display (persists until cleared).
    
    Args:
        message: Texto del mensaje
        msg_type: Tipo de mensaje ("success", "error", "info", "warning")
    """
    st.session_state["last_message"] = message
    st.session_state["message_type"] = msg_type


def clear_message() -> None:
    """Clear the current message."""
    st.session_state["last_message"] = None
    st.session_state["message_type"] = None


def clear_thesis() -> None:
    """Reset all thesis-related state (call after a new upload)."""
    for key in ("thesis_id", "upload_meta", "uploaded_file_name", "uploaded_file_size"):
        st.session_state[key] = None
    
    st.session_state["review_history"] = []
    st.session_state["last_review"] = None
    
    # Reset processing statuses
    st.session_state["ai_analysis_status"] = "pending"
    st.session_state["citation_check_status"] = "pending"


def clear_all() -> None:
    """Reset ALL session state (use with caution)."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Re-initialize with defaults
    init_session()


# ==================== FUNCIONES AUXILIARES ====================
def has_active_thesis() -> bool:
    """Check if there's an active thesis being processed."""
    return st.session_state.get("thesis_id") is not None


def is_processing() -> bool:
    """Check if any background process is running."""
    ai_status = st.session_state.get("ai_analysis_status", "pending")
    cit_status = st.session_state.get("citation_check_status", "pending")
    return ai_status == "running" or cit_status == "running"


def get_uploaded_files_count() -> int:
    """Get the number of uploaded files."""
    return len(st.session_state.get("uploaded_files", []))