# Frontend Dev Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 `frontend` 服务切换为 Vite 源码直出开发模式，确保 `5188` 刷新后始终加载当前源码而不是旧静态包。

**Architecture:** 保留 `backend` 容器不变，把 `frontend` 从 Nginx 静态站点改成 Node + Vite 开发服务容器。通过 Docker Compose 挂载 `./frontend` 源码目录，Vite 监听 `0.0.0.0:5188`，并把 `/api` 代理到 `backend:8888`。

**Tech Stack:** Docker Compose, Node 20, Vite 5, React 18

---

### Task 1: 为开发态部署配置补回归测试

**Files:**
- Create: `frontend/tests/devModeConfig.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const compose = readFileSync(new URL('../../docker-compose.yml', import.meta.url), 'utf8')
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')

test('frontend service runs Vite dev server instead of serving built dist', () => {
  assert.match(compose, /frontend:[\s\S]*image:\s*node:20/i)
  assert.match(compose, /frontend:[\s\S]*5188:5188/i)
  assert.match(compose, /frontend:[\s\S]*vite --host 0\.0\.0\.0 --port 5188/i)
  assert.doesNotMatch(compose, /frontend:[\s\S]*dockerfile:\s*Dockerfile/i)
})

test('vite dev server is reachable from docker network and proxies api to backend', () => {
  assert.match(viteConfig, /host:\s*['"]0\.0\.0\.0['"]/)
  assert.match(viteConfig, /port:\s*5188/)
  assert.match(viteConfig, /VITE_API_PROXY_TARGET \|\| ['"]http:\/\/backend:8888['"]/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/devModeConfig.test.mjs`

Expected: FAIL because current compose 仍然使用 `build + Dockerfile + nginx`。

- [ ] **Step 3: Write minimal implementation**

修改配置文件，使测试通过，不在这一步处理文档。

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/devModeConfig.test.mjs`

Expected: PASS

### Task 2: 切换 frontend 容器到源码直出模式

**Files:**
- Modify: `docker-compose.yml`
- Modify: `frontend/vite.config.js`
- Delete: `frontend/Dockerfile`
- Delete: `frontend/nginx.conf`

- [ ] **Step 1: Update docker-compose frontend service**

目标状态：

```yaml
  frontend:
    image: node:20
    container_name: sanya-eco-frontend
    working_dir: /app
    environment:
      VITE_API_PROXY_TARGET: http://backend:8888
      CHOKIDAR_USEPOLLING: "true"
    command: >
      sh -c "if [ ! -d node_modules ] || [ -z \"$(ls -A node_modules 2>/dev/null)\" ]; then npm ci; fi &&
      npm run dev -- --host 0.0.0.0 --port 5188"
    ports:
      - "5188:5188"
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
      - ./logs/frontend:/app/.vite-logs
```

- [ ] **Step 2: Update Vite dev server config**

目标状态：

```js
const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://backend:8888'

server: {
  host: '0.0.0.0',
  port: 5188,
  proxy: {
    '/api': {
      target: proxyTarget,
      changeOrigin: true,
    },
  },
},
```

- [ ] **Step 3: Remove obsolete static deployment files**

删除：

```text
frontend/Dockerfile
frontend/nginx.conf
```

- [ ] **Step 4: Run regression test**

Run: `node --test frontend/tests/devModeConfig.test.mjs`

Expected: PASS

### Task 3: 更新部署文档

**Files:**
- Modify: `deploy/README.md`

- [ ] **Step 1: Write the failing documentation expectation mentally against current README**

当前 README 仍然描述 `docker compose up -d --build` 的静态部署流程，不符合新模式。

- [ ] **Step 2: Rewrite deployment instructions for dev mode**

至少覆盖：

```md
- frontend 现在运行的是 Vite 开发服务，不再构建 dist
- 启动使用 `docker compose up -d`
- 首次启动 frontend 会自动安装依赖
- 修改 frontend/src 后，浏览器刷新即可看到最新代码
- 如需重新安装依赖，可执行 `docker compose restart frontend`
```

- [ ] **Step 3: Verify docs changed as intended**

Run: `Select-String -Path 'deploy\\README.md' -Pattern 'Vite|源码|docker compose up -d|dist|Nginx'`

Expected: 文档中明确写出 Vite 开发模式，并移除旧静态部署描述。

### Task 4: 完整验证

**Files:**
- Verify only

- [ ] **Step 1: Run config regression test**

Run: `node --test frontend/tests/devModeConfig.test.mjs`

Expected: PASS

- [ ] **Step 2: Validate Vite config syntax**

Run: `npm install`

Run: `npm run build`

Workdir: `frontend`

Expected: PASS（即便运行时改成 dev server，源码本身仍可构建）

- [ ] **Step 3: Validate compose file shape**

Run: `docker compose config`

Expected: PASS，且 `frontend` 服务不再引用 `build.context: ./frontend`

