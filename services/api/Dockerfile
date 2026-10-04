FROM python:3.13-slim

WORKDIR /app

# Build context is the repo root (see docker-compose.yml).
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api/app ./app

# Runtime data files (also mounted from ./data in compose; this keeps
# standalone `docker run` working without the volume).
COPY data/index_meta.json ./data/index_meta.json
COPY data/qco_snapshot.yaml ./data/qco_snapshot.yaml
COPY data/glossary.yaml ./data/glossary.yaml

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
