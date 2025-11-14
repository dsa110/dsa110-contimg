# Fixing Vite Process Respawning

**Date:** 2025-01-27  
**Issue:** Vite processes keep respawning after being killed

---

## Problem

Vite processes on ports 5173, 5174, 5175, 5176 keep respawning even after:

- Killing Vite processes directly
- Killing parent npm processes
- Using `pkill -f "npm run dev"`

**Root Cause:**

- Processes are being killed in the wrong order
- Parent processes (wrappers, scripts) aren't being identified
- Process groups aren't being handled
- Some processes require sudo to kill

---

## Solution

### New Script: `kill-vite-thoroughly.sh`

**What it does:**

1. Finds all Vite processes and their ports
2. Identifies parent npm processes
3. Finds process groups and sessions
4. Identifies wrapper scripts that might restart processes
5. Kills in correct order: Vite → npm → wrappers → process groups
6. Force kills any remaining processes
7. Verifies cleanup

**Usage:**

```bash
# Run thorough cleanup
./scripts/kill-vite-thoroughly.sh

# If some processes require sudo
sudo ./scripts/kill-vite-thoroughly.sh
```

### Integration

The script is now integrated into:

- `prevent-duplicate-services.sh` - Uses thorough cleanup automatically
- `cleanup-duplicate-services.sh` - Uses thorough cleanup when available

---

## Process Hierarchy

Understanding the process tree is critical:

```
Wrapper Script (bash/sh)
  └─ npm run dev
      └─ sh -c vite
          └─ node vite (port 5173)
```

**Killing order:**

1. Kill Vite processes (children)
2. Kill npm processes (parents)
3. Kill wrapper scripts (grandparents)
4. Kill process groups (if needed)
5. Force kill any remaining

---

## Why Processes Respawning

### Common Causes

1. **Wrapper Scripts**
   - Scripts that monitor and restart processes
   - Background jobs that respawn on failure
   - Auto-restart mechanisms

2. **Process Groups**
   - Killing a child doesn't kill the group
   - Group leader keeps processes alive
   - Need to kill by process group ID

3. **Session Leaders**
   - Processes in same session respawn each other
   - Need to kill by session ID

4. **Permission Issues**
   - Some processes owned by root
   - Need sudo to kill
   - Permission denied errors

---

## Manual Cleanup Steps

If the script doesn't work, try manual steps:

### Step 1: Find All Processes

```bash
# Find Vite processes
pgrep -af vite

# Find npm processes
pgrep -af "npm run dev"

# Find processes on ports
lsof -i :5173-5179
```

### Step 2: Check Process Hierarchy

```bash
# For each PID, check parent
ps -p <PID> -o pid,ppid,pgid,sid,cmd

# Check process tree
pstree -p <PID>
```

### Step 3: Kill in Order

```bash
# 1. Kill Vite processes
pkill -f vite

# 2. Kill npm processes
pkill -f "npm run dev"

# 3. Kill by process group (if needed)
kill -TERM -<PGID>

# 4. Force kill remaining
pkill -9 -f vite
pkill -9 -f "npm run dev"
```

### Step 4: With Sudo (if needed)

```bash
sudo pkill -f vite
sudo pkill -f "npm run dev"
sudo kill -TERM -<PGID>
```

---

## Prevention

The automatic prevention system now:

1. Uses thorough cleanup script
2. Kills processes in correct order
3. Handles process groups
4. Uses sudo when needed
5. Verifies cleanup

**No manual steps needed** - prevention is automatic!

---

## Troubleshooting

### Processes Still Respawning

1. **Check for systemd services:**

   ```bash
   systemctl list-units --type=service | grep -i vite
   ```

2. **Check for Docker containers:**

   ```bash
   docker ps | grep -i vite
   ```

3. **Check for process managers:**

   ```bash
   ps aux | grep -E "supervisor|pm2|forever|nodemon"
   ```

4. **Check for cron jobs:**

   ```bash
   crontab -l
   ```

5. **Check for init scripts:**
   ```bash
   ls -la /etc/init.d/ | grep -i vite
   ```

### Run Thorough Cleanup

```bash
# Run with verbose output
bash -x ./scripts/kill-vite-thoroughly.sh

# Check what it finds
./scripts/kill-vite-thoroughly.sh 2>&1 | tee cleanup.log
```

---

## Status

✅ **Thorough Cleanup Script** - Implemented  
✅ **Process Group Handling** - Implemented  
✅ **Wrapper Script Detection** - Implemented  
✅ **Sudo Support** - Implemented  
✅ **Integration** - Complete

---

**See Also:**

- `scripts/kill-vite-thoroughly.sh` - Thorough cleanup script
- `scripts/prevent-duplicate-services.sh` - Automatic prevention
- `scripts/cleanup-duplicate-services.sh` - Manual cleanup
