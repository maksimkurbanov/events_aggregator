FROM astral/uv:0.9-python3.14-bookworm-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

ENV EVENT_PROVIDER_URL="http://events-provider.dev-2.python-labs.ru"
ENV LMS_API_KEY=$LMS_API_KEY
ENV PYTHONPATH="/app"

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY --chown=appuser:appuser . /app

USER appuser

CMD ["uv", "run", "python", "src/main.py"]
