# Server Persistent Run

Recommended long-running setup:

- Backend: `systemd` service for FastAPI/uvicorn
- Frontend: `npm run build` once, then serve `frontend/dist` with Nginx

Files provided in this repo:

- `scripts/server/run_backend_prod.sh`
- `scripts/server/build_frontend.sh`
- `deploy/systemd/sanya-eco-backend.service`
- `deploy/nginx/sanya-eco-monitor.conf`

Key points:

- Do not use `uvicorn --reload` on the server for long-running service.
- Do not use `npm run dev` on the server for long-running service.
- Use `systemctl enable --now sanya-eco-backend` for backend auto-start.
- Use Nginx for frontend static hosting and `/api` reverse proxy.
