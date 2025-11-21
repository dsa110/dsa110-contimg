# Backend Issues & Fixes - Quick Start

**Created:** 2025-11-19  
**Status:** ✅ Ready to Execute

---

## What's Wrong?

The dashboard diagnostics revealed several backend issues:

1. **🔴 CRITICAL:** Absurd workflow manager not running (503 errors)
2. **🔴 CRITICAL:** Disk space at 93.7% (HDD) and 82.5% (SSD)
3. **🟡 HIGH:** Database missing metadata (showing "N/A" in tables)
4. **🟡 HIGH:** System load elevated (5.9)
5. **🟢 MEDIUM:** Missing circuit breakers for pipeline stages
6. **🟢 MEDIUM:** Ingestion pipeline not populating metadata

**Result:** Dashboard shows "DEGRADED" status and several errors.

---

## Quick Fix (5 Minutes)

Run this single command to fix most issues automatically:

```bash
cd /data/dsa110-contimg
./scripts/fix_all_backend_issues.sh
```

This will:

- ✅ Clean up disk space (frees 10-50GB depending on old data)
- ✅ Schedule automated cleanup (runs daily at 2 AM)
- ✅ Backfill missing database metadata
- ✅ Schedule health monitoring (runs every 30 minutes)
- ✅ Verify all fixes worked

**Time:** 5-10 minutes  
**Requires:** Root/sudo access for cron scheduling

---

## What Each Script Does

### 1. `cleanup_disk_space.sh`

**Purpose:** Free up disk space  
**Actions:**

- Deletes staging data older than 7 days (MS files, images)
- Deletes incoming data older than 30 days (HDF5/UVH5 files)
- Deletes logs older than 90 days
- Removes temporary files

**Run manually:**

```bash
./scripts/cleanup_disk_space.sh
```

**Expected result:** Disk usage drops below 80%

---

### 2. `backfill_metadata.py`

**Purpose:** Fix "N/A" values in dashboard tables  
**Actions:**

- Reads FITS headers to extract RA/Dec coordinates
- Extracts image names and types from filenames
- Updates database with missing metadata

**Run manually:**

```bash
source scripts/developer-setup.sh  # Ensure casa6 environment
python scripts/backfill_metadata.py
```

**Expected result:** Images table shows filenames and coordinates

---

### 3. `health_check.sh`

**Purpose:** Monitor system health and send alerts  
**Actions:**

- Checks disk space (alerts if > 80%)
- Checks system load (alerts if > 6.0)
- Checks Absurd service availability
- Checks database accessibility

**Run manually:**

```bash
./scripts/health_check.sh
```

**View logs:**

```bash
tail -f logs/health_check_$(date +%Y%m%d).log
```

---

### 4. `fix_all_backend_issues.sh`

**Purpose:** Run all fixes in correct order  
**Actions:**

- Runs cleanup_disk_space.sh
- Schedules daily cleanup
- Runs backfill_metadata.py
- Schedules health monitoring
- Verifies all fixes worked

**This is the master script - run this one!**

---

## Manual Steps (For Issues Not Automated)

### Enable Absurd Workflow Manager

**Symptoms:** Queue Depth Monitoring shows "Connection Failed"

**Fix Option 1: Enable in environment**

```bash
echo "ABSURD_ENABLED=true" >> /data/dsa110-contimg/.env
echo "ABSURD_API_URL=http://localhost:8001" >> /data/dsa110-contimg/.env
sudo systemctl restart dsa110-backend
```

**Fix Option 2: Start Absurd service**

```bash
cd /data/dsa110-contimg
nohup python -m dsa110_contimg.absurd.server --port 8001 --host 0.0.0.0 > logs/absurd.log 2>&1 &
```

**Verify:**

```bash
curl http://localhost:8000/api/absurd/health
# Should return: {"status": "ok"} or similar JSON
```

---

### Reduce System Load

**Symptoms:** System load > 6.0, slow performance

**Fix:**

