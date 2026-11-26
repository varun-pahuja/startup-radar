# Build stage
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install uv && \
    /install/bin/uv pip install --no-cache-dir --prefix=/install -e .

# Runtime stage
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:${PATH}" \
    HOME=/app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Create dirs for data, reports, config (mounted at runtime)
RUN mkdir -p data reports config drafts

EXPOSE 8000

# Default runs the dashboard; override with CLI commands
CMD ["startup-radar", "serve", "--host", "0.0.0.0", "--port", "8000"]