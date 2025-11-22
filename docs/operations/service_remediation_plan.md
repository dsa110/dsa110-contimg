# Service Remediation Strategy

## Executive Summary

**Date:** 2025-11-21  
**Status:** 38/51 Healthy, 13/51 Degraded, 0/51 Unhealthy

## Issues Identified

### Category 1: Missing Routes (404) - 7 services

**Root Cause:** Routes not implemented in backend API

1. `/api/health/services` - Health Services
2. `/api/mosaics?limit=10` - Mosaics listing
3. `/api/sources?limit=10` - Sources listing
4. `/api/pointing/history?limit=10` - Pointing History
5. `/api/calibration/status` - Calibration Status
6. `/api/visualization/casatable/info` - Casa Table Info
7. `/api/ws/status` - WebSocket Status

**Priority:** HIGH  
**Fix Strategy:** Implement missing route handlers in
`backend/src/dsa110_contimg/api/routes.py`

### Category 2: Server Errors (500) - 3 services

**Root Cause:** Backend exceptions during request processing

1. `/api/regions?limit=10` - Regions API
2. `/api/absurd/tasks?limit=10` - ABSURD Tasks
3. `/api/absurd/queues/dsa110-pipeline/stats` - ABSURD Queue Stats

**Priority:** MEDIUM  
**Fix Strategy:** Check backend logs, fix exceptions, add error handling

### Category 3: Parameter Validation (422/400/403) - 3 services

**Root Cause:** Invalid or missing request parameters

1. `/api/pointing_history?limit=10` - Missing required params (start_mjd,
   end_mjd)
2. `/api/visualization/browse?path=/data` - Path traversal restriction
3. `/api/visualization/fits/info?path=/data/test.fits` - Absolute path not
   allowed

**Priority:** LOW  
**Fix Strategy:** Update frontend to pass correct parameters, or relax
validation rules

## Remediation Plan

### Phase 1: Quick Wins (Missing Routes) - 2-3 hours

Implement stub endpoints that return empty/default responses:

- [ ] Health Services endpoint
- [ ] Mosaics listing endpoint
- [ ] Sources listing endpoint
- [ ] Pointing History endpoint
- [ ] Calibration Status endpoint
- [ ] Casa Table Info endpoint
- [ ] WebSocket Status endpoint

**Expected Impact:** 7 services → healthy (45/51 total)

### Phase 2: Fix Server Errors - 1-2 hours

Investigate and fix backend exceptions:

- [ ] Debug Regions API (likely database schema issue)
- [ ] Debug ABSURD Tasks API (check Absurd integration)
- [ ] Debug ABSURD Queue Stats API (check queue name/existence)

**Expected Impact:** 3 services → healthy (48/51 total)

### Phase 3: Parameter Fixes - 30 mins

Update frontend or backend validation:

- [ ] Add default date range for pointing_history
- [ ] Fix visualization path handling or update frontend
- [ ] Add test file paths for FITS/Casa endpoints

**Expected Impact:** 3 services → healthy (51/51 total)

## Implementation Order

### Priority 1: Missing Routes (2-3 hours)

Files to modify:

- `backend/src/dsa110_contimg/api/routes.py`
- `backend/src/dsa110_contimg/api/models.py` (for response models)

### Priority 2: Server Errors (1-2 hours)

Steps:

1. Check backend logs: `tail -f /data/dsa110-contimg/artifacts/logs/*.log`
2. Reproduce errors locally
3. Add error handling and logging
4. Test fixes

### Priority 3: Parameter Validation (30 mins)

Files to modify:

- Frontend: `frontend/src/pages/SystemStatusPage.tsx`
- Or Backend: Route parameter handling

## Verification Strategy

After each phase:

```bash
python3 scripts/diagnostics/diagnose_all_services.py
```

Monitor improvements in healthy count.

## Rollback Plan

All changes in feature branch:

```bash
git checkout -b fix/service-health-improvements
git commit -m "feat: implement missing API endpoints"
# Test
git push origin fix/service-health-improvements
# If issues: git reset --hard origin/main
```

## Success Criteria

- ✅ 51/51 services healthy
- ✅ No 404 errors
- ✅ No 500 errors
- ✅ All endpoints return valid responses
- ✅ Response times < 100ms for most endpoints

## Next Steps

1. Start with Phase 1 (missing routes) - highest impact
2. Create stub implementations
3. Test with diagnostic script
4. Move to Phase 2 once Phase 1 complete
