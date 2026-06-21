# AI Business Automator — Dockerfile (HF Spaces, production, multi-tenant)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY config.py server.py ./
COPY client_config.json ./
COPY static/ ./static/
COPY run.sh ./

# Hugging Face Spaces sets PORT=7860 automatically
EXPOSE 7860

# Run with uvicorn directly (no reload in prod)
CMD ["python", "server.py"]
