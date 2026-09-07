FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/ ./src/
COPY logging_config.yml ./

RUN uv sync --frozen

COPY docker/app/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8797", "--workers", "5" ]