# Calibration Procedure Enhancements

## Current Limitations

### 1. **No Calibrator Visibility**
- Users have no idea which calibrator is selected
- No information about calibrator flux, position, or source name
- Cannot see which MS contains a calibrator transit vs which don't
- No way to preview calibrator matches before running calibration

### 2. **No Control Over Cal Table Types**
- Always runs K + BP + G (delay, bandpass, gain)
- No way to skip K-cal (delay)
- No way to run only BP + G
- No way to run only G (phase-only gains)
- Cannot customize solution intervals or parameters

### 3. **No Field Selection**
- Auto-field selection is opaque
- Cannot manually select which fields to calibrate
- Cannot see which fields contain the calibrator

### 4. **No Refant Control**
- Uses QA ranking or fallback median antenna
- No manual override in UI
- No visibility into which refant was chosen

### 5. **No Calibration Preview**
- Cannot see if MS contains a suitable calibrator before calibration
- No metadata about observation time vs calibrator transits
- No flux/SNR predictions

---

## Proposed Enhancements

### Phase 1: Calibrator Detection & Display (High Priority)

#### 1.1 Calibrator Match Endpoint
**Backend**: `GET /api/ms/{path}/calibrator-matches`

Returns list of potential calibrators for an MS with:
- Source name (e.g., "3C286", "3C48")
- RA/Dec (J2000)
- Flux at 1.4 GHz (Jy)
- Primary beam response (0-1)
- Weighted flux (PB × flux)
- Separation from meridian (deg)
- Recommended fields (indices)
- Transit time (if available)
- **Match quality**: "excellent" (PB > 0.8), "good" (0.5-0.8), "marginal" (0.3-0.5), "poor" (<0.3)

**Implementation**:
```python
# In routes.py
@router.get("/ms/{ms_path:path}/calibrator-matches")
def get_calibrator_matches(ms_path: str, catalog: str = "vla", radius_deg: float = 1.0):
    """Find calibrator candidates for an MS."""
    from dsa110_contimg.calibration.catalogs import calibrator_match, read_vla_parsed_catalog_csv
    from dsa110_contimg.pointing import read_pointing_from_ms
    
    ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
    
    # Get MS metadata
    pt_dec = read_pointing_from_ms(ms_full_path)
    mid_mjd = get_mid_mjd_from_ms(ms_full_path)  # Need to implement
    
    # Load catalog
    if catalog == "vla":
        cat_path = os.getenv("VLA_CATALOG", "data/catalogs/VLA_calibrators.csv")
        df = read_vla_parsed_catalog_csv(cat_path)
    else:
        raise HTTPException(400, "Unknown catalog")
    
    # Get top matches
    matches = calibrator_match(df, pt_dec, mid_mjd, radius_deg=radius_deg, top_n=5)
    
    return {"matches": matches, "pointing_dec": float(pt_dec.to_value(u.deg))}
```

#### 1.2 Calibrator Match UI Component
**Frontend**: Display in MS Metadata Panel

```typescript
// Add to MS metadata panel
{msMetadata && (() => {
  const { data: calMatches } = useCalibratorMatches(selectedMS);
  if (!calMatches || calMatches.matches.length === 0) {
    return (
      <Box sx={{ mt: 1, p: 1, bgcolor: '#3e2723', borderRadius: 1 }}>
        <Typography variant="caption" color="warning.main">
          No calibrators detected (pointing may not contain suitable source)
        </Typography>
      </Box>
    );
  }
  
  const best = calMatches.matches[0];
  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="subtitle2" gutterBottom>
        Calibrator Matches
      </Typography>
      <Box sx={{ p: 1, bgcolor: '#1e3a1e', borderRadius: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#4caf50' }}>
          Best: {best.name}
        </Typography>
        <Typography variant="caption" display="block">
          Flux: {best.flux_jy.toFixed(2)} Jy | PB: {best.pb_response.toFixed(2)} | Quality: {best.quality}
        </Typography>
        <Typography variant="caption" display="block">
          RA: {best.ra_deg.toFixed(4)}° | Dec: {best.dec_deg.toFixed(4)}°
        </Typography>
      </Box>
      {calMatches.matches.length > 1 && (
        <Accordion>
          <AccordionSummary>Show {calMatches.matches.length - 1} more</AccordionSummary>
          <AccordionDetails>
            {calMatches.matches.slice(1).map((m, i) => (
              <Box key={i} sx={{ mb: 1 }}>
                {m.name} - {m.flux_jy.toFixed(2)} Jy (PB: {m.pb_response.toFixed(2)})
              </Box>
            ))}
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
})()}
```

