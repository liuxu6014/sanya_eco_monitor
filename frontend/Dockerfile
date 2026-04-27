# Stage 1: Build
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Ensure we build for production
RUN npm run build

# Stage 2: Serve
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Copy standard nginx config for routing and proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /var/log/nginx
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/
CMD ["nginx", "-g", "daemon off;"]
