# ==============================================================================
# ARGUS — Backend Multi-Stage Dockerfile (backend/Dockerfile)
# ==============================================================================

# Build Stage
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final Runtime Stage
FROM python:3.11-slim AS runner

WORKDIR /app

RUN groupadd -r argus && useradd -r -g argus -d /app argus

COPY --from=builder /install /usr/local
COPY backend/ /app/backend/
COPY data/ /app/data/
COPY RegulatoryDocs/ /app/RegulatoryDocs/

# Environment variables for Cloud Run runtime
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    ARGUS_PROVIDER_MODE=live \
    PYTHONPATH=/app

USER argus

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2"]
