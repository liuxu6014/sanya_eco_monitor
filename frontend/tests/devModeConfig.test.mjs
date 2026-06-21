import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const compose = readFileSync(new URL('../../docker-compose.yml', import.meta.url), 'utf8')
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')

test('frontend service serves a production build via nginx (not a vite dev server)', () => {
  // 生产 compose：前端走 Dockerfile 多阶段构建 + nginx 托管，不再在容器里跑 vite dev server。
  assert.match(compose, /frontend:[\s\S]*dockerfile:\s*Dockerfile/i)
  assert.doesNotMatch(compose, /frontend:[\s\S]*vite --host/i)
  const nginx = readFileSync(new URL('../nginx.conf', import.meta.url), 'utf8')
  assert.match(nginx, /proxy_pass\s+http:\/\/backend:8888/)
  // 挂在子路径 /sanya 下，SPA 回退到 /sanya/index.html
  assert.match(nginx, /location \/sanya\//)
  assert.match(nginx, /try_files \$uri \$uri\/ \/sanya\/index\.html/)
})

test('vite dev config still supports local `npm run dev` proxy to backend', () => {
  assert.match(viteConfig, /host:\s*['"]0\.0\.0\.0['"]/)
  assert.match(viteConfig, /port:\s*5188/)
  assert.match(viteConfig, /VITE_API_PROXY_TARGET \|\| ['"]http:\/\/localhost:8888['"]/)
})
