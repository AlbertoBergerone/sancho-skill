# FieldLog API - multi-stage, non-root, pinned base image (see docs/adr/0002-containers.md)
#
# The digest below is an EXAMPLE placeholder. Pin the real one before building:
#   docker buildx imagetools inspect python:3.12-slim --format '{{.Manifest.Digest}}'
ARG PYTHON_IMAGE=python:3.12-slim@sha256:0000000000000000000000000000000000000000000000000000000000000000

FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY api/requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --require-hashes -r requirements.txt
COPY api/app ./app

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /build/app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
# Secrets (DATABASE_URL, JWT_SECRET) are injected at runtime, never baked into the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