---

### Phase 2: Flexible Cal Table Selection (High Priority)

#### 2.1 Enhanced Calibration Parameters Model
```python
# In models.py
class CalibrateJobParams(BaseModel):
    field: Optional[str] = None
    refant: Optional[str] = "103"
    
    # Cal table selection
    solve_delay: bool = True  # K-cal
    solve_bandpass: bool = True  # BP-cal
    solve_gains: bool = True  # G-cal
    
    # Advanced options
    delay_solint: str = "inf"
    bandpass_solint: str = "inf"
    gain_solint: str = "inf"
    gain_calmode: str = "ap"  # "ap" (amp+phase), "p" (phase-only), "a" (amp-only)
    
    # Field selection
    auto_fields: bool = True
    manual_fields: Optional[List[int]] = None
    
    # Catalog matching
    cal_catalog: Optional[str] = "vla"
    search_radius_deg: float = 1.0
    min_pb: float = 0.5
    
    # Flagging
    do_flagging: bool = False
```

#### 2.2 Calibration UI with Options
```typescript
// In Calibrate tab, add expandable advanced options
<Typography variant="subtitle2" gutterBottom>
  Calibration Tables to Generate
</Typography>
<FormGroup>
  <FormControlLabel
    control={<Checkbox checked={calibParams.solve_delay} onChange={...} />}
    label="K (Delay calibration)"
  />
  <FormControlLabel
    control={<Checkbox checked={calibParams.solve_bandpass} onChange={...} />}
    label="BP (Bandpass calibration)"
  />
  <FormControlLabel
    control={<Checkbox checked={calibParams.solve_gains} onChange={...} />}
    label="G (Gain calibration)"
  />
</FormGroup>

<Accordion>
  <AccordionSummary>Advanced Options</AccordionSummary>
  <AccordionDetails>
    <TextField
      label="Gain Solution Interval"
      value={calibParams.gain_solint}
      helperText="e.g., 'inf', '60s', '10min'"
    />
    <FormControl>
      <InputLabel>Gain Cal Mode</InputLabel>
      <Select value={calibParams.gain_calmode}>
        <MenuItem value="ap">Amp + Phase</MenuItem>
        <MenuItem value="p">Phase only</MenuItem>
        <MenuItem value="a">Amp only</MenuItem>
      </Select>
    </FormControl>
    <TextField
      label="Minimum PB Response"
      type="number"
      value={calibParams.min_pb}
      helperText="0.0 - 1.0 (higher = stricter)"
    />
  </AccordionDetails>
</Accordion>
```

#### 2.3 Backend Cal Runner Enhancement
Modify `run_calibrate_job` to respect the new parameters:

```python
def run_calibrate_job(job_id: int, ms_path: str, params: dict, products_db: Path):
    """Run calibration with flexible table selection."""
    solve_delay = params.get("solve_delay", True)
    solve_bandpass = params.get("solve_bandpass", True)
    solve_gains = params.get("solve_gains", True)
    
    # Build CLI args
    cmd = ["-m", "dsa110_contimg.calibration.cli", "calibrate", "--ms", ms_path]
    
    if params.get("field"):
        cmd += ["--field", params["field"]]
    
    cmd += ["--refant", params.get("refant", "103")]
    
    # Control which tables to solve
    if not solve_delay:
        cmd += ["--skip-delay"]
    if not solve_bandpass:
        cmd += ["--skip-bandpass"]
    if not solve_gains:
        cmd += ["--skip-gains"]
    
    # Advanced parameters
    if params.get("gain_solint"):
        cmd += ["--gain-solint", params["gain_solint"]]
    if params.get("gain_calmode"):
        cmd += ["--gain-calmode", params["gain_calmode"]]
    
    # ... rest of execution
```

**Note**: This requires updating `calibration/cli.py` to accept these new flags.

---

### Phase 3: Field Selection & Preview (Medium Priority)

#### 3.1 Field Browser Endpoint
**Backend**: `GET /api/ms/{path}/fields`

Returns list of fields with:
- Field ID
- Field name
- Phase center (RA/Dec)
- Number of integrations
- Time range
- Whether field contains calibrator (based on PB threshold)

