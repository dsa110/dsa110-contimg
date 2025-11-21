# Image Filters - Manual Testing Quick Guide

**Quick Reference:** Steps to manually test the image filtering implementation.

---

## Prerequisites

1. **Backend API Server:**

   ```bash
   cd /data/dsa110-contimg
   PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -m uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend Dev Server:**
   ```bash
   cd /data/dsa110-contimg/frontend
   npm run dev
   ```

---

## Quick API Tests (5 minutes)

### Test 1: Working Filters (Should be fast)

```bash
# Noise threshold
curl -s "http://localhost:8000/api/images?noise_max=0.001&limit=5" | jq '.total'

# Date range
curl -s "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00&limit=5" | jq '.total'

# Combined
curl -s "http://localhost:8000/api/images?noise_max=0.001&start_date=2025-01-01T00:00:00&limit=10" | jq '.total'
```

**Expected:** Fast response (<200ms), valid JSON with `items` array

### Test 2: Experimental Filters (May be slow)

```bash
# Declination range (may take 1-5 seconds)
curl -s "http://localhost:8000/api/images?dec_min=40&dec_max=50&limit=5" | jq '.total'

# Calibrator filter
curl -s "http://localhost:8000/api/images?has_calibrator=true&limit=5" | jq '.total'
```

**Expected:** Slower response (1-5s acceptable), may return filtered results

### Test 3: Edge Cases (Should not crash)

```bash
# Invalid date (should be ignored gracefully)
curl -s "http://localhost:8000/api/images?start_date=not-a-date&limit=5" | jq '.total'

# Out of range declination
curl -s "http://localhost:8000/api/images?dec_min=-100&dec_max=200&limit=5" | jq '.total'
```

**Expected:** No crashes, returns reasonable results

---

## Quick UI Tests (10 minutes)

### Navigate to Sky View

1. Open browser: `http://localhost:3000/sky` (or your frontend port)
2. Open DevTools (F12) → Console tab
3. Verify no JavaScript errors

### Test Basic Filters

1. **MS Path Search:**
   - Type in search box → Press Enter
   - Verify images filter

2. **Image Type Dropdown:**
   - Select "Image" → Verify filter applies
   - Select "All Types" → Verify filter clears

3. **PB Corrected:**
   - Toggle dropdown → Verify filter applies

### Test Advanced Filters

1. **Expand Advanced Filters:**
   - Click expand icon (▼) → Verify section expands
   - Verify all controls visible: date pickers, slider, text input, checkbox,
     "Clear All" button

2. **Date Range:**
   - Click Start Date → Select date → Verify URL updates (`?start_date=...`)
   - Click End Date → Select date → Verify images filter
   - Check URL bar for parameters

3. **Noise Threshold:**
   - Enter "0.5" in noise input (0.5 mJy)
   - Verify images filter
   - Clear input → Verify filter removes

4. **Declination Slider:**
   - Move slider to [30, 60]
   - Verify displayed range updates
   - Note: May be slow (this is expected)

5. **Calibrator Checkbox:**
   - Check box → Verify filter applies
   - Uncheck → Verify filter removes

6. **Clear All Filters:**
   - Set multiple filters
   - Click "Clear All" button
   - Verify all filters reset
   - Verify URL clears
   - Verify full image list displayed

### Test URL Synchronization

1. Set multiple filters (date, noise, declination)
2. Copy URL from address bar
3. Open new tab → Paste URL
4. Verify filters restore correctly

---

## Success Criteria

✅ **API Tests:**

- Working filters respond quickly (<200ms)
- Experimental filters work (even if slow)
- No crashes on edge cases

✅ **UI Tests:**

- All filters functional
- URL synchronization works
- Clear All Filters works
- No console errors

---

## If Tests Fail

**API Issues:**

- Check server logs for errors
- Verify database connection
- Check FITS file accessibility

**UI Issues:**

- Check browser console for errors
- Verify API responses in Network tab
- Check React Query cache

**Report Issues:**

- Document exact steps to reproduce
- Include error messages
- Note browser/OS version

---

**Estimated Time:** 15 minutes total  
**Priority:** High (before commit)
