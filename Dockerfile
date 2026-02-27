FROM astral/uv:0.9-python3.14-bookworm-slim

#RUN addgroup --system --gid 1000 appuser && \
#    adduser --system --uid 1000 --ingroup appuser appuser
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app
#RUN chown appuser:appgroup /usr/local



ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
ENV PATH="/usr/local/bin:$PATH"
ENV PYTHONPATH="."
#ENV UV_LINK_MODE=copy
#ENV UV_CACHE_DIR=app/tmp/uv_cache


# Install the project's dependencies using the lockfile and settings
#RUN --mount=type=bind,source=uv.lock,target=uv.lock \
#    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#    uv sync --locked --no-install-project --no-dev --offline

#--mount=type=cache,target=/Users/ratchet/.cache/uv \

#COPY --chown=appuser:appuser pyproject.toml uv.lock ./
#COPY --chown=appuser:appuser . /app
COPY --chown=appuser:appuser . /app


#RUN uv run pip install --verbose --no-index --find-links ./offline_wheels -r requirements.txt
RUN uv sync --offline --no-index --find-links ./offline_wheels


#RUN --mount=type=bind,source=uv.lock,target=uv.lock \
#    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#    uv sync --locked --no-dev --offline

USER appuser


CMD ["uv", "run", "python", "src/main.py"]