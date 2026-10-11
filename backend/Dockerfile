# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# PYTHONDONTWRITEBYTECODE: no .pyc files in a layer that is read-only anyway.
# PYTHONUNBUFFERED: logs reach kubectl logs immediately instead of sitting in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies are their own layer, copied before the source, so editing a
# route does not invalidate the pip install on every rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Run as a non-root user. Created with --no-create-home and a fixed uid so the
# Kubernetes securityContext can pin runAsUser: 10001 to a real account.
RUN useradd --system --no-create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000

# Liveness only; it deliberately avoids the database. See app/main.py.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
