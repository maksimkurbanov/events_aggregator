FROM astral/uv:0.9-python3.14-bookworm-slim

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

ENV PYTHONPATH=.
#ENV PATH="/usr/local/bin:$PATH"

COPY --chown=appuser:appuser . /app

#RUN uv sync --offline --no-index --find-links ./ --locked --no-dev
RUN uv sync --locked --no-dev

USER appuser

CMD ["uv", "run", "python", "src/main.py"]