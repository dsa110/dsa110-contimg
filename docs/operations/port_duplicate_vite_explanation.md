# Why Duplicate Vite Instances Keep Appearing

**Date:** 2025-01-27  
**Issue:** Vite instances keep respawning on port 5175 after being killed

---

## Root Cause

The duplicate Vite instances are being spawned by **multiple `npm run dev`
processes** running in the background. When you kill a Vite process, the parent
`npm` process automatically restarts it.

### Process Hierarchy

```
PID 725820: bash script running "npm run dev" (background)
  └─ PID 725821: npm run dev
      └─ PID 726006: sh -c -- vite
          └─ PID 726008: node vite (port 5173) ✓ Primary

PID 3938705: npm run dev (another instance)
  └─ PID 3938728: sh -c vite
      └─ PID 3938729: node vite (port 5175) ✗ Duplicate
```

**The Problem:**

- Multiple `npm run dev` processes are running
- Each spawns its own Vite instance
- When you kill a Vite process, `npm` restarts it
- You need to kill the **parent `npm` process**, not just Vite

---

## Why This Happens

### Common Causes

1. **Multiple Terminal Sessions**
   - Started `npm run dev` in different terminals
   - Each terminal has its own process

2. **Background Processes**
   - Started with `&` or `nohup`
   - Processes continue running after terminal closes

3. **Scripts Starting Services**
   - Startup scripts that don't check for existing instances
   - Multiple scripts running simultaneously

4. **Auto-Restart Behavior**
   - `npm` automatically restarts child processes
   - Vite's file watcher may trigger restarts

---

## Solution

### Option 1: Kill Parent npm Processes (Recommended)

```bash
# Find all npm run dev processes
ps aux | grep "npm run dev" | grep -v grep

# Kill the parent npm processes (not just Vite)
pkill -f "npm run dev"

# Or kill specific PIDs
kill 725821 3938705

# Then verify
./scripts/check-duplicate-services.sh
```

### Option 2: Use the Updated Cleanup Script

I'll update the cleanup script to kill parent processes:

```bash
./scripts/cleanup-duplicate-services.sh
# Now kills npm processes, not just Vite
```

### Option 3: Find and Stop All Frontend Dev Servers

```bash
# Find all processes in frontend directory
ps aux | grep frontend | grep -E "npm|vite|node" | grep -v grep

# Kill all of them
pkill -f "frontend.*npm"
pkill -f "frontend.*vite"
```

---

## Prevention

### 1. Check Before Starting

```bash
# Check for existing instances
./scripts/check-duplicate-services.sh

# If duplicates found, clean up first
./scripts/cleanup-duplicate-services.sh
```

### 2. Use Service Management Script

```bash
# Use the service management script (checks for conflicts)
./scripts/manage-services.sh start dashboard
```

### 3. Stop All Before Starting

```bash
# Stop all frontend dev servers
pkill -f "npm run dev"
pkill -f "vite"

# Wait a moment
sleep 2

# Then start fresh
cd frontend && npm run dev
```

---

## Updated Cleanup Script

The cleanup script should be updated to:

1. Find parent `npm` processes
2. Kill `npm` processes (which will kill their Vite children)
3. Verify cleanup

This prevents the auto-restart behavior.

---

## Quick Fix Right Now

```bash
# Kill all npm run dev processes
pkill -f "npm run dev"

# Wait a moment for processes to die
sleep 2

# Verify
./scripts/check-duplicate-services.sh

# Start fresh (only one instance)
cd frontend && npm run dev
```

---

**The key insight:** You need to kill the **parent `npm` processes**, not just
the Vite processes, because `npm` will restart Vite automatically.
