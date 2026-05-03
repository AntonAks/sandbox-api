# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --frozen --no-install-project; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi


FROM python:3.12-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
RUN chown app:app /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY --chown=app:app src/ ./src/
COPY --chown=app:app alembic/ ./alembic/
COPY --chown=app:app alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8000/health/live', timeout=3); sys.exit(0)" || exit 1

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
