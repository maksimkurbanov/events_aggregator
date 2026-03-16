#!/bin/bash
set -e

uv run alembic upgrade head
exec uv run python -m src.main