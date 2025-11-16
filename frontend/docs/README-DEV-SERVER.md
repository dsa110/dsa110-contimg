# Running the Dev Server Persistently

The dev server can be run in several ways that survive terminal closure:

## Option 1: Screen (Recommended for simplicity)

```bash
cd /data/dsa110-contimg/frontend
./scripts/start-dev.sh screen
```

**To attach and see output:**
```bash
screen -r frontend-dev
```

**To detach (keep running):**
Press `Ctrl+A` then `D`

**To stop:**
```bash
./scripts/stop-dev.sh screen
# OR
screen -X -S frontend-dev quit
```

## Option 2: PM2 (Recommended for production-like management)

PM2 provides auto-restart, logging, and process management:

```bash
cd /data/dsa110-contimg/frontend
./scripts/start-dev.sh pm2
```

**View logs:**
```bash
pm2 logs frontend-dev
```

**Restart:**
```bash
pm2 restart frontend-dev
```

**Stop:**
```bash
./scripts/stop-dev.sh pm2
# OR
pm2 stop frontend-dev
pm2 delete frontend-dev
```

**View status:**
```bash
pm2 status
```

## Option 3: Tmux

```bash
cd /data/dsa110-contimg/frontend
./scripts/start-dev.sh tmux
```

**To attach:**
```bash
tmux attach -t frontend-dev
```

**To detach:**
Press `Ctrl+B` then `D`

**To stop:**
```bash
./scripts/stop-dev.sh tmux
```

## Option 4: Nohup (Simple background process)

```bash
cd /data/dsa110-contimg/frontend
./scripts/start-dev.sh nohup
```

**View logs:**
```bash
tail -f dev-server.log
```

**Stop:**
```bash
./scripts/stop-dev.sh nohup
# OR find and kill the process
pkill -f vite
```

## Quick Reference

| Method | Pros | Cons |
|--------|------|------|
| **Screen** | Simple, built-in, easy to attach/detach | Basic logging |
| **PM2** | Auto-restart, great logging, process management | Requires npm install |
| **Tmux** | Powerful, built-in, multiple windows | Slightly more complex |
| **Nohup** | Simplest, no dependencies | Harder to manage, basic logging |

## Recommendation

- **For development:** Use `screen` - it's simple and built-in
- **For production-like testing:** Use `PM2` - better process management

## Checking if server is running

```bash
# Check if port 5174 is in use
lsof -i :5174

# Or check processes
ps aux | grep vite
```