```bash
# Kill stuck CASA processes (running > 6 hours)
ps aux | awk '/casa.*tclean/ && $10 > "06:00:00" {print $2}' | xargs -r kill -9

# Reduce parallelism in config
vim /data/dsa110-contimg/config/config.yaml
# Set:
#   max_concurrent_jobs: 2
#   max_threads_per_job: 4

# Restart backend
sudo systemctl restart dsa110-backend
```

---

## Verification

After running fixes, check:

```bash
# 1. Disk space improved
df -h /data /stage /
# Should show < 80% usage

# 2. Absurd responding
curl http://localhost:8000/api/absurd/health
# Should return JSON, not 503

# 3. Database metadata populated
sqlite3 state/products.sqlite3 "SELECT COUNT(*), COUNT(name), COUNT(ra_deg) FROM images;"
# All counts should be similar

# 4. System load normal
uptime
# Load should be < 6.0

# 5. Dashboard status
curl http://localhost:8000/api/status
# Should show "healthy" or at least not "critical"

# 6. Cron jobs scheduled
crontab -l
# Should show cleanup and health_check jobs
```

---

## Expected Results

### Before Fixes:

- System Health: **DEGRADED**
- HDD: **93.7% (Critical)**
- SSD: **82.5% (Warning)**
- System Load: **5.9 (Warning)**
- Queue Depth: **Connection Failed**
- Images Table: **Many "N/A" fields**
- MS Table: **All "N/A" fields**

### After Fixes:

- System Health: **HEALTHY** or **WARNING** (not CRITICAL)
- HDD: **< 80% (Healthy)**
- SSD: **< 80% (Healthy)**
- System Load: **< 4.0 (Healthy)**
- Queue Depth: **Shows data** (if Absurd enabled) or **Demo Mode**
- Images Table: **Filenames, RA, Dec populated**
- MS Table: **Names and Scan IDs populated**

---

## Automated Maintenance

After running `fix_all_backend_issues.sh`, these jobs run automatically:

| Task             | Schedule         | Purpose                         |
| ---------------- | ---------------- | ------------------------------- |
| **Disk Cleanup** | Daily at 2:00 AM | Enforce data retention policies |
| **Health Check** | Every 30 minutes | Detect issues early             |

**View scheduled jobs:**

```bash
crontab -l
```

**View logs:**

```bash
# Cleanup logs
ls -lh logs/disk_cleanup_*.log
tail -f logs/disk_cleanup_*.log

# Health check logs
ls -lh logs/health_check_*.log
tail -f logs/health_check_*.log
```

---

## Troubleshooting

### Script fails with "Permission denied"

```bash
chmod +x scripts/*.sh scripts/*.py
```

### Cleanup doesn't free enough space

```bash
# Find largest directories
du -h /data | sort -rh | head -20
du -h /stage | sort -rh | head -20

# Consider manually removing old data
```

### Absurd still returns 503 after enabling

```bash
# Check backend logs
tail -f logs/backend.log
journalctl -u dsa110-backend -f

# Verify configuration loaded
cat .env | grep ABSURD
```

### Metadata backfill fails

```bash
# Ensure casa6 environment
source scripts/developer-setup.sh
which python  # Should be casa6 python

# Check database exists and is writable
ls -lh state/products.sqlite3
sqlite3 state/products.sqlite3 "PRAGMA integrity_check;"
```

---

## Complete Documentation

For detailed information, see:

1. **Quick Reference:**  
   `docs/troubleshooting/BACKEND_ISSUES_SUMMARY.md`

2. **Detailed Analysis:**  
   `docs/troubleshooting/backend_issues_and_fixes.md`

3. **Step-by-Step Guide:**  
   `docs/how-to/fix_backend_issues.md`

4. **Data Architecture:**  
   `docs/concepts/DIRECTORY_ARCHITECTURE.md`

---

## Support

If issues persist after running all fixes:

1. Check logs in `logs/` directory
2. Review detailed documentation (links above)
3. Run verification commands (see "Verification" section)
4. Contact operations team with log files

---

**Remember:** The dashboard is working correctly! It's showing you real backend
issues that need fixing. These fixes address the root causes.

---

**Last Updated:** 2025-11-19  
**Version:** 1.0  
**Tested:** ✅ Scripts created and verified
