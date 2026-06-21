# 服务器部署教程

三亚市天涯区智慧农业生态监测平台 —— 基于 Docker Compose 的一键部署。

前端经 Nginx 托管静态产物并反代 `/api` 到后端（同源），后端仅在容器网络内暴露。

---

## 一、服务器准备

- 操作系统：Linux（Ubuntu 20.04+/CentOS 7+ 等均可）
- 已安装 **Docker** 与 **Docker Compose v2**、**git**
- 放行入站端口 **5188**（启用 HTTPS 再放行 **443**）

检查环境：

```bash
docker --version
docker compose version
git --version
```

> 未装 Docker 可执行：`curl -fsSL https://get.docker.com | sh`，随后 `sudo systemctl enable --now docker`。

---

## 二、拉取代码

```bash
git clone https://github.com/liuxu6014/sanya_eco_monitor.git
cd sanya_eco_monitor
```

---

## 三、配置后端环境变量（关键）

`.env` 不在仓库中，需从样例复制并填写：

```bash
cp backend/.env.example backend/.env
vi backend/.env
```

**至少要改这几项**：

| 变量 | 说明 |
|------|------|
| `ACCESS_PASSWORD` | 管理员登录密码（**务必改成强密码**） |
| `LEADER_ACCESS_PASSWORD` | 领导只读密码 |
| `PLATFORM_PASSWORD` | 第三方平台账号密码 |
| `LLM_API_KEY` | DeepSeek API Key（生成 AI 报告需要，不用可留空） |
| `IMAGE_GEN_API_KEY` | 图片生成 API Key（不用可留空） |
| `QWEATHER_API_KEY` / `QWEATHER_API_HOST` | 和风天气（不用可留空，并设 `QWEATHER_ENABLED=false`） |
| `AUTH_COOKIE_SECURE` | **纯 HTTP 部署填 `false`；配了 HTTPS 改 `true`** |

> 数据库默认用 SQLite，数据持久化到 `deploy/runtime/backend/sanya_eco.db`（compose 已挂载），无需额外配置。

---

## 四、构建并启动

```bash
docker compose up -d --build
```

首次会构建后端镜像（含中文字体、报告依赖）和前端镜像（npm 构建 + nginx），约几分钟。

查看状态与日志：

```bash
docker compose ps
docker compose logs -f backend     # 后端日志
docker compose logs -f frontend    # nginx 日志
```

两个容器都 `healthy` 即部署成功。

---

## 五、访问

浏览器打开（本项目挂在 **5188 端口的 `/sanya` 子路径**下）：

```
http://<服务器IP>:5188/sanya/
```

用 `ACCESS_PASSWORD` 登录。`/api` 由前端 Nginx 同源反代到后端，无需单独开放 8888 端口。

> 各页签地址：`/sanya/`（概览）、`/sanya/analytics`、`/sanya/special`、`/sanya/reports`。
> 如需改子路径或端口：改 `frontend/vite.config.js` 的 `base`、`src/utils/navigationTabs.js` 的 `BASE_PATH`、`frontend/nginx.conf` 的 `location /sanya/`、`docker-compose.yml` 的端口映射（四处保持一致）。

---

## 六、启用 HTTPS（强烈建议）

1. 准备证书，放到 `deploy/certs/`（需 `fullchain.pem` 与 `privkey.pem`）：

   ```bash
   mkdir -p deploy/certs
   # 将证书拷入：deploy/certs/fullchain.pem、deploy/certs/privkey.pem
   ```

2. 编辑 `frontend/nginx.conf`：取消文件底部 **HTTPS server 块** 与 **80→443 跳转块** 的注释，把 `your.domain.com` 改成你的域名。

3. 编辑 `docker-compose.yml` 的 `frontend` 服务：取消 `- "443:443"` 与 `certs` 卷的注释。

4. 后端 `backend/.env` 设 `AUTH_COOKIE_SECURE=true`。

5. 重新部署：

   ```bash
   docker compose up -d --build
   ```

> 如前后端分域名部署（不走同源反代），还需在 `backend/.env` 设 `CORS_ALLOW_ORIGINS=https://你的前端域名`。

---

## 七、日常运维

```bash
# 更新代码并重新部署
git pull
docker compose up -d --build

# 重启 / 停止
docker compose restart
docker compose down

# 备份数据库
cp deploy/runtime/backend/sanya_eco.db ~/sanya_eco_backup_$(date +%Y%m%d).db

# 手动触发一次数据采集（需管理员登录态，调试用）
# 在平台界面操作，或登录后请求 /api/collect/trigger
```

数据采集由后端 APScheduler 自动按 `COLLECT_INTERVAL_MINUTES`（默认 30 分钟，可在 `.env` 调）执行。

---

## 八、常见问题

- **登录返回 401**：`.env` 的 `ACCESS_PASSWORD` 未设置或填错；改后 `docker compose up -d` 重启 backend。
- **前端打开空白**：等待 `frontend` 容器 `healthy`；`docker compose logs frontend` 看 nginx 是否启动。
- **后端起不来**：`docker compose logs backend`，多为 `.env` 缺失或第三方平台地址/账号错误。
- **HTTPS 配后登录掉线**：确认 `AUTH_COOKIE_SECURE=true` 且确实经 HTTPS 访问（HTTP 下 Secure cookie 不会回传）。
- **采集不到数据**：检查服务器能否访问第三方平台地址（`PLATFORM_BASE_URL` / `WHXPH_BASE_URL`），以及账号密码是否正确。
