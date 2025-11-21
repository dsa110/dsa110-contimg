# Disk Space Display Fix

**Date:** 2025-11-17 **Type:** Bug Fix **Status:** ✅ Complete

---

## Issue

Disk space was not showing in the "System Health" section on the Dashboard page.

---

## Root Cause

The backend API was updated to support multiple disk mount points by changing
from single `disk_total`/`disk_used` fields to a `disks` array with `DiskInfo`
objects. However, the frontend was not updated to use the new format.

**Old API Format (Deprecated):**

```json
{
  "disk_total": 123456789,
  "disk_used": 98765432
}
```

**New API Format:**

```json
{
  "disk_total": null,
  "disk_used": null,
  "disks": [
    {
      "mount_point": "/data/",
      "total": 983349022720,
      "used": 832512393216,
      "free": 100810117120,
      "percent": 84.66
    }
  ]
}
```

---

## Solution

Updated frontend components to use the new `disks` array format:

### Files Modified

1. **`src/pages/DashboardPage.tsx`**
   - Changed from `metrics.disk_total`/`metrics.disk_used` to `metrics.disks[0]`
   - Label now shows mount point: `Disk (/data/)`

2. **`src/pages/HealthPage.tsx`**
   - Changed from `metrics.disk_total`/`metrics.disk_used` to
     `primaryDisk.total`/`used`/`free`
   - Label now shows mount point

3. **`src/pages/SystemDiagnosticsPage.tsx`**
   - Changed from `metrics.disk_total`/`metrics.disk_used` to
     `metrics.disks[0].percent`

---

## Changes Made

### Dashboard Page

**Before:**

```typescript
const diskHistory = useMetricHistory(
  metrics?.disk_total && metrics?.disk_used
    ? (metrics.disk_used / metrics.disk_total) * 100
    : undefined
);
```

**After:**

```typescript
const primaryDisk = metrics?.disks?.[0]; // Get first disk (usually /data/)
const diskHistory = useMetricHistory(primaryDisk?.percent ?? undefined);
```

**StatusIndicator:**

```typescript
<StatusIndicator
  value={primaryDisk.percent}
  label={`Disk (${primaryDisk.mount_point})`}
  // ...
/>
```

---

### Health Page

**Before:**

```typescript
const diskHistory = useMetricHistory(
  metrics?.disk_total && metrics?.disk_used
    ? (metrics.disk_used / metrics.disk_total) * 100
    : undefined
);
```

**After:**

```typescript
const primaryDisk = metrics?.disks?.[0];
const diskHistory = useMetricHistory(primaryDisk?.percent ?? undefined);
```

**Disk Space Stats:**

```typescript
// Total
{
  primaryDisk?.total
    ? `${(primaryDisk.total / 1024 / 1024 / 1024).toFixed(2)} GB`
    : "N/A";
}

// Used
{
  primaryDisk?.used
    ? `${(primaryDisk.used / 1024 / 1024 / 1024).toFixed(2)} GB`
    : "N/A";
}

// Free
{
  primaryDisk?.free
    ? `${(primaryDisk.free / 1024 / 1024 / 1024).toFixed(2)} GB`
    : "N/A";
}
```

---

### System Diagnostics Page

**Before:**

```typescript
value={
  systemMetrics.disk_total && systemMetrics.disk_used
    ? `${((systemMetrics.disk_used / systemMetrics.disk_total) * 100).toFixed(1)}%`
    : "N/A"
}
```

**After:**

```typescript
value={
  systemMetrics.disks?.[0]?.percent
    ? `${systemMetrics.disks[0].percent.toFixed(1)}%`
    : "N/A"
}
```

---

## Benefits

1. **Multi-Mount Support**: Now supports multiple disk mount points (though
   currently displays only the first one)
2. **More Accurate**: Uses direct `percent` field from backend instead of
   calculating
3. **Better Labels**: Shows mount point in label: `Disk (/data/)`
4. **Cleaner Code**: Simpler logic using `disks` array

---

## Future Enhancements

1. **Multiple Disk Display**: Show all disks, not just the primary one
2. **Disk Selection**: Allow user to select which disk to monitor
3. **Aggregate View**: Show total across all disks

---

## Testing

**API Response:**

```bash
$ curl http://localhost:8000/api/metrics/system | jq .disks
[
  {
    "mount_point": "/data/",
    "total": 983349022720,
    "used": 832512393216,
    "free": 100810117120,
    "percent": 84.66
  }
]
```

**Dashboard Display:**

- Disk (/data/): 84.66% with trend indicator
- Color coding: Green (<75%), Orange (75-90%), Red (>90%)

---

## Related Files

- `src/pages/DashboardPage.tsx` - Main dashboard
- `src/pages/HealthPage.tsx` - Health monitoring page
- `src/pages/SystemDiagnosticsPage.tsx` - System diagnostics
- `src/api/types.ts` - TypeScript types (already had `disks` array)

---

**Status:** ✅ Fixed - Disk space now displays correctly on all pages
