# Running the Dashboard Persistently on HPC

When running the dashboard on a remote HPC server, you need to ensure it
continues running after you disconnect your SSH session. This guide covers
several methods to achieve this.

## Quick Start

### Prerequisites

**Important:** If you need to rebuild the frontend (e.g., after code changes),
use `make frontend-build` which will use casa6's Node.js v22.6.0 (or Docker as
fallback):

```bash
# Build frontend using casa6 Node.js (preferred) or Docker (fallback)
make frontend-build
```

### Option 1: Using tmux (Recommended)

```bash
# Start the dashboard in a tmux session
bash /data/dsa110-contimg/scripts/start-dashboard-tmux.sh

# Attach to the session
tmux attach -t dsa110-dashboard

# Detach (keeps running): Press Ctrl+B, then D
```

### Option 2: Using screen

```bash
# Start the dashboard in a screen session
bash /data/dsa110-contimg/scripts/start-dashboard-screen.sh

# Attach to the session
screen -r dsa110-dashboard

# Detach (keeps running): Press Ctrl+A, then D
```

### Option 3: Using systemd (Requires sudo)

If you have sudo access, you can install the dashboard as a system service:

```bash
# Install the service
sudo cp /data/dsa110-contimg/ops/systemd/contimg-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable contimg-api.service
sudo systemctl start contimg-api.service

# Check status
sudo systemctl status contimg-api.service

# View logs
sudo journalctl -u contimg-api.service -f
```

## Detailed Methods

### Method 1: tmux

tmux is a terminal multiplexer that allows you to create persistent sessions.

#### Starting the Dashboard

```bash
cd /data/dsa110-contimg
source ops/systemd/contimg.env  # Optional: load environment variables

# Start in a new tmux session
tmux new-session -d -s dsa110-dashboard \
    "uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000"
```

Or use the helper script:

```bash
bash scripts/start-dashboard-tmux.sh
```

#### Managing the Session

```bash
# List all tmux sessions
tmux ls

# Attach to the session
tmux attach -t dsa110-dashboard

# Detach from session (keeps running)
# Press: Ctrl+B, then D

# Kill the session
tmux kill-session -t dsa110-dashboard

# Send commands to the session without attaching
tmux send-keys -t dsa110-dashboard "some command" Enter
```

#### Useful tmux Commands

- `Ctrl+B` then `D` - Detach from session
- `Ctrl+B` then `C` - Create new window
- `Ctrl+B` then `N` - Next window
- `Ctrl+B` then `P` - Previous window
- `Ctrl+B` then `[` - Enter scroll mode (use arrow keys, press `q` to exit)

### Method 2: screen

screen is another terminal multiplexer, similar to tmux.

#### Starting the Dashboard

```bash
cd /data/dsa110-contimg
source ops/systemd/contimg.env  # Optional: load environment variables

# Start in a new screen session
screen -dmS dsa110-dashboard \
    bash -c "cd /data/dsa110-contimg && uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000"
```

Or use the helper script:

```bash
bash scripts/start-dashboard-screen.sh
```

#### Managing the Session

```bash
# List all screen sessions
screen -ls

# Attach to the session
screen -r dsa110-dashboard

# Detach from session (keeps running)
# Press: Ctrl+A, then D

# Kill the session
screen -S dsa110-dashboard -X quit
```

#### Useful screen Commands

- `Ctrl+A` then `D` - Detach from session
- `Ctrl+A` then `C` - Create new window
- `Ctrl+A` then `N` - Next window
- `Ctrl+A` then `P` - Previous window
- `Ctrl+A` then `[` - Enter scroll mode (use arrow keys, press `q` to exit)

### Method 3: nohup (Simple but less flexible)

nohup runs a command immune to hangups, but you lose interactive control:

```bash
cd /data/dsa110-contimg
source ops/systemd/contimg.env

# Start with nohup
nohup uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 \
    > state/logs/dashboard.out 2>&1 &

# Note the process ID (PID)
echo $!

# To stop later, kill the process
kill <PID>
```

### Method 4: systemd Service (Production)

For production deployments with sudo access, use systemd:

#### Installation

