FROM astral/uv:0.9-python3.14-bookworm-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

ENV PYTHONPATH="."
#ENV PATH="/usr/local/bin:$PATH"
#ENV UV_LINK_MODE=copy
#ENV UV_CACHE_DIR=app/tmp/uv_cache

COPY --chown=appuser:appuser . /app

RUN uv sync --offline --no-index --find-links ./offline_wheels

USER appuser

CMD ["uv", "run", "python", "src/main.py"]