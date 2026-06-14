# Streamlit Deployment Guide

## Required env vars
- `STREAMLIT_BACKEND_URL`

## Streamlit Cloud
1. Set app path to `frontend_streamlit/app.py`.
2. Add `STREAMLIT_BACKEND_URL` in Secrets.
3. Install from `frontend_streamlit/requirements.txt`.

## Render / Railway
1. Start command: `streamlit run frontend_streamlit/app.py --server.port=$PORT --server.address=0.0.0.0`
2. Build command: `pip install -r frontend_streamlit/requirements.txt`
3. Set `STREAMLIT_BACKEND_URL` to public FastAPI URL.

## HuggingFace Spaces (Docker)
1. Use Docker SDK.
2. Build with `frontend_streamlit/Dockerfile`.
3. Set `STREAMLIT_BACKEND_URL` in Space variables.

## Docker (local)
```bash
docker compose up --build
```
