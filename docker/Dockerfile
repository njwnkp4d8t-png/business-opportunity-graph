# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Copy package files first for better layer caching
COPY frontend/package*.json ./

# Install dependencies with error handling
# Use npm install instead of npm ci because this project
# does not include a package-lock.json in the repo.
RUN set -ex && \
    npm install --no-audit && \
    npm cache clean --force

# Copy frontend source
COPY frontend ./

# Build frontend with validation
RUN set -ex && \
    npm run build && \
    test -d dist && \
    test -f dist/index.html || { echo "ERROR: Frontend build failed - dist/index.html not found"; exit 1; }

# Stage 2: Python base with dependencies
FROM python:3.11-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VENV_PATH="/opt/venv" \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies with error handling
RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gdal-bin \
        libgdal-dev \
        libspatialindex-dev \
        libgeos-dev \
        libproj-dev \
        nginx-light \
        curl \
        ca-certificates \
        supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy and validate requirements.txt
COPY requirements.txt .
RUN test -f requirements.txt || { echo "ERROR: requirements.txt not found"; exit 1; }

# Create virtual environment and install Python dependencies
RUN set -ex && \
    python -m venv "${VENV_PATH}" && \
    "${VENV_PATH}/bin/pip" install --upgrade pip setuptools wheel && \
    "${VENV_PATH}/bin/pip" install --no-cache-dir -r requirements.txt jupyterlab && \
    "${VENV_PATH}/bin/pip" check

ENV PATH="${VENV_PATH}/bin:${PATH}"

# Copy application code
COPY . .

# Stage 3: Runtime
FROM python-base AS runtime

# Copy frontend build artifacts
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

# Validate frontend files were copied
RUN test -f /usr/share/nginx/html/index.html || { echo "ERROR: Frontend files not copied correctly"; exit 1; }

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
RUN test -f /etc/nginx/conf.d/default.conf || { echo "ERROR: nginx.conf not found"; exit 1; }

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy entrypoint script and normalize line endings
COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Create application user and set permissions
RUN set -ex && \
    useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /var/log/nginx /var/log/supervisor /var/lib/nginx /run /var/run/supervisor && \
    chown -R appuser:appuser \
        /app \
        /opt/venv \
        /var/log/nginx \
        /var/log/supervisor \
        /var/lib/nginx \
        /usr/share/nginx/html \
        /run \
        /var/run/supervisor \
        /entrypoint.sh

USER appuser

EXPOSE 8080

# Health check that validates nginx is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Use entrypoint script for proper service orchestration.
# Invoke via bash to avoid any line-ending/shebang issues.
ENTRYPOINT ["bash", "/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
