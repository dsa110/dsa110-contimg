# API Server Configuration

## Overview

The DSA-110 pipeline API server runs using `uvicorn` and can be configured for
auto-reload during development or stable operation in production.

## Auto-Reload Behavior

### Default Configuration

The API server **enables auto-reload by default** for development convenience.
When enabled, the server automatically restarts when Python source files are
modified.

### How It Works

Auto-reload is controlled by the `UVICORN_RELOAD` environment variable:

- **`UVICORN_RELOAD=1`** (default): Enables auto-reload
  - Server watches for changes to `.py` files in `src/dsa110_contimg/`
  - Automatically restarts when files are modified
  - Useful for active development

- **`UVICORN_RELOAD=0`**: Disables auto-reload
  - Server runs in stable mode without file watching
  - Recommended for production deployments
  - Better performance (no file watching overhead)

### Configuration Location

The auto-reload setting is configured in `scripts/manage-services.sh`:

```bash
UVICORN_RELOAD="${UVICORN_RELOAD:-1}"  # Enable auto-reload by default for development
```

### Usage Examples

**Start API with auto-reload (default):**

```bash
./scripts/manage-services.sh start api
# or explicitly
UVICORN_RELOAD=1 ./scripts/manage-services.sh start api
```

**Start API without auto-reload (production mode):**

```bash
UVICORN_RELOAD=0 ./scripts/manage-services.sh start api
```

**Restart API with different reload setting:**

```bash
./scripts/manage-services.sh stop api
UVICORN_RELOAD=0 ./scripts/manage-services.sh start api
```

### When Auto-Reload Triggers

The server will automatically reload when:

- Any Python file (`.py`) in `src/dsa110_contimg/` is modified
- The file is saved (file system change detected)
- The change is detected by uvicorn's file watcher

### Performance Considerations

- **Development**: Auto-reload is convenient and recommended
- **Production**: Disable auto-reload (`UVICORN_RELOAD=0`) for:
  - Better performance (no file watching overhead)
  - More stable operation
  - Reduced resource usage

### Troubleshooting

**Auto-reload not working:**

- Check that `UVICORN_RELOAD=1` is set
- Verify file permissions (uvicorn needs read access to watch files)
- Check logs for file watching errors

**Server restarting unexpectedly:**

- Check if auto-reload is enabled (`UVICORN_RELOAD=1`)
- Verify no automated processes are modifying Python files
- Consider disabling auto-reload if not needed

### Related Configuration

- API Port: `CONTIMG_API_PORT` (default: 8000)
- Dashboard Port: `CONTIMG_DASHBOARD_PORT` (default: 3210)
- Log Directory: `/var/log/dsa110`
- PID Directory: `/var/run/dsa110`

See `scripts/manage-services.sh` for full service management options.

## Integration with Service Management

The API server is managed through `scripts/manage-services.sh`, which handles:

- Starting/stopping the API server
- Port management
- Process monitoring
- Log file management

For complete service management documentation, see the script help:

```bash
./scripts/manage-services.sh --help
```

## Running Without SSH Connection

The API server can run independently of your SSH session using several methods:

### Method 1: Service Management Script (Current Implementation)

The `manage-services.sh` script uses `nohup` to run processes in the background,
allowing them to continue after SSH disconnection:

```bash
# Start API - will continue running after SSH disconnect
./scripts/manage-services.sh start api

# Check status
./scripts/manage-services.sh status api

# Stop API
./scripts/manage-services.sh stop api
```

**How it works:**

- Uses `nohup` to prevent SIGHUP signals from terminating the process
- Runs in background with output redirected to log files
- Process continues even when SSH session ends

### Method 2: Systemd Service (Recommended for Production)

For production deployments, use systemd to manage the service:

```bash
# Install systemd service (if configured)
sudo systemctl enable dsa110-api
sudo systemctl start dsa110-api

# Check status
sudo systemctl status dsa110-api

# View logs
sudo journalctl -u dsa110-api -f
```

**Advantages:**

- Automatic restart on failure
- Proper service management
- Logging via journald
- Starts on system boot

### Method 3: Screen/Tmux (Development)

For interactive development sessions:

```bash
# Using screen
screen -S api
./scripts/manage-services.sh start api
# Press Ctrl+A then D to detach
# Reattach with: screen -r api

# Using tmux
tmux new -s api
./scripts/manage-services.sh start api
# Press Ctrl+B then D to detach
# Reattach with: tmux attach -t api
```

### Method 4: Disown (Quick Detach)

If you've already started a process:

```bash
# Start process
./scripts/manage-services.sh start api

# Find process ID
ps aux | grep uvicorn

# Disown the process (if started manually)
disown -h %1  # or specific PID
```

### Verifying Process Persistence

After disconnecting SSH, verify the service is still running:

```bash
# Check if API is responding
curl http://localhost:8000/api/status

# Check process
ps aux | grep uvicorn

# Check logs
tail -f /var/log/dsa110/api.log
```

### Current Implementation Details

The `manage-services.sh` script handles process persistence by:

1. Using `nohup` to ignore hangup signals
2. Redirecting output to log files (`/var/log/dsa110/`)
3. Running processes in background
4. Storing PID files for process management (`/var/run/dsa110/`)

**Note:** The current implementation should maintain connections after SSH
disconnect, but for production use, systemd services are recommended for better
reliability and automatic restarts.

### Systemd Service Setup

A systemd service file is available at `ops/systemd/contimg-api.service`. To use
it:

```bash
# Copy service file to systemd directory
sudo cp ops/systemd/contimg-api.service /etc/systemd/system/

# Copy environment file
sudo cp ops/systemd/contimg.env /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (starts on boot)
sudo systemctl enable contimg-api

# Start service
sudo systemctl start contimg-api

# Check status
sudo systemctl status contimg-api

# View logs
sudo journalctl -u contimg-api -f
```

**Systemd Service Features:**

- Automatic restart on failure (`Restart=always`)
- Starts on system boot (`WantedBy=multi-user.target`)
- Proper logging via journald
- Runs independently of user sessions
- Survives SSH disconnection and system reboots

**Note:** The systemd service uses a different command structure than
`manage-services.sh`. Ensure the service file matches your deployment needs.
