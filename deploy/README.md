# Docker 开发模式部署

当前仓库的前端入口已经切换为 Vite 开发服务模式，不再构建 `dist`，也不再通过 Nginx 提供静态页面。

## 端口

- `5188`：前端 Vite 开发服务
- `8888`：后端 API

## 首次启动

在项目根目录执行：

```bash
docker compose up -d
```

说明：

- `frontend` 容器会挂载本地 `./frontend` 源码目录
- 首次启动时如果容器内没有 `node_modules`，会自动执行 `npm ci`
- 前端服务启动后，浏览器访问 `http://<主机IP>:5188`

## 日常开发

修改以下目录中的前端代码后：

```text
frontend/src
frontend/public
frontend/vite.config.js
```

Vite 会自动热更新；如果个别改动没有自动反映，直接浏览器刷新即可。刷新后加载的仍然是当前源码，不会回退到旧静态包。

## 常用命令

启动：

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f frontend
docker compose logs -f backend
```

重启前端：

```bash
docker compose restart frontend
```

停止：

```bash
docker compose stop
```

完全关闭：

```bash
docker compose down
```

## 依赖更新

如果 `package.json` 或 `package-lock.json` 发生变化，执行：

```bash
docker compose restart frontend
```

如果需要强制重新安装前端依赖，可执行：

```bash
docker compose down
docker volume rm sanya-eco-monitor_frontend_node_modules
docker compose up -d
```

如果实际卷名不是 `sanya-eco-monitor_frontend_node_modules`，先用 `docker volume ls` 查看再删除。

## 后端准备

首次使用前，仍需准备：

```bash
cp backend/.env.example backend/.env
mkdir -p deploy/runtime/backend backend/data logs/backend
```

按需编辑 `backend/.env`，并确认数据库目录可写。

## 验证

后端健康检查：

```bash
curl http://127.0.0.1:8888/api/health
```

前端首页：

```bash
curl http://127.0.0.1:5188/
```

## 说明

这套链路是开发模式，不是生产静态部署方案。若后续需要恢复生产环境静态发布，需要重新设计单独的前端发布流程。
