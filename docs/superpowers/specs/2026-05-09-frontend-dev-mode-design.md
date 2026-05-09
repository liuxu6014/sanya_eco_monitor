# 前端源码直出开发模式设计

日期：2026-05-09

## 背景

当前 `frontend` 服务通过 Docker 多阶段构建产出静态 `dist`，再由 Nginx 提供页面。页面里的“刷新”按钮会执行整页 `reload`，因此浏览器会重新加载容器内的旧静态资源。如果容器没有重建，页面会立即回退到旧布局。

用户希望把当前 `5188` 入口直接改成开发环境的源码直出模式，确保：

- 浏览器刷新后仍然拿到当前源码
- 前端改动可实时生效
- 不再依赖手工 `build` 才能看到最新布局
- `frontend/Dockerfile` 和 `frontend/nginx.conf` 不再保留

## 目标

将当前 Docker Compose 中的 `frontend` 服务从“静态资源发布容器”改为“Vite 开发服务容器”，让 `http://<host>:5188` 直接对应仓库中的 `frontend/` 源码。

## 非目标

- 不同时保留生产态和开发态双前端服务
- 不继续支持当前 Nginx 静态部署链路
- 不修改后端接口路径和认证机制
- 不在本次变更中重构页面组件逻辑

## 方案选择

### 方案 A：把现有 `frontend` 服务直接切换为 Vite 开发服务

优点：

- 实现最直接，符合用户诉求
- `5188` 入口语义清晰，不存在“看的是哪套前端”的歧义
- Docker Compose 仍然是一条命令启动

缺点：

- 当前 `frontend` 服务不再适合作为生产部署方案
- 容器启动速度会慢于 Nginx 静态服务

### 方案 B：新增 `frontend-dev`，保留原 `frontend`

优点：

- 开发态和静态态并存
- 兼容已有部署习惯

缺点：

- 增加维护复杂度
- 用户当前明确不要保留旧链路

### 结论

采用方案 A。

## 目标架构

### 变更前

- `frontend/Dockerfile` 构建 `dist`
- Nginx 从 `/usr/share/nginx/html` 提供静态文件
- 浏览器刷新重新请求旧静态包

### 变更后

- `frontend` 容器直接基于 `node` 运行
- 容器内挂载仓库 `./frontend` 源码目录
- 启动命令为 Vite 开发服务，监听 `0.0.0.0:5188`
- 浏览器访问 `5188` 时由 Vite 实时提供源码构建结果
- `/api` 继续通过 Vite 代理转发到后端 `8888`

## 详细设计

### 1. `docker-compose.yml`

`frontend` 服务调整为：

- 使用 `node:20` 或与当前项目兼容的 Node 版本镜像
- 工作目录设为 `/app`
- 挂载 `./frontend:/app`
- 挂载独立的 npm 缓存或 `node_modules` 卷，避免宿主污染和安装抖动
- 启动命令改为先安装依赖再启动 Vite
- 对外端口继续暴露 `5188:5188`
- 保留对 `backend` 的依赖

### 2. `vite.config.js`

需要确认并固定：

- `server.host = '0.0.0.0'`
- `server.port = 5188`
- `/api` 代理目标在容器内应指向 `http://backend:8888`

为了兼容本地非容器运行，代理目标继续允许通过环境变量覆盖。

### 3. 依赖安装策略

为避免每次容器启动都全量重新装包，优先使用以下方式：

- 源码目录挂载：`./frontend:/app`
- 命名卷挂载：`/app/node_modules`
- 启动命令：
  - 若 `node_modules` 缺失，执行 `npm ci`
  - 若已存在，直接启动 Vite

如果实现上为了简化先统一执行 `npm install` 或 `npm ci`，也可以接受，但文档中要说明首次启动和后续启动的差异。

### 4. 删除旧静态部署文件

删除：

- `frontend/Dockerfile`
- `frontend/nginx.conf`

同时更新相关文档，避免后续有人继续按旧静态链路部署。

### 5. 文档更新

需要更新 `deploy/README.md`，明确：

- 当前仓库默认前端入口为开发模式源码直出
- 启动命令仍然是 `docker compose up -d`
- 修改前端源码后刷新页面即可看到最新结果
- 如果未来需要生产态静态部署，需要重新设计独立发布链路

## 数据流

### 页面加载

1. 浏览器访问 `http://host:5188`
2. 请求到达 Vite 开发服务
3. Vite 按当前源码即时编译并返回页面和模块
4. 页面中的 `/api/*` 请求通过 Vite 代理转发至 `backend:8888`

### 页面刷新

1. 浏览器执行整页 reload
2. 重新请求 Vite 开发服务
3. 返回当前源码对应的最新模块
4. 页面不会再回退到旧 `dist`

## 风险与约束

### 风险

- 开发服务性能和稳定性低于静态 Nginx
- 容器内文件监听在 Windows + Docker 场景下可能需要轮询模式
- 首次安装依赖耗时较长

### 应对

- 如文件变更监听不稳定，可启用 Vite/Chokidar 轮询
- 将 `node_modules` 使用卷隔离，避免宿主目录依赖冲突
- 文档明确这是开发模式，不作为正式生产发布方案

## 验证方案

完成后需验证：

1. `docker compose up -d frontend backend` 可成功启动
2. 访问 `http://127.0.0.1:5188` 能打开页面
3. 修改 `frontend/src` 任一可见文本后，浏览器无需重建即可看到变化
4. 点击页面“刷新”或浏览器 F5 后，页面仍保持最新布局
5. `/api/health`、页面登录和主要数据接口通过 Vite 代理仍能工作

## 实施清单

- 修改 `docker-compose.yml` 中的 `frontend` 服务
- 调整 `frontend/vite.config.js`
- 删除 `frontend/Dockerfile`
- 删除 `frontend/nginx.conf`
- 更新 `deploy/README.md`
- 运行前端启动和页面刷新验证

