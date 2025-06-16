FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        curl \
        gnupg \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Application specific
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    DB_HOST=postgres-service \
    DB_NAME=secrets_db \
    DB_USER=postgres \
    DB_PASSWORD=postgres \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    WORKERS=4 \
    PORT=8000

# Create non-root user with specific UID/GID
RUN groupadd -g 1000 appgroup \
    && useradd -u 1000 -g appgroup -s /bin/bash -m appuser \
    && mkdir -p /app/logs /app/cache /vault/secrets \
    && chown -R appuser:appgroup /app /vault/secrets

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        procps \
    && rm -rf /var/lib/apt/lists/* \
    && curl -L https://github.com/opencontainers/runc/releases/download/v1.1.12/runc.amd64 -o /usr/local/bin/runc \
    && chmod +x /usr/local/bin/runc

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code with proper permissions
COPY --chown=appuser:appgroup . .

# Create log directory and set permissions
RUN touch /app/logs/app.log \
    && chown -R appuser:appgroup /app/logs

# Switch to non-root user
USER appuser

# Health check with proper timeout and interval
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application with gunicorn for better production performance
CMD ["sh", "-c", "gunicorn main:app --workers ${WORKERS} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --log-level ${LOG_LEVEL} --access-logfile /app/logs/access.log --error-logfile /app/logs/error.log"]