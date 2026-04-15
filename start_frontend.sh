#!/bin/bash
# 启动前端服务
cd frontend
echo "正在检查并安装前端依赖..."
npm install
echo "正在启动 Vite 开发服务器 (端口 5175)..."
npm run dev
