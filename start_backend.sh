#!/bin/bash
# 启动后端服务
cd backend
echo "正在检查并安装后端依赖..."
uv sync
echo "正在启动 FastAPI 服务 (端口 8888)..."
uv run uvicorn main:app --host 0.0.0.0 --port 8888 --reload
