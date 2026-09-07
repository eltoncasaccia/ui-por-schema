# Multi-stage: a imagem final nao carrega ferramenta de build nem cache.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY entrypoint.sh ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

FROM python:3.13-slim-bookworm AS run
WORKDIR /app
# Usuario nao-root: container de API nao roda como root.
RUN useradd --create-home --uid 10001 app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/saude')" || exit 1
CMD ["./entrypoint.sh"]
