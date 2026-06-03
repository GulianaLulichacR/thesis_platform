"""Phase 1 integration tests — run with: pytest tests/ -v"""
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200


def test_upload_invalid_extension():
    fake_file = io.BytesIO(b"not a real file")
    resp = client.post(
        "/api/v1/thesis/upload",
        files={"file": ("test.txt", fake_file, "text/plain")},
    )
    assert resp.status_code == 415


def test_analysis_missing_thesis():
    resp = client.post(
        "/api/v1/analysis/structure",
        json={"thesis_id": "nonexistent_id_000"},
    )
    assert resp.status_code == 500  # StorageError


def test_openapi_docs():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    # Verify key routes exist
    assert "/api/v1/thesis/upload" in data["paths"]
    assert "/api/v1/analysis/structure" in data["paths"]
    assert "/api/v1/analysis/references" in data["paths"]
    assert "/api/v1/analysis/full-report" in data["paths"]
    assert "/api/v1/chat/question" in data["paths"]
