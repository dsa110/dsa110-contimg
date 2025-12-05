# Systemd Services for DSA-110

**Date:** 2025-11-17  
**Purpose:** Manage frontend and backend services with systemd

---

## Services Available

1. **vite-dev.service** - Frontend development server
2. **dsa110-backend.service** - Backend API and Redis (via Docker Compose)
3. **container-health-monitor.service** - Automated container health monitoring

---

## Backend Service (Recommended)

### Installation

```bash
# Copy service file
sudo cp /data/dsa110-contimg/scripts/dsa110-backend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable (start on boot)
sudo systemctl enable dsa110-backend

# Start now
sudo systemctl start dsa110-backend
```

### Usage

```bash
# Check status
sudo systemctl status dsa110-backend

# View logs
sudo journalctl -u dsa110-backend -f

# Restart
sudo systemctl restart dsa110-backend

# Stop
sudo systemctl stop dsa110-backend

# Disable auto-start
sudo systemctl disable dsa110-backend
```

---

## Frontend Service (Already Installed)

```bash
# Check status
sudo systemctl status vite-dev

# View logs
sudo journalctl -u vite-dev -f

# Restart
sudo systemctl restart vite-dev
```

---

## Health Monitor Service (Optional but Recommended)

Auto-restarts unhealthy containers:

```bash
# Copy service file
sudo cp /data/dsa110-contimg/scripts/container-health-monitor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable container-health-monitor
sudo systemctl start container-health-monitor

# Check status
sudo systemctl status container-health-monitor

# View logs
sudo journalctl -u container-health-monitor -f
```

---

## Benefits of Systemd Services

### For Backend

- **Automatic startup** on system boot
- **Dependency management** - Waits for Docker to be ready
- **Centralized logging** via journalctl
- **Easy management** - Single command to start/stop entire stack
- **Restart on failure** - Automatic recovery

### For Frontend

- **Independent from Docker** - Faster development iteration
- **Auto-restart** on crashes
- **Proper daemon** - Runs in background cleanly

### For Health Monitor

- **Proactive monitoring** - Catches issues early
- **Auto-restart unhealthy containers**
- **Continuous operation**

---

## Service Dependencies

```
System Boot
    :arrow_down:
docker.service (starts automatically)
    :arrow_down:
dsa110-backend.service (our backend)
    :arrow_down:
vite-dev.service (our frontend, depends on backend being up)
    :arrow_down:
container-health-monitor.service (monitors all containers)
```

---

## Verification After Installation

```bash
# Check all DSA-110 services
systemctl list-units "dsa110-*" "vite-*" "container-health-*"

# Check if enabled for boot
systemctl is-enabled dsa110-backend vite-dev

# View all logs together
journalctl -u dsa110-backend -u vite-dev -f
```

---

## Troubleshooting

### Backend service fails to start

```bash
# Check Docker is running
systemctl status docker

# Check logs
sudo journalctl -u dsa110-backend -n 50

# Manually test docker compose
cd /data/dsa110-contimg && docker compose up -d api redis
```

### Frontend can't connect to backend

```bash
# Ensure backend started first
systemctl status dsa110-backend

# Check containers are running
docker ps | grep dsa110

# Check API is responding
curl http://localhost:8000/api/status
```

### Services not starting on boot

```bash
# Check if enabled
systemctl is-enabled dsa110-backend
systemctl is-enabled vite-dev

# Enable them
sudo systemctl enable dsa110-backend
sudo systemctl enable vite-dev
```

---

## Recommendation

**Install all three services:**

1. **dsa110-backend** - Essential for production-like environment
2. **vite-dev** - Already installed, keep it
3. **container-health-monitor** - Highly recommended for reliability

This gives you a complete, self-healing system that:

- Starts automatically on boot
- Monitors itself continuously
- Restarts failed components automatically
- Provides centralized logging

---

**Installation Commands (Copy-Paste):**

```bash
# Backend service
sudo cp /data/dsa110-contimg/scripts/dsa110-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dsa110-backend
sudo systemctl start dsa110-backend

# Health monitor service
sudo cp /data/dsa110-contimg/scripts/container-health-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable container-health-monitor
sudo systemctl start container-health-monitor

# Verify all services
systemctl status dsa110-backend vite-dev container-health-monitor
```

---

**Last Updated:** 2025-11-17  
**Maintained By:** DevOps Team