#### 3.2 Field Selection UI
Add to Calibrate tab:
```typescript
<Typography variant="subtitle2" gutterBottom>
  Field Selection
</Typography>
<FormControlLabel
  control={
    <Checkbox 
      checked={calibParams.auto_fields} 
      onChange={(e) => setCalibParams({...calibParams, auto_fields: e.target.checked})}
    />
  }
  label="Auto-select fields (recommended)"
/>

{!calibParams.auto_fields && (() => {
  const { data: fields } = useMSFields(selectedMS);
  return (
    <Box>
      <Typography variant="caption">Manual field selection:</Typography>
      <FormGroup>
        {fields?.items.map((field) => (
          <FormControlLabel
            key={field.id}
            control={
              <Checkbox
                checked={calibParams.manual_fields?.includes(field.id)}
                onChange={(e) => {
                  const current = calibParams.manual_fields || [];
                  const updated = e.target.checked
                    ? [...current, field.id]
                    : current.filter(id => id !== field.id);
                  setCalibParams({...calibParams, manual_fields: updated});
                }}
              />
            }
            label={`${field.id}: ${field.name} ${field.has_calibrator ? '(Calibrator)' : ''}`}
          />
        ))}
      </FormGroup>
    </Box>
  );
})()}
```

---

### Phase 4: Batch Calibration & MS Filtering (Medium Priority)

#### 4.1 MS List with Calibrator Status
Enhance the MS list dropdown to show which MS files have calibrators:

```typescript
// In MS dropdown
<Select>
  {msList?.items.map((ms) => (
    <MenuItem key={ms.path} value={ms.path}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {ms.path}
        {ms.has_calibrator && (
          <Chip label="CAL" size="small" color="success" />
        )}
      </Box>
    </MenuItem>
  ))}
</Select>
```

**Backend**: Enhance `GET /api/ms` to include `has_calibrator` flag:
```python
@router.get("/ms", response_model=MSList)
def list_ms(include_calibrator_check: bool = False):
    # ... existing code ...
    
    if include_calibrator_check:
        for ms_entry in entries:
            # Quick check: does this MS have any strong calibrators?
            try:
                matches = get_calibrator_matches_quick(ms_entry.path)
                ms_entry.has_calibrator = len(matches) > 0 and matches[0].pb_response > 0.5
            except:
                ms_entry.has_calibrator = False
    
    return MSList(items=entries)
```

#### 4.2 "Calibrate All with Calibrators" Batch Job
Add button to calibrate all MS files that contain calibrators:

```typescript
<Button
  variant="outlined"
  onClick={() => {
    const msWithCal = msList.items.filter(ms => ms.has_calibrator);
    // Create batch calibration job
    batchCalibrateMutation.mutate({ ms_paths: msWithCal.map(ms => ms.path) });
  }}
>
  Calibrate All MS with Calibrators ({msWithCal.length})
</Button>
```

---

### Phase 5: Calibration Quality Feedback (Low Priority)

#### 5.1 Cal Table QA Endpoint
**Backend**: `GET /api/caltables/{path}/qa`

Returns:
- Solution SNR statistics (median, min, max)
- Number of flagged solutions
- Antenna-based quality metrics
- Per-SPW quality
- Suggested refant based on solutions

#### 5.2 Cal Table QA Display
Show in Apply tab when hovering over or selecting a cal table:
```typescript
<Tooltip title={
  <Box>
    <Typography>SNR: {table.qa.median_snr.toFixed(1)}</Typography>
    <Typography>Flagged: {table.qa.percent_flagged.toFixed(1)}%</Typography>
    <Typography>Quality: {table.qa.quality_grade}</Typography>
  </Box>
}>
  <Chip label={table.table_type} />
</Tooltip>
```

---

## Implementation Priority

### Immediate (Next Session):
1. **Calibrator Match Endpoint** - Critical for user understanding
2. **Calibrator Match UI** - Show in MS metadata panel
3. **Cal Table Type Selection** - Checkboxes for K/BP/G

### Short Term (1-2 days):
4. **Enhanced Calibration Parameters** - solint, calmode options
5. **Field Selection UI** - Manual field picker
6. **MS List Calibrator Status** - Flag MS with calibrators

### Medium Term (1 week):
7. **Batch Calibration** - Calibrate multiple MS at once
8. **Field Browser** - Detailed field information
9. **Refant Selection** - Manual refant override in UI

