# DSA-110 Services Quick Reference

## TL;DR - What to Use

| I want to...                     | Command                                           |
| -------------------------------- | ------------------------------------------------- |
| **Start everything (dev)**       | Open workspace in VS Code (auto-runs preflight)   |
| **Run frontend (dev)**           | `cd frontend && npm run dev`                      |
| **Run API (dev)**                | VS Code Task: "Backend: Start API Server"         |
| **Check system health**          | `./scripts/preflight-check.sh`                    |
| **Start production services**    | `sudo systemctl start contimg-api dsa110-contimg-dashboard` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUCTION                                │
├─────────────────────────────────────────────────────────────────┤
│  contimg-api.service          → FastAPI backend      :8000      │
│  dsa110-contimg-dashboard     → Vite preview         :3210      │
│  contimg-stream.service       → Streaming converter  (daemon)   │
│  contimg-docs.service         → MkDocs server        :8001      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT                               │
├─────────────────────────────────────────────────────────────────┤
│  npm run dev                  → Vite dev server      :3000      │
│  uvicorn (manual)             → FastAPI with reload  :8000      │
│  npm run storybook            → Component dev        :6006      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Port Assignments

| Port | Service              | Environment  |
| ---- | -------------------- | ------------ |
| 3000 | Frontend dev server  | Development  |
| 3210 | Dashboard production | Production   |
| 6006 | Storybook            | Development  |
| 8000 | API (FastAPI)        | Both         |
| 8001 | MkDocs               | Optional     |

---

## Development Workflow

### Frontend Development

```bash
cd /data/dsa110-contimg/frontend
npm run dev          # Start Vite dev server on :3000
```

Or use VS Code Task: **"Frontend: Dev Server"**

Features:
- Hot module reload
- Proxies `/api/*` → `localhost:8000`
- Source maps enabled

### Backend Development

The API service is usually already running via systemd. Check with:
```bash
sudo systemctl status contimg-api
```

To run manually with hot-reload:
```bash
conda activate casa6
cd /data/dsa110-contimg/backend/src
uvicorn dsa110_contimg.api.app:app --reload --host 0.0.0.0 --port 8000
```

Or use VS Code Task: **"Backend: Start API Server"** (auto-detects if systemd is running)

---

## Production Services

### Core Services

| Service File                      | Purpose                    | Canonical? |
| --------------------------------- | -------------------------- | ---------- |
| `contimg-api.service`             | FastAPI backend            | ✅ Yes     |
| `dsa110-contimg-dashboard.service`| Frontend (vite preview)    | ✅ Yes     |
| `contimg-stream.service`          | Real-time data ingest      | ✅ Yes     |
| `dsa110-contimg-api.service`      | *Legacy duplicate*         | ❌ Deprecated |

### Start/Stop Commands

```bash
# Start all core services
sudo systemctl start contimg-api dsa110-contimg-dashboard contimg-stream

# Enable on boot
sudo systemctl enable contimg-api dsa110-contimg-dashboard contimg-stream

# Check status
sudo systemctl status contimg-api dsa110-contimg-dashboard

# View logs
sudo journalctl -u contimg-api -f
```

### Service Dependencies

```
contimg-stream.service
    └── Requires: contimg-api.service (for status updates)

dsa110-contimg-dashboard.service
    └── Recommends: contimg-api.service (for API calls)
```

---

## VS Code Tasks

Available via `Terminal > Run Task` or `Ctrl+Shift+P > Tasks: Run Task`:

| Task                        | What it does                              |
| --------------------------- | ----------------------------------------- |
| 🔍 Preflight Check          | Validates environment (runs on folder open) |
| 🚀 Start All Services       | Runs preflight (placeholder for more)     |
| Frontend: Dev Server        | Starts Vite on :3000                      |
| Backend: Start API Server   | Starts uvicorn or confirms systemd running |
| Backend: Run Tests          | pytest in backend/                        |
| Docs: Serve MkDocs          | MkDocs dev server on :8001                |

---

## Troubleshooting

### "Port already in use"

```bash
# Find what's using a port
lsof -i :3000

# Kill process on port (use with caution)
kill $(lsof -t -i :3000)
```

### Frontend can't reach API

1. Check API is running: `curl http://localhost:8000/api/health`
2. Check Vite proxy config in `frontend/vite.config.ts`
3. Ensure you're accessing via `localhost:3000`, not direct IP

### Systemd service won't start

```bash
# Check logs
sudo journalctl -u contimg-api -n 50 --no-pager

# Validate service file
sudo systemd-analyze verify /etc/systemd/system/contimg-api.service

# Reload after changes
sudo systemctl daemon-reload
```

---

## File Locations

| What                    | Where                                          |
| ----------------------- | ---------------------------------------------- |
| Service files (source)  | `/data/dsa110-contimg/ops/systemd/`            |
| Service files (active)  | `/etc/systemd/system/`                         |
| Environment config      | `/data/dsa110-contimg/ops/systemd/contimg.env` |
| Service logs            | `/data/dsa110-contimg/state/logs/`             |
| Frontend source         | `/data/dsa110-contimg/frontend/`               |
| Backend source          | `/data/dsa110-contimg/backend/src/`            |
