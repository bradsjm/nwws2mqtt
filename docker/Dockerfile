# Dockerfile for NWWS2MQTT - Optimized multi-stage build with UV
ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

# Set build arguments and environment variables
ARG PYTHON_VERSION
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for building including geospatial and scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libhdf5-dev \
    libnetcdf-dev \
    libeccodes-dev \
    libjpeg-dev \
    libpng-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    libspatialindex-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the project
RUN uv sync --frozen --no-dev

# Production stage - slim runtime image
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

# Set runtime environment variables
ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

# Install runtime system dependencies including geospatial and scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libssl3 \
    ca-certificates \
    tzdata \
    libgdal32 \
    libgeos-c1v5 \
    libproj25 \
    libhdf5-103-1 \
    libnetcdf19 \
    libeccodes0 \
    libjpeg62-turbo \
    libpng16-16 \
    libopenjp2-7 \
    zlib1g \
    libspatialindex6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Set working directory
WORKDIR /app

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Default command
CMD ["python", "-m", "nwws"]