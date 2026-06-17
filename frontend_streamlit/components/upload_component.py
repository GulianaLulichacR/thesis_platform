"""
upload_component.py
──────────────────
Módulo de compatibilidad. La lógica de subida e historial fue
consolidada en app.py. Este archivo re-exporta las funciones del
historial para que otros módulos que importen desde aquí no se rompan.
"""
from components.history_component import render_thesis_history, render_thesis_selector  # noqa: F401


def render_upload_component() -> None:
    """Función vacía de compatibilidad; la UI real está en app.py."""
    pass