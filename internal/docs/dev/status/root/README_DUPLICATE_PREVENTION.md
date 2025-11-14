# Automatic Duplicate Prevention

**Status:** ✅ **ACTIVE**

The pipeline now **automatically prevents duplicate service instances** without
any manual intervention.

---

## How It Works

### Automatic Prevention

When you start any service, duplicate prevention runs automatically:

```bash
# Frontend - automatic prevention
cd frontend && npm run dev

# API - automatic prevention
./scripts/manage-services.sh start api

# Dashboard - automatic prevention
./scripts/manage-services.sh start dashboard
```

**What happens automatically:**

1. ✅ Checks for duplicate instances
2. ✅ Auto-cleans duplicates (kills parent npm processes)
3. ✅ Acquires service lock (prevents race conditions)
4. ✅ Verifies port availability
5. ✅ Starts service safely

---

## Quick Reference

### Check for Duplicates

```bash
./scripts/check-duplicate-services.sh
```

### Clean Up Duplicates

```bash
# Interactive cleanup
./scripts/cleanup-duplicate-services.sh

# Kill all frontend dev processes
./scripts/kill-all-frontend-dev.sh
```

### Disable Auto-Cleanup

```bash
# Error instead of auto-cleaning
AUTO_CLEANUP_DUPLICATES=0 npm run dev
```

---

## Files

- `scripts/prevent-duplicate-services.sh` - Prevention script
- `scripts/service-lock.sh` - Locking mechanism
- `frontend/scripts/start-dev-safe.sh` - Safe startup
- `scripts/check-duplicate-services.sh` - Detection
- `scripts/cleanup-duplicate-services.sh` - Manual cleanup

---

## Documentation

See `docs/operations/automatic_duplicate_prevention.md` for complete details.

---

**No manual steps needed - prevention is automatic!**
