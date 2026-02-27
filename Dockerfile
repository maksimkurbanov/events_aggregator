FROM astral/uv:0.9-python3.14-bookworm-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

ENV PYTHONPATH=/app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY --chown=appuser:appuser . /app

USER appuser

CMD ["uv", "run", "python", "src/main.py"]
#CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
