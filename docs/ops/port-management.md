# Port Management for DSA-110 Services

## Reserved Ports

- **8000**: DSA-110 API (FastAPI backend)
- **3000**: DSA-110 Dashboard (React frontend)
- **8010**: Alternative API port (if needed)
- **8080**: Proxy services (existing)

## Quick Start: Service Management Script

The easiest way to manage services and ensure ports are reserved:

```bash
# Start both services (kills conflicting processes automatically)
/data/dsa110-contimg/scripts/manage-services.sh start all

# Check status
/data/dsa110-contimg/scripts/manage-services.sh status

# Stop all services
/data/dsa110-contimg/scripts/manage-services.sh stop all

# View logs
/data/dsa110-contimg/scripts/manage-services.sh logs api
/data/dsa110-contimg/scripts/manage-services.sh logs dashboard
```

**Features**:
- ✓ Automatically kills conflicting processes
- ✓ Manages PID files
- ✓ Logs to `/var/log/dsa110/`
- ✓ Color-coded status output
- ✓ Background process management

## Option Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Service Script** | Simple, no sudo needed, immediate | Manual start after reboot | Development |
| **Systemd** | Auto-start on boot, robust, logging | Requires sudo, more setup | Production |
| **Docker Compose** | Isolated, portable, easy scaling | Requires Docker, overhead | Containerized deployments |

## Method 1: Service Management Script (Recommended for Now)

### Usage

```bash
# Start API only
./scripts/manage-services.sh start api

# Start dashboard only
./scripts/manage-services.sh start dashboard

# Start both
./scripts/manage-services.sh start all

# Restart API
./scripts/manage-services.sh restart api

# Check what's running
./scripts/manage-services.sh status

# View live logs
./scripts/manage-services.sh logs api 100
```

### Add to PATH (Optional)

```bash
# Add alias to your ~/.bashrc
echo 'alias dsa110-services="/data/dsa110-contimg/scripts/manage-services.sh"' >> ~/.bashrc
source ~/.bashrc

# Now you can use:
dsa110-services start all
dsa110-services status
```

## Method 2: Systemd Services (Production)

### Installation

```bash
# Follow instructions in:
cat /data/dsa110-contimg/systemd/INSTALL.md

# Quick install:
sudo cp /data/dsa110-contimg/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dsa110-api.service
sudo systemctl start dsa110-api.service
```

### Usage

```bash
# Start services
sudo systemctl start dsa110-api.service
sudo systemctl start dsa110-dashboard.service

# Check status
sudo systemctl status dsa110-api.service

# View logs
sudo journalctl -u dsa110-api.service -f

# Enable auto-start on boot
sudo systemctl enable dsa110-api.service
```

**Benefits**:
- Services start automatically on boot
- Automatic restart on crash
- System-level logging
- Proper process management

## Method 3: Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop all
docker-compose down
```

## Manual Port Management

### Check Port Usage

```bash
# See what's using port 8000
sudo lsof -i :8000
# or
sudo netstat -tlnp | grep :8000

# See all DSA-110 related processes
ps aux | grep -E "uvicorn|dsa110"
```

### Kill Process on Port

```bash
# Method 1: By port
sudo fuser -k 8000/tcp

# Method 2: By PID
sudo kill <PID>

# Method 3: Force kill
sudo kill -9 <PID>
```

### Prevent Port Conflicts

Add to your `~/.bashrc`:

```bash
# Function to check if DSA-110 ports are free
check_dsa110_ports() {
    local ports=(8000 3000)
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "⚠️  Port $port is in use:"
            lsof -i :$port
        else
            echo "✓ Port $port is free"
        fi
    done
}

# Alias
alias dsa110-check-ports='check_dsa110_ports'
```

## Firewall Configuration (If Needed)

```bash
# Allow ports through firewall
sudo ufw allow 8000/tcp comment "DSA-110 API"
sudo ufw allow 3000/tcp comment "DSA-110 Dashboard"

# Check firewall status
sudo ufw status
```

## Troubleshooting

### "Address already in use"

```bash
# Find what's using the port
sudo lsof -i :8000

# Kill it
sudo fuser -k 8000/tcp

# Or use the service script
./scripts/manage-services.sh restart api
```

### Service won't start

```bash
# Check logs
tail -100 /var/log/dsa110/api.log

# Check if conda environment exists
conda env list | grep casa6

# Test manually
cd /data/dsa110-contimg
conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src
uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000
```

### Multiple instances running

```bash
# Find all uvicorn processes
ps aux | grep uvicorn

# Kill all DSA-110 related processes
pkill -f "dsa110_contimg.api"

# Or use service script
./scripts/manage-services.sh stop all
```

## Best Practices

1. **Development**: Use the service management script
   ```bash
   ./scripts/manage-services.sh start all
   ```

2. **Production**: Use systemd services
   ```bash
   sudo systemctl enable dsa110-api.service
   sudo systemctl start dsa110-api.service
   ```

3. **Always check status before starting**:
   ```bash
   ./scripts/manage-services.sh status
   ```

4. **Use logs to debug**:
   ```bash
   ./scripts/manage-services.sh logs api
   ```

5. **Clean shutdown**:
   ```bash
   ./scripts/manage-services.sh stop all
   ```

## Monitoring

### Create monitoring script

```bash
# Add to crontab for periodic checks
*/5 * * * * /data/dsa110-contimg/scripts/manage-services.sh status > /tmp/dsa110-status.txt
```

### Simple health check

```bash
# Check if services are responding
curl -f http://localhost:8000/api/status || echo "API down!"
curl -f http://localhost:3000 || echo "Dashboard down!"
```

---

**Quick Reference**:
- Start: `./scripts/manage-services.sh start all`
- Stop: `./scripts/manage-services.sh stop all`
- Status: `./scripts/manage-services.sh status`
- Logs: `./scripts/manage-services.sh logs api`

