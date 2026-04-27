#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/ubuntu/uploads/sanya_eco_monitor"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$FRONTEND_DIR"
npm ci
npm run build
