#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/ubuntu/uploads/sanya_eco_monitor"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  uv sync
else
  uv sync --frozen
fi

exec uv run uvicorn main:app --host 0.0.0.0 --port 8888
