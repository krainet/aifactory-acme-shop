# One image for the web and worker roles. Base images are multi-arch (amd64 and arm64).
FROM ghcr.io/astral-sh/uv:0.11.19 AS uv

FROM python:3.12.14-slim
COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /app
# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

RUN useradd --create-home --uid 10001 acme
USER acme
EXPOSE 8080
CMD ["uvicorn", "acme_shop.main:app", "--host", "0.0.0.0", "--port", "8080"]
