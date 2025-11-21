# CASA pkg_resources Warning - Quick Fix

## ✅ Status: Fixed (Warning Suppressed)

The warning you were seeing:

```
pkg_resources is deprecated as an API... pin to Setuptools<81
```

Has been mitigated with:

1. **Warning suppression** in `src/dsa110_contimg/api/routes.py`
2. **Setuptools pinned** to 80.9.0 (below 81)
3. **Documentation** in `docs/dev/casa_pkg_resources_warning.md`

## Why This Warning Appeared

- **Source:** CASA's own code (not ours)
- **Issue:** CASA uses deprecated `pkg_resources` API
- **Impact:** None (cosmetic warning only)

## What We Did

✅ Suppressed the warning at API startup  
✅ Pinned setuptools to prevent future issues  
✅ Documented for future reference

## You're All Set!

The warning will no longer appear when starting the API or running scripts.

---

**Details:** See `docs/dev/casa_pkg_resources_warning.md`
