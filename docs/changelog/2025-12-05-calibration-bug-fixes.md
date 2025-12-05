# 2025-12-05: Calibration Module Bug Fixes

## Summary

Fixed two critical bugs in the calibrator selection pipeline that caused
`select_bandpass_from_catalog()` to return incorrect results.

## Bug Fixes

### 1. Catalog Missing Calibrators (catalogs.py)

**Problem**: `load_vla_catalog_from_sqlite()` used the `vla_20cm` view which
performs an INNER JOIN between calibrators and fluxes tables. Calibrators
without 20cm flux measurements were excluded entirely.

**Impact**: Calibrators like `1911+161` (which only has Q-band/43GHz flux) were
invisible to the selection function, causing it to pick distant calibrators
instead.

**Fix**: Changed to use LEFT JOIN with `COALESCE(f.flux_jy, 1.0)` to include
all calibrators with a default 1.0 Jy flux when 20cm data is missing.

```python
# Before: Only calibrators with 20cm flux (1041 entries)
df = pd.read_sql_query("SELECT * FROM vla_20cm", conn)

# After: All calibrators with default flux fallback (1861 entries)
df = pd.read_sql_query("""
    SELECT c.name, c.ra_deg, c.dec_deg,
           COALESCE(f.flux_jy, 1.0) as flux_jy
    FROM calibrators c
    LEFT JOIN fluxes f ON c.name = f.name AND f.band = '20cm'
""", conn)
```

### 2. Airy Pattern Wrong Formula (beam_model.py)

**Problem**: `_airy_primary_beam_response()` used an incorrect approximation
for the Bessel function J₁(x):

```python
# WRONG: This is not J₁(x)
resp = (2 * (np.sin(x) - x * np.cos(x)) / (x * x)) ** 2
```

**Impact**: The primary beam response was inverted - sources far from the field
center got HIGHER response than sources near the center. This made far-away
calibrators appear better than nearby ones.

**Fix**: Use `scipy.special.j1()` for the correct Bessel function:

```python
# CORRECT: Using scipy's proper Bessel function
from scipy.special import j1
resp = (2.0 * j1(x) / x) ** 2
```

## Verification

After fixes:

- `1911+161` correctly found at field 19 (0.03° separation)
- Primary beam response: field 19 = 0.9996, field 0 = 0.7007 (correct ordering)
- All calibrators now visible regardless of flux band availability

## Files Changed

- `backend/src/dsa110_contimg/calibration/catalogs.py`
- `backend/src/dsa110_contimg/calibration/beam_model.py`

## Documentation Updated

- `docs/guides/pipeline-walkthrough-absurd-to-calibration.md` - Added Phase 3
  workflow for calibrator MS creation
- `docs/guides/mosaicking.md` - Corrected Airy model formula
- `docs/guides/catalog-overview.md` - Updated function notes
- `backend/src/dsa110_contimg/calibration/README.md` - Added primary beam model
  section
