# 多阶段构建：node 构建静态产物 → nginx 托管 + 反代 /api（生产用，替代 vite dev server）
ARG NPM_REGISTRY=https://registry.npmmirror.com

FROM node:20-alpine AS build
ARG NPM_REGISTRY
WORKDIR /app
COPY package*.json ./
RUN npm config set registry "$NPM_REGISTRY" && npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
