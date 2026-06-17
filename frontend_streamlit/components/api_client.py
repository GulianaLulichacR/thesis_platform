from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

_MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}


class APIClientError(Exception):
    """Raised when the backend returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ThesisAPIClient:
    """Synchronous HTTP client for the Thesis Platform backend."""

    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ThesisAPIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ─────────────────────────────────────────────────────────────
    # Core request handler
    # ─────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()

            return {"success": True, "text": response.text}

        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise APIClientError(
                f"API error {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc

        except httpx.ConnectError as exc:
            raise APIClientError(
                f"No se puede conectar al backend en {self.base_url}"
            ) from exc

        except httpx.TimeoutException as exc:
            raise APIClientError(
                f"Timeout al llamar {path}"
            ) from exc

        except httpx.HTTPError as exc:
            raise APIClientError(f"HTTP error: {exc}") from exc

        except Exception as exc:
            raise APIClientError(f"Error inesperado: {exc}") from exc

    # ─────────────────────────────────────────────────────────────
    # Health
    # ─────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        for path in ["/health", "/api/v1/health", "/docs", "/openapi.json"]:
            try:
                result = self._request("GET", path)
                return {"ok": True, "path": path, "response": result}
            except Exception:
                pass
        raise APIClientError(f"No hay endpoint de salud disponible en {self.base_url}")

    # ─────────────────────────────────────────────────────────────
    # Thesis
    # ─────────────────────────────────────────────────────────────

    def upload_thesis(
        self,
        file_path: str | None = None,
        file_name: str | None = None,
        file_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """Subir una tesis. Acepta ruta de archivo o bytes directamente."""
        if file_path is not None:
            file_name = file_name or os.path.basename(file_path)
            with open(file_path, "rb") as f:
                file_bytes = f.read()

        if file_name is None or file_bytes is None:
            raise ValueError("Debes proveer file_path o (file_name + file_bytes)")

        ext = file_name.rsplit(".", 1)[-1].lower()
        mime = _MIME_TYPES.get(ext, "application/octet-stream")
        files = {"file": (file_name, file_bytes, mime)}

        return self._request("POST", "/api/v1/thesis/upload", files=files)

    def list_thesis(self) -> list[dict[str, Any]]:
        """Listar todas las tesis subidas."""
        return self._request("GET", "/api/v1/thesis/")

    def get_thesis(self, thesis_id: str) -> dict[str, Any]:
        """Obtener metadatos de una tesis por ID."""
        return self._request("GET", f"/api/v1/thesis/{thesis_id}")

    def get_thesis_metadata(self, thesis_id: str) -> dict[str, Any]:
        """Obtener metadatos de la tesis."""
        return self._request("GET", f"/api/v1/thesis/{thesis_id}/metadata")

    def get_thesis_preview(self, thesis_id: str) -> dict[str, Any]:
        """Obtener información de vista previa."""
        try:
            return self._request("GET", f"/api/v1/thesis/{thesis_id}/preview")
        except APIClientError:
            # Fallback: construir respuesta mínima desde metadatos
            meta = self.get_thesis(thesis_id)
            return {
                "file_type": meta.get("file_type", "pdf"),
                "download_url": f"/api/v1/thesis/{thesis_id}/download",
            }

    def delete_thesis(self, thesis_id: str) -> dict[str, Any]:
        """Eliminar una tesis."""
        return self._request("DELETE", f"/api/v1/thesis/{thesis_id}")

    def upload_template(self, file_name: str, file_bytes: bytes) -> dict[str, Any]:
        ext = file_name.rsplit(".", 1)[-1].lower()
        mime = _MIME_TYPES.get(ext, "application/octet-stream")
        files = {"file": (file_name, file_bytes, mime)}
        return self._request("POST", "/api/v1/thesis/template/upload", files=files)

    # ─────────────────────────────────────────────────────────────
    # Review
    # ─────────────────────────────────────────────────────────────

    def run_full_review(
        self,
        thesis_id: str,
        provider: str = "gemini",
        model: str = DEFAULT_GEMINI_MODEL,
        include_structure: bool = True,
        include_references: bool = True,
        include_format: bool = True,
        include_similarity: bool = True,
        similarity_provider: str = "mock",
        include_ai_detection: bool = True,
        ai_detection_provider: str = "mock",
    ) -> dict[str, Any]:
        payload = {
            "thesis_id": thesis_id,
            "provider": provider,
            "model": model,
            "include_structure": include_structure,
            "include_references": include_references,
            "include_format": include_format,
            "include_similarity": include_similarity,
            "similarity_provider": similarity_provider,
            "include_ai_detection": include_ai_detection,
            "ai_detection_provider": ai_detection_provider,
        }
        return self._request("POST", "/api/v1/review/full", json=payload)

    # ─────────────────────────────────────────────────────────────
    # Chat
    # ─────────────────────────────────────────────────────────────

    def ask_question(
        self,
        thesis_id: str,
        question: str,
        provider: str = "gemini",
        model: str | None = DEFAULT_GEMINI_MODEL,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "thesis_id": thesis_id,
            "question": question,
            "provider": provider,
        }
        if model:
            payload["model"] = model
        return self._request("POST", "/api/v1/chat/question", json=payload)