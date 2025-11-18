# Dual Disk Display Implementation

**Date:** 2025-11-17 **Type:** Feature Enhancement **Status:** ✅ Complete

---

## Summary

Updated the dashboard to display **both** disk mount points:

- **SSD (/stage/)** - Fast staging area (typically 90% full)
- **HDD (/data/)** - Bulk storage for images and products (typically 84% full)

---

## Background

The DSA-110 pipeline uses two separate storage systems:

1. **`/stage/` (SSD)** - Fast NVMe storage for:
   - Temporary staging
   - Active processing
   - Quick I/O operations
   - Mounted on root filesystem (`/dev/nvme0n1p2`)

2. **`/data/` (HDD)** - Large capacity storage for:
   - FITS images
   - Measurement Sets
   - Calibration tables
   - Pipeline products
   - Separate mount point (`/dev/sdb1`)

Previously, only `/data/` was displayed. Now both are shown.

---

## Changes Made

### Backend (`src/dsa110_contimg/api/routes.py`)

Added logging to track disk collection:

```python
except Exception as e:
    # Log error but continue to next disk
    import logging
    logging.getLogger(__name__).warning(
        f"Failed to get disk usage for {mount_label} ({mount_path}): {e}"
    )
```

The backend was already configured to collect both disks, but we added logging
to help debug any issues.

---

### Frontend - Dashboard Page

**Before:**

```typescript
const primaryDisk = metrics?.disks?.[0]; // Only first disk
const diskHistory = useMetricHistory(primaryDisk?.percent ?? undefined);
```

**After:**

```typescript
// Track both disks separately
const stageDisk = metrics?.disks?.find((d) => d.mount_point === "/stage/");
const dataDisk = metrics?.disks?.find((d) => d.mount_point === "/data/");
const stageDiskHistory = useMetricHistory(stageDisk?.percent ?? undefined);
const dataDiskHistory = useMetricHistory(dataDisk?.percent ?? undefined);
```

**Display:**

```typescript
{stageDisk && (
  <StatusIndicator
    value={stageDisk.percent}
    label="Disk (SSD /stage/)"
    // ... with trend indicator
  />
)}
{dataDisk && (
  <StatusIndicator
    value={dataDisk.percent}
    label="Disk (HDD /data/)"
    // ... with trend indicator
  />
)}
```

---

### Frontend - Health Page

**Updated:**

- Status indicators show both disks side-by-side
- Two separate "Disk Details" cards:
  - "Disk Details - SSD (/stage/)"
  - "Disk Details - HDD (/data/)"

Each card shows:

- Total Space (GB)
- Used Space (GB)
- Available Space (GB)

---

## Display Layout

### Dashboard - System Health Section

```
┌─────────────┬─────────────┬──────────────────┬──────────────────┐
│ CPU: 0.0%   │ Memory: 42% │ Disk (SSD): 90%  │ Disk (HDD): 84%  │
│ Healthy     │ Healthy     │ Warning          │ Healthy          │
└─────────────┴─────────────┴──────────────────┴──────────────────┘
```

### Health Page - Status Indicators

```
┌─────────────┬─────────────┬──────────────────┬──────────────────┐
│ CPU         │ Memory      │ SSD /stage/      │ HDD /data/       │
│   0.0%      │   41.6%     │    90.0%         │    84.7%         │
│ ────────────│ ────────────│ ────────────     │ ──────────       │
│ Sparkline   │ Sparkline   │ Sparkline        │ Sparkline        │
└─────────────┴─────────────┴──────────────────┴──────────────────┘
```

### Health Page - Disk Details Cards

```
┌─────────────────────────┐  ┌─────────────────────────┐
│ Disk Details - SSD      │  │ Disk Details - HDD      │
│ (/stage/)               │  │ (/data/)                │
├─────────────────────────┤  ├─────────────────────────┤
│ Total: 915.8 GB         │  │ Total: 13,036.1 GB      │
│ Used: 775.3 GB          │  │ Used: 10,923.7 GB       │
│ Available: 94.1 GB      │  │ Available: 2,117.5 GB   │
└─────────────────────────┘  └─────────────────────────┘
```

---

## Color Coding

Both disks use the same thresholds:

- 🟢 **Green (Healthy)**: < 75% usage
- 🟠 **Orange (Warning)**: 75-90% usage
- 🔴 **Red (Critical)**: > 90% usage

**Current Status:**

- SSD (/stage/): 90% → **🟠 Warning**
- HDD (/data/): 84% → **🟠 Warning**

---

## API Response Format

```json
{
  "disks": [
    {
      "mount_point": "/stage/",
      "total": 983349022720,
      "used": 885123456789,
      "free": 98225565931,
      "percent": 90.0
    },
    {
      "mount_point": "/data/",
      "total": 14000483987456,
      "used": 11726404399104,
      "free": 2274079588352,
      "percent": 84.66
    }
  ]
}
```

---

## Benefits

1. **Complete Visibility**: Monitor both storage systems simultaneously
2. **Proactive Management**: Identify which disk needs attention
3. **Historical Trends**: Track usage trends for each disk independently
4. **Clear Labels**: SSD vs HDD designation helps understand performance
   characteristics

---

## Testing

**Verify API returns both disks:**

```bash
curl http://localhost:8000/api/metrics/system | jq '.disks'
```

**Expected:**

- Should see 2 disks in array
- `/stage/` showing ~90% usage
- `/data/` showing ~84% usage

---

## Files Modified

1. `src/dsa110_contimg/api/routes.py` - Added error logging
2. `src/pages/DashboardPage.tsx` - Dual disk display
3. `src/pages/HealthPage.tsx` - Dual disk display with details cards
4. `src/pages/SystemDiagnosticsPage.tsx` - Updated to use disks array

---

## Future Enhancements

1. **Disk-Specific Alerts**: Different thresholds for SSD vs HDD
2. **Cleanup Recommendations**: Suggest which disk to clean based on usage
3. **I/O Metrics**: Show read/write speeds for each disk
4. **Historical Charts**: Long-term usage trends per disk

---

**Status:** ✅ Both disks now display on Dashboard and Health pages
