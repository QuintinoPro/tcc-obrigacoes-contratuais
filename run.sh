#!/usr/bin/env bash
# Sobe o protótipo em http://localhost:8000
cd "$(dirname "$0")"
[ -d .venv ] || { uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt; }
exec .venv/bin/uvicorn app.main:create_app --factory --port "${PORT:-8000}"
