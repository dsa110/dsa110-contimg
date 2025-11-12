# Remote Access Tools Guide

This guide documents the available tools for accessing and working with the lxd110h17 HPC server.

## Overview

We have three main ways to access the server:

1. **SSH** - Command-line access (primary method)
2. **Chrome Remote Desktop** - Full GUI desktop access
3. **Cursor Browser Tool** - Native Chrome browser for web testing/debugging

## 1. SSH Access (Command-Line)

### Basic Connection

```bash
ssh h17
```

### SSH Configuration

The SSH config is set up in `~/.ssh/config` on your local Mac with:
- Multi-hop connection: `ovro` → `dsa110maas` → `h23` → `h17`
- Compression enabled for better performance
- X11 forwarding **disabled** (to allow Cursor Browser tool to use native Chrome)

### Persistent Sessions

Use `tmux` or `screen` to keep sessions running after disconnecting:

**tmux:**
```bash
# Create new session
tmux new -s sessionname

# Attach to session
tmux attach -t sessionname

# Detach (keeps running): Ctrl+B then D
```

**screen:**
```bash
# Create new session
screen -S sessionname

# Attach to session
screen -r sessionname

# Detach (keeps running): Ctrl+A then D
```

### Port Forwarding (for Web Services)

To access web services running on the server:

```bash
ssh -L 8000:localhost:8000 -L 5173:localhost:5173 h17
```

Then access:
- Backend API: `http://localhost:8000`
- Frontend dev server: `http://localhost:5173`

## 2. Chrome Remote Desktop (Full GUI Access)

### Setup

Chrome Remote Desktop is already configured on lxd110h17. To access:

1. Go to `remotedesktop.google.com` on your Mac
2. Sign in with your Google account (`jakobtfaber@gmail.com`)
3. Find "lxd110h17" in your computers list
4. Click to connect and enter your PIN

### Starting Chrome Remote Desktop

If Chrome Remote Desktop is stopped, start it with:

```bash
/opt/google/chrome-remote-desktop/chrome-remote-desktop --start --new-session
```

**Note:** Use `--start --new-session` to bypass pkexec/systemctl authentication requirements.

### Running Persistently

Chrome Remote Desktop runs as a background service and persists across SSH disconnections. To start it in a tmux/screen session for monitoring:

```bash
tmux new -s crd
/opt/google/chrome-remote-desktop/chrome-remote-desktop --start --new-session &
# Detach: Ctrl+B then D
```

### Checking Status

```bash
# Check if running
/opt/google/chrome-remote-desktop/chrome-remote-desktop --get-status

# Check processes
ps aux | grep chrome-remote-desktop-host | grep -v grep
```

### Stopping

```bash
/opt/google/chrome-remote-desktop/chrome-remote-desktop --stop
```

## 3. Cursor Browser Tool (Native Chrome)

### What It Is

Cursor's Browser tool allows you to interact with web pages directly from Cursor. When X11 forwarding is **disabled** in SSH, it uses native Chrome on your Mac (fast, native UI).

### Requirements

- X11 forwarding **must be disabled** in SSH config
- Connect without `-XY` flags: `ssh h17` (not `ssh -XY h17`)
- DISPLAY should be unset: `echo $DISPLAY` should show nothing

### Using the Browser Tool

The Browser tool is available in Cursor's MCP tools. It will:
- Open Chrome on your Mac (not XQuartz/xterm)
- Provide fast, native macOS UI
- Allow web testing/debugging directly from Cursor

### Troubleshooting

**If Browser tool uses XQuartz/xterm instead of Chrome:**
1. Check SSH config: Ensure `ForwardX11 yes` is commented out for `h17`
2. Reconnect SSH without `-XY` flags
3. Verify: `echo $DISPLAY` should be empty
4. Restart Cursor if needed

**If DISPLAY keeps getting set:**
- Check all jump hosts in SSH config (`ovro`, `dsa110maas`, `h23`) for `ForwardX11 yes`
- Comment out X11 forwarding in all relevant hosts
- Reconnect SSH

## When to Use Each Tool

| Tool | Use Case | Performance |
|------|----------|-------------|
| **SSH** | Command-line work, code editing, running scripts | Fast |
| **Chrome Remote Desktop** | Full GUI desktop, running GUI applications, visual debugging | Good (through Google servers) |
| **Cursor Browser Tool** | Web testing, debugging web apps, checking web pages | Fastest (native Chrome) |

## Quick Reference

### SSH Commands
```bash
ssh h17                                    # Connect
tmux new -s name                           # Create persistent session
tmux attach -t name                       # Attach to session
ssh -L 8000:localhost:8000 h17           # Port forwarding
```

### Chrome Remote Desktop
```bash
# Start
/opt/google/chrome-remote-desktop/chrome-remote-desktop --start --new-session

# Status
/opt/google/chrome-remote-desktop/chrome-remote-desktop --get-status

# Stop
/opt/google/chrome-remote-desktop/chrome-remote-desktop --stop
```

### Verification Commands
```bash
# Check DISPLAY (should be empty for Cursor Browser)
echo $DISPLAY

# Check Chrome Remote Desktop
ps aux | grep chrome-remote-desktop-host | grep -v grep

# Check SSH X11 forwarding
netstat -an | grep 6010 || ss -an | grep 6010
```

## Troubleshooting

### Chrome Remote Desktop Shows as Offline

1. Check if process is running:
   ```bash
   ps aux | grep chrome-remote-desktop-host | grep -v grep
   ```

2. If not running, start it:
   ```bash
   /opt/google/chrome-remote-desktop/chrome-remote-desktop --start --new-session
   ```

3. Check status:
   ```bash
   /opt/google/chrome-remote-desktop/chrome-remote-desktop --get-status
   ```

### Cursor Browser Tool Uses XQuartz Instead of Chrome

1. Verify DISPLAY is unset:
   ```bash
   echo $DISPLAY  # Should be empty
   ```

2. Check SSH config for `ForwardX11 yes` and comment it out

3. Reconnect SSH without `-XY` flags

4. Restart Cursor

### SSH Connection Issues

- Check jump host connectivity: `ssh h23` should work
- Verify SSH config: `cat ~/.ssh/config | grep -A 10 "^Host h17"`
- Test direct connection if possible

## Configuration Files

### SSH Config Location
`~/.ssh/config` on your local Mac

### Chrome Remote Desktop Config
`~/.config/chrome-remote-desktop/host#*.json` on lxd110h17

## Related Documentation

- [Persistent Dashboard Setup](persistent-dashboard.md) - Running services persistently
- [Development Setup](../development/DEVELOPMENT_SETUP.md) - Development environment setup

