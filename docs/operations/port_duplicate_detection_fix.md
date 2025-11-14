# Port Duplicate Detection - Fix Applied

**Date:** 2025-01-27  
**Issue:** Script wasn't detecting duplicate Vite instances on ports 5175 and
5176

---

## Problem

The `check-duplicate-services.sh` script was reporting "No duplicate Vite
instances" even though:

- Port 5173: Vite instance (PID 726008) - Primary
- Port 5175: Vite instance (PID 3480125) - Duplicate
- Port 5176: Vite instance (PID 1772875) - Duplicate

**Root Cause:** The script was using `pgrep -af` which wasn't reliably matching
Vite processes, and the count logic had issues.

---

## Solution

### Updated Detection Method

Changed from process name matching to **port-based detection**:

1. **Check ports directly:** Use `lsof -ti :PORT` to find processes on Vite
   ports (5173-5179)
2. **Verify Vite process:** Check if the PID is actually running Vite using
   `ps -p PID -o cmd`
3. **Count correctly:** Use `wc -l` with proper whitespace handling

### Script Improvements

**Before:**

```bash
vite_processes=$(pgrep -af "vite.*517[0-9]" 2>/dev/null || true)
vite_count=$(echo "$vite_processes" | grep -c "vite" || echo "0")
```

**After:**

```bash
# Check each port individually
for port in 5173 5174 5175 5176 5177 5178 5179; do
    pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | grep -i vite || true)
        if [ -n "$cmd" ]; then
            vite_ports="$vite_ports $port"
        fi
    fi
done
vite_count=$(echo "$vite_ports" | wc -l | tr -d ' ')
```

---

## Results

### Before Fix

```
✓ No duplicate Vite instances
```

### After Fix

```
⚠️  Warning: Multiple Vite instances detected (3 ports in use)

Vite instances by port:
  Port 5173: PID 726008 (node /data/dsa110-contimg/frontend/node_modules/.bin/vite)
  Port 5175: PID 3480125 (node /data/dsa110-contimg/frontend/node_modules/.bin/vite)
  Port 5176: PID 1772875 (node /data/dsa110-contimg/frontend/node_modules/.bin/vite)

Recommendation: Keep only one Vite instance (preferably on port 5173)
  To kill duplicates: pkill -f 'vite.*517[4-9]'
```

---

## New Tools

### 1. Cleanup Script

Created `scripts/cleanup-duplicate-services.sh` to automatically clean up
duplicates:

```bash
./scripts/cleanup-duplicate-services.sh
```

**Features:**

- Detects duplicate Vite and API instances
- Keeps primary instance (port 5173 for Vite)
- Prompts before killing duplicates
- Shows what will be killed

### 2. Improved Detection

The updated `check-duplicate-services.sh` now:

- ✅ Correctly detects all Vite instances
- ✅ Shows port and PID for each instance
- ✅ Provides clear recommendations
- ✅ Exits with error code if duplicates found

---

## Usage

### Check for Duplicates

```bash
./scripts/check-duplicate-services.sh
```

### Clean Up Duplicates

```bash
# Interactive (prompts before killing)
./scripts/cleanup-duplicate-services.sh

# Or kill manually
kill 1772875 3480125  # Kill duplicate PIDs
```

### Verify Cleanup

```bash
./scripts/check-duplicate-services.sh
# Should show: ✓ No duplicate Vite instances
```

---

## Prevention

To prevent duplicates in the future:

1. **Check before starting:**

   ```bash
   ./scripts/check-duplicate-services.sh
   ```

2. **Use service management script:**

   ```bash
   ./scripts/manage-services.sh start dashboard
   # Automatically checks for conflicts
   ```

3. **Add to startup scripts:**
   - The service management script should check for duplicates
   - Fail fast if duplicates detected

---

## Status

✅ **Fixed:** Duplicate detection now works correctly  
✅ **Tested:** Confirmed detection of 3 Vite instances  
✅ **Tools:** Cleanup script available  
✅ **Documentation:** Updated with fix details

---

**See Also:**

- `scripts/check-duplicate-services.sh` - Detection script
- `scripts/cleanup-duplicate-services.sh` - Cleanup script
- `docs/operations/port_usage_unknown_ports.md` - Port analysis
