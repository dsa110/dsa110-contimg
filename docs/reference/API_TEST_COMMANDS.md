# API Test Commands - Quick Reference

**API Running:** ✅ Port 8000  
**Run these in Terminal 2** (while API runs in Terminal 1)

---

## Quick Verification (30 seconds)

```bash
# Test 1: Basic API status
curl -s "http://localhost:8000/api/status" | jq '.queue.total'

# Test 2: Images endpoint exists
curl -s "http://localhost:8000/api/images?limit=3" | jq '.total, .items | length'
```

**Expected:** Both return numbers (not errors)

---

## Date Filter Tests (The Working Filter)

```bash
# Test 3: Start date filter
curl -s "http://localhost:8000/api/images?start_date=2025-10-28T00:00:00&limit=5" | jq '.items[] | {id, created_at, path}'

# Test 4: Date range filter
curl -s "http://localhost:8000/api/images?start_date=2025-10-28T14:00:00&end_date=2025-10-28T15:00:00&limit=10" | jq '.total'

# Test 5: Combined date filters
curl -s "http://localhost:8000/api/images?start_date=2025-10-28T00:00:00&end_date=2025-10-28T23:59:59&limit=5" | jq '.total'
```

**Expected:**
- Returns filtered images
- Fast response (<200ms)
- Accurate pagination

---

## Noise Filter Test (Expected: No Filtering)

```bash
# Test 6: Noise threshold filter
curl -s "http://localhost:8000/api/images?noise_max=0.001&limit=3" | jq '.items[] | {id, noise_jy}'
```

**Expected:**
- Returns all images (no filtering)
- All `noise_jy` values are `null`
- **This is expected** - metadata not populated (see `docs/known-issues/image-metadata-population.md`)

---

## Experimental Filter Tests

```bash
# Test 7: Declination range filter (may be slow)
time curl -s "http://localhost:8000/api/images?dec_min=40&dec_max=50&limit=3" | jq '.total, .items | length'

# Test 8: Calibrator filter (heuristic)
curl -s "http://localhost:8000/api/images?has_calibrator=true&limit=3" | jq '.total, .items | length'
```

**Expected:**
- Declination filter: Works but slow (1-5 seconds)
- Calibrator filter: Works (pattern matching)

---

## Edge Case Tests

```bash
# Test 9: Invalid date format (should handle gracefully)
curl -s "http://localhost:8000/api/images?start_date=not-a-date&limit=5" | jq '.total'

# Test 10: Out of range declination (should handle gracefully)
curl -s "http://localhost:8000/api/images?dec_min=-100&dec_max=200&limit=5" | jq '.total'
```

**Expected:**
- No crashes
- Returns reasonable results (may ignore invalid inputs)

---

## Metadata Verification

```bash
# Test 11: Check metadata population
curl -s "http://localhost:8000/api/images?limit=1" | jq '.items[0] | {noise_jy, center_ra_deg, center_dec_deg, beam_major_arcsec}'
```

**Expected:**
- All values are `null` (metadata not populated)
- **This confirms the metadata issue**

---

## Health Endpoint Test

```bash
# Test 12: Root health endpoint (after fix)
curl -s "http://localhost:8000/health" | jq '.'

# Test 13: API health endpoint
curl -s "http://localhost:8000/api/health" | jq '.'
```

**Expected:**
- Both return JSON with status information
- No more 404 errors

---

## What to Look For

### ✅ Success Indicators:
- All curl commands return valid JSON
- Date filters reduce result set appropriately
- No 500 errors in API logs
- Fast response times for date filters (<200ms)

### ⚠️ Expected Issues:
- Noise filter doesn't filter (metadata null)
- Declination filter is slow (FITS reading)
- Some metadata fields are null

### ❌ Failure Indicators:
- 500 errors in API logs
- Connection refused errors
- Invalid JSON responses
- Date filters don't work

---

## Quick Test Script

Save this as `test_filters.sh`:

```bash
#!/bin/bash
API_URL="http://localhost:8000"

echo "=== Test 1: Basic API ==="
curl -s "$API_URL/api/status" | jq '.queue.total'

echo -e "\n=== Test 2: Images Endpoint ==="
curl -s "$API_URL/api/images?limit=3" | jq '.total, .items | length'

echo -e "\n=== Test 3: Date Filter ==="
curl -s "$API_URL/api/images?start_date=2025-10-28T00:00:00&limit=5" | jq '.items[] | .created_at' | head -3

echo -e "\n=== Test 4: Noise Filter (Expected: No Filtering) ==="
curl -s "$API_URL/api/images?noise_max=0.001&limit=3" | jq '.items[] | .noise_jy'

echo -e "\n=== Test 5: Health Endpoint ==="
curl -s "$API_URL/health" | jq '.'

echo -e "\n=== Tests Complete ==="
```

Run: `chmod +x test_filters.sh && ./test_filters.sh`

---

**Last Updated:** 2025-01-XX

