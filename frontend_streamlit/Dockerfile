FROM python:3.11-slim

WORKDIR /app

COPY frontend_streamlit/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY frontend_streamlit /app/frontend_streamlit
COPY .env.example /app/.env.example

ENV STREAMLIT_BACKEND_URL=http://api:8000
EXPOSE 8501

CMD ["streamlit", "run", "frontend_streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
