from __future__ import annotations

import os
from typing import Any

import httpx


_MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}

# Constante a nivel de módulo (accesible desde los métodos)
DEFAULT_GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)


class APIClientError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class ThesisAPIClient:
    """
    Stable synchronous HTTP client for Streamlit + FastAPI.
    """

    def __init__(
        self,
        base_url: str | None = None,
        connect_timeout: float = 10.0,
        upload_timeout: float = 120.0,
        read_timeout: float = 300.0,
    ) -> None:

        self.base_url = (
            base_url
            or os.getenv(
                "STREAMLIT_BACKEND_URL",
                "http://127.0.0.1:8000",
            )
        ).rstrip("/")

        self._client = httpx.Client(
            base_url=self.base_url,
            follow_redirects=True,
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=upload_timeout,
                pool=connect_timeout,
            ),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            ),
        )

    # ─────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ThesisAPIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ─────────────────────────────────────────────────────────────
    # Core request handler
    # ─────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:

        try:
            response = self._client.request(
                method,
                path,
                **kwargs,
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "content-type",
                ""
            )

            if "application/json" in content_type:
                return response.json()

            return {
                "success": True,
                "text": response.text,
            }

        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise APIClientError(
                f"API error {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc

        except httpx.ConnectError as exc:
            raise APIClientError(
                f"Cannot connect to backend at {self.base_url}"
            ) from exc

        except httpx.TimeoutException as exc:
            raise APIClientError(
                f"Request timeout calling {path}"
            ) from exc

        except httpx.HTTPError as exc:
            raise APIClientError(
                f"HTTP error: {exc}"
            ) from exc

        except Exception as exc:
            raise APIClientError(
                f"Unexpected client error: {exc}"
            ) from exc

    # ─────────────────────────────────────────────────────────────
    # Health
    # ─────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        health_paths = [
            "/health",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
        ]

        last_error: Exception | None = None

        for path in health_paths:
            try:
                result = self._request("GET", path)
                return {
                    "ok": True,
                    "path": path,
                    "response": result,
                }
            except Exception as exc:
                last_error = exc

        raise APIClientError(
            f"No valid health endpoint found on backend: {self.base_url}\n"
            f"Last error: {last_error}"
        )

    # ─────────────────────────────────────────────────────────────
    # Thesis Upload
    # ─────────────────────────────────────────────────────────────

    def upload_thesis(
        self,
        file_name: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:

        ext = file_name.rsplit(".", 1)[-1].lower()
        mime = _MIME_TYPES.get(ext, "application/octet-stream")
        files = {"file": (file_name, file_bytes, mime)}

        return self._request(
            "POST",
            "/api/v1/thesis/upload",
            files=files,
        )

    def upload_template(
        self,
        file_name: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:

        ext = file_name.rsplit(".", 1)[-1].lower()
        mime = _MIME_TYPES.get(ext, "application/octet-stream")
        files = {"file": (file_name, file_bytes, mime)}

        return self._request(
            "POST",
            "/api/v1/thesis/template/upload",
            files=files,
        )

    # ─────────────────────────────────────────────────────────────
    # Metadata
    # ─────────────────────────────────────────────────────────────

    def get_thesis_metadata(
        self,
        thesis_id: str,
    ) -> dict[str, Any]:

        return self._request(
            "GET",
            f"/api/v1/thesis/{thesis_id}/metadata",
        )

    # ─────────────────────────────────────────────────────────────
    # Preview
    # ─────────────────────────────────────────────────────────────

    def get_thesis_preview(
        self,
        thesis_id: str,
    ) -> dict[str, Any]:
        """
        Obtiene la información de la vista previa de la tesis (URL, tipo de archivo, etc.).
        """
        return self._request(
            "GET",
            f"/api/v1/thesis/{thesis_id}/preview",
        )
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

        return self._request(
            "POST",
            "/api/v1/review/full",
            json=payload,
        )

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

        return self._request(
            "POST",
            "/api/v1/chat/question",
            json=payload,
        )