```bash
# Copy service file
sudo cp /data/dsa110-contimg/ops/systemd/contimg-api.service /etc/systemd/system/

# Edit if needed to use correct Python path
sudo nano /etc/systemd/system/contimg-api.service
# Update ExecStart to use: /opt/miniforge/envs/casa6/bin/uvicorn

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable contimg-api.service

# Start service
sudo systemctl start contimg-api.service
```

#### Management

```bash
# Check status
sudo systemctl status contimg-api.service

# View logs
sudo journalctl -u contimg-api.service -f

# Stop
sudo systemctl stop contimg-api.service

# Restart
sudo systemctl restart contimg-api.service

# Disable auto-start
sudo systemctl disable contimg-api.service
```

## SSH Port Forwarding

To access the dashboard from your local machine, set up SSH port forwarding:

```bash
# Forward local port 8000 to remote port 8000
ssh -L 8000:localhost:8000 user@hpc-server

# Or keep the connection alive with autossh
autossh -M 20000 -L 8000:localhost:8000 user@hpc-server
```

Then access the dashboard at `http://localhost:8000` in your browser.

### Persistent SSH Tunnel

To maintain the SSH tunnel even if it disconnects:

```bash
# Using autossh (install with: sudo apt install autossh)
autossh -M 20000 -N -L 8000:localhost:8000 user@hpc-server

# Or use tmux/screen to keep SSH tunnel alive
tmux new-session -d -s ssh-tunnel \
    "ssh -N -L 8000:localhost:8000 user@hpc-server"
```

## Troubleshooting

### Dashboard Not Accessible

1. **Check if the service is running:**

   ```bash
   # For tmux/screen
   tmux ls
   screen -ls

   # For systemd
   sudo systemctl status contimg-api.service

   # Check process
   ps aux | grep uvicorn
   ```

2. **Check port binding:**

   ```bash
   netstat -tlnp | grep 8000
   # or
   ss -tlnp | grep 8000
   ```

3. **Check firewall rules:**

   ```bash
   # On the HPC server
   sudo ufw status
   # May need to allow port 8000
   sudo ufw allow 8000/tcp
   ```

4. **Check logs:**

   ```bash
   # tmux/screen logs
   tail -f /data/dsa110-contimg/state/logs/dashboard*.log

   # systemd logs
   sudo journalctl -u contimg-api.service -n 50
   ```

### Service Keeps Dying

1. **Check environment variables:**

   ```bash
   source /data/dsa110-contimg/ops/systemd/contimg.env
   env | grep CONTIMG
   ```

2. **Check Python path:**

   ```bash
   which uvicorn
   # Should be: /opt/miniforge/envs/casa6/bin/uvicorn
   ```

3. **Test manually:**
   ```bash
   cd /data/dsa110-contimg
   export PYTHONPATH=/data/dsa110-contimg/src
   /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
   ```

### Cannot Access from Local Machine

1. **Verify SSH tunnel:**

   ```bash
   # On local machine
   netstat -an | grep 8000
   ```

2. **Check HPC server firewall:**

   ```bash
   # On HPC server
   sudo iptables -L -n | grep 8000
   ```

3. **Try accessing from HPC server itself:**
   ```bash
   curl http://localhost:8000/api/status
   ```

## Best Practices

1. **Use tmux or screen** for development/testing - they provide the best
   balance of persistence and interactivity.

2. **Use systemd** for production - it provides automatic restart, logging, and
   boot-time startup.

3. **Set up SSH port forwarding** to access the dashboard securely from your
   local machine.

4. **Monitor logs regularly** to catch issues early.

5. **Use environment files** (`contimg.env`) to manage configuration
   consistently.

6. **Document your setup** - note which method you're using and any
   customizations.

## Quick Reference

| Method  | Best For    | Requires Sudo | Auto-restart | Logs       |
| ------- | ----------- | ------------- | ------------ | ---------- |
| tmux    | Development | No            | No           | Manual     |
| screen  | Development | No            | No           | Manual     |
| nohup   | Quick tests | No            | No           | File-based |
| systemd | Production  | Yes           | Yes          | journalctl |
