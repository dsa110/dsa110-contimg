# PM2 Warning - Expected Behavior

**Date:** 2025-01-27  
**Status:** ✅ This is expected behavior

---

## Is This Expected?

**YES!** This warning is expected and indicates the script is working correctly.

### What the Warning Means

When you see:

```
⚠️  WARNING: PM2 daemon is running!
  PM2 daemon PID: 3060697
  PM2-managed processes found:
    4050388 npm run dev
```

This means:

1. ✅ **Script detected PM2** - The cleanup script found PM2 daemon running
2. ✅ **Found managed processes** - PM2 is managing npm/vite processes
3. ✅ **Warning about respawning** - PM2 will restart processes if killed

---

## Why PM2 Command Not Found?

If you see:

```
pm2 command not found in PATH
```

This is **normal** if:

- PM2 was installed via npm but not added to PATH
- PM2 is in a user directory (e.g., `~/.npm-global/bin/pm2`)
- PM2 daemon is running but command isn't in system PATH

**This doesn't mean PM2 isn't running** - the daemon can run without the command
being in PATH.

---

## What to Do

### Option 1: Kill PM2 Daemon (Recommended)

The script will prompt:

```
Kill PM2 daemon directly? (y/n)
```

**Answer 'y'** to kill the PM2 daemon, which will:

- Stop PM2 from restarting processes
- Allow cleanup to proceed normally
- Prevent future respawning

### Option 2: Find PM2 Command

If you want to use PM2 commands:

```bash
# Find pm2 command
find ~ -name pm2 2>/dev/null

# Or check common locations
ls -la ~/.npm-global/bin/pm2
ls -la /usr/local/bin/pm2

# Add to PATH if found
export PATH="$HOME/.npm-global/bin:$PATH"
```

### Option 3: Manual Kill

If the script doesn't work:

```bash
# Kill PM2 daemon directly
sudo kill 3060697

# Then run cleanup
./scripts/kill-vite-thoroughly.sh
```

---

## Expected Flow

### Normal Flow (PM2 Detected)

```
1. Script detects PM2 daemon
   └─> Shows warning

2. Script finds PM2-managed processes
   └─> Lists them

3. Script checks for pm2 command
   ├─> If found: Offers to stop PM2 processes
   └─> If not found: Offers to kill PM2 daemon

4. User responds
   ├─> 'y': Kills PM2, continues cleanup
   └─> 'n': Continues anyway (may respawn)

5. Script continues with cleanup
   └─> Kills Vite processes normally
```

---

## Is PM2 Running Expected?

### For Development: NO

**PM2 should NOT be managing dev servers:**

- Dev servers should run directly (`npm run dev`)
- PM2 adds complexity and auto-restart behavior
- Can cause port conflicts and respawning issues

**If PM2 is running for dev:**

- Stop it: `pm2 stop all && pm2 delete all`
- Or kill daemon: `sudo kill <PM2_PID>`

### For Production: YES

**PM2 is fine for production:**

- PM2 is designed for production process management
- Provides monitoring, logging, auto-restart
- Use separate PM2 configs for production

---

## Prevention

To prevent PM2 from managing dev servers:

1. **Don't start dev servers with PM2:**

   ```bash
   # ❌ DON'T
   pm2 start npm --name "frontend" -- run dev

   # ✅ DO
   npm run dev
   # Or
   ./scripts/manage-services.sh start dashboard
   ```

2. **Check before starting:**

   ```bash
   # Check if PM2 is running
   ps aux | grep -i pm2

   # If running, stop it
   pm2 stop all
   pm2 delete all
   ```

3. **Use the cleanup script:**
   ```bash
   # Script will detect and handle PM2
   ./scripts/kill-vite-thoroughly.sh
   ```

---

## Summary

✅ **Warning is expected** - Script is working correctly  
✅ **PM2 detection is correct** - Found daemon and managed processes  
✅ **Command not found is normal** - Daemon can run without command in PATH  
✅ **Script will prompt** - Offers to kill PM2 daemon directly  
✅ **Answer 'y'** - To stop PM2 and prevent respawning

---

**The script is working as designed!** Just answer 'y' to kill PM2 daemon when
prompted.
