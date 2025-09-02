# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget git \
    && rm -rf /var/lib/apt/lists/*

# install runtime deps via pip (simple requirements)
COPY infra/requirements.txt /app/infra/requirements.txt
RUN pip install --no-cache-dir -r /app/infra/requirements.txt

# create non-root user
RUN useradd -ms /bin/bash appuser
USER appuser

# copy source
COPY --chown=appuser:appuser src /app/src
COPY --chown=appuser:appuser api.md /app/api.md

CMD ["python", "-m", "src.app.main"]