### Long Term (Future):
10. **Cal Table QA** - Quality metrics and visualization
11. **Calibrator Transit Prediction** - Predict optimal cal times
12. **Custom Calibrator Catalog** - Upload user catalogs

---

## Technical Considerations

### 1. Calibrator Matching Performance
- Catalog matching can be slow for large catalogs
- **Solution**: Cache calibrator matches in MS metadata when MS is registered
- **Alternative**: Run matching in background thread, show spinner

### 2. CLI Compatibility
- Current `calibration/cli.py` doesn't support skip flags
- **Solution**: Add `--skip-delay`, `--skip-bandpass`, `--skip-gains` flags
- **Fallback**: Run separate commands for each cal type

### 3. Field Information Extraction
- Reading field info from MS requires CASA tables
- **Solution**: Cache field info when MS is registered
- **Alternative**: Lazy-load on demand with timeout

### 4. Batch Job Management
- Multiple parallel calibration jobs can overwhelm system
- **Solution**: Queue batch jobs, run sequentially
- **Alternative**: Limit concurrency (max 2-3 parallel cal jobs)

---

## Example User Workflow (After Enhancements)

### Scenario 1: Quick Calibration (Default)
1. Select MS from dropdown
2. See "Best Calibrator: 3C286 (5.2 Jy, PB: 0.82)" in metadata panel
3. Go to Calibrate tab
4. Click "Run Calibration" (uses defaults: K+BP+G, auto fields)
5. Done in 3 clicks

### Scenario 2: Custom Calibration
1. Select MS from dropdown
2. See calibrator info
3. Go to Calibrate tab
4. Uncheck "K (Delay)" - only want BP + G
5. Expand "Advanced Options"
6. Set Gain Cal Mode to "Phase only"
7. Set Gain Solution Interval to "60s"
8. Click "Run Calibration"

### Scenario 3: Batch Calibration
1. Click "Show MS with Calibrators" filter
2. See 15 MS files with calibrator detections
3. Click "Calibrate All with Calibrators (15)"
4. Jobs queued and run sequentially
5. Monitor progress in Recent Jobs

### Scenario 4: Marginal Calibrator
1. Select MS
2. See "Best Calibrator: 3C48 (PB: 0.42, Quality: marginal)"
3. Warning: "Low PB response - calibration may be poor"
4. Expand calibrator list, see no better options
5. Proceed anyway or skip this MS

---

## API Summary (New Endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ms/{path}/calibrator-matches` | Find calibrator candidates |
| GET | `/api/ms/{path}/fields` | List MS fields with metadata |
| GET | `/api/ms?has_calibrator=true` | Filter MS with calibrators |
| GET | `/api/caltables/{path}/qa` | Cal table quality metrics |
| POST | `/api/jobs/calibrate-batch` | Batch calibration job |

---

## Files to Modify

### Backend
- `src/dsa110_contimg/api/models.py` - Add enhanced calibration models
- `src/dsa110_contimg/api/routes.py` - Add new endpoints
- `src/dsa110_contimg/api/job_runner.py` - Enhance cal job runner
- `src/dsa110_contimg/calibration/cli.py` - Add skip flags, expose more options

### Frontend
- `frontend/src/api/types.ts` - Add calibrator match types
- `frontend/src/api/queries.ts` - Add new hooks
- `frontend/src/pages/ControlPage.tsx` - Enhance Calibrate tab UI

---

## Questions to Resolve

1. **Should we support uploading custom calibrator catalogs?**
   - Pros: Flexibility for non-VLA sources
   - Cons: Validation complexity, format standardization

2. **Should calibration be skippable in workflow?**
   - Some MS may not have calibrators
   - Could add "Convert → Image (no cal)" option

3. **Should we auto-skip MS without calibrators?**
   - Could save time in batch workflows
   - But user may want to try anyway

4. **How to handle multiple calibrators in same MS?**
   - Currently picks best, but user may want to choose
   - Add calibrator selection dropdown?

5. **Should we show transit times?**
   - Requires LST calculation + catalog matching
   - Very useful for understanding data quality
   - Worth the implementation effort?

---

This document provides a comprehensive roadmap for enhancing the calibration procedure. The immediate priorities (calibrator detection + table type selection) provide the most value with reasonable implementation effort.

