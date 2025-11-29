# Troubleshooting Index

**Last Updated:** November 29, 2025

This is the single source of truth for all known issues, fixes, and
troubleshooting guides in the DSA-110 Continuum Imaging Pipeline.

---

## Quick Reference

| Issue | Status | Category | Guide |
|-------|--------|----------|-------|
| [Docker WSClean Hang](#docker-wsclean-hang) | 🔴 Open | Backend/Imaging | [docker-wsclean.md](docker-wsclean.md) |
| [Image Metadata Not Populated](#image-metadata-not-populated) | 🔴 Open | Database | [known-issues/image-metadata-population.md](known-issues/image-metadata-population.md) |
| [MS Permission Errors](#ms-permission-errors) | ✅ Resolved | Backend/CASA | [resolved/ms-permission-errors.md](resolved/ms-permission-errors.md) |
| [Frontend Restart Required](#frontend-restart-required) | ✅ Resolved | Frontend | [resolved/frontend-restart-needed.md](resolved/frontend-restart-needed.md) |

---

## Open Issues

### Docker WSClean Hang

**Severity:** HIGH  
**Status:** 🔴 Open (Workaround Available)  
**Affects:** NVSS seeding, Docker-based WSClean `-predict` operations

Docker WSClean `-predict` operations hang at "Cleaning up temporary files..."
and never complete. Timeouts don't trigger because the hang occurs at the
Docker/kernel level.

**Workaround:** Disable NVSS seeding (`use_nvss_seeding=False`)

**Full Documentation:** [docker-wsclean.md](docker-wsclean.md)

---

### Image Metadata Not Populated

**Severity:** HIGH  
**Status:** 🔴 Open  
**Affects:** Image filtering, database queries

Database images have `noise_jy`, `center_ra_deg`, `center_dec_deg` set to NULL,
causing noise filtering to fail and declination filtering to be slow.

**Impact:**
- Noise filtering returns no results
- Declination filtering requires reading FITS files (slow)

**Full Documentation:** [known-issues/image-metadata-population.md](known-issues/image-metadata-population.md)

---

## Resolved Issues

### MS Permission Errors

**Severity:** MEDIUM  
**Status:** ✅ Resolved  
**Resolution Date:** November 2025

CASA tasks failed with "Permission denied" errors on Measurement Set files
created with root ownership.

**Solution:** Automated permission fixing integrated into `selfcal.py` and
manual script available.

**Full Documentation:** [resolved/ms-permission-errors.md](resolved/ms-permission-errors.md)

---

### Frontend Restart Required

**Severity:** LOW  
**Status:** ✅ Resolved  
**Resolution Date:** November 2025

Frontend dev server needed restart to pick up `.env.development` changes.

**Solution:** Restart frontend dev server or modify API client directly.

**Full Documentation:** [resolved/frontend-restart-needed.md](resolved/frontend-restart-needed.md)

---

## Informational Reports

These documents provide audit results and analysis, not issue resolutions:

- [frontend_api_audit_report.md](frontend_api_audit_report.md) - API prefix audit (all calls correct)

---

## How to Add New Issues

1. **Create issue document** in appropriate location:
   - Active issues: `troubleshooting/` or `troubleshooting/known-issues/`
   - Resolved issues: `troubleshooting/resolved/`

2. **Use standard format:**
   ```markdown
   # Issue Title
   
   **Date:** YYYY-MM-DD  
   **Severity:** HIGH | MEDIUM | LOW  
   **Status:** 🔴 Open | 🟡 In Progress | ✅ Resolved
   
   ## Problem
   [Description]
   
   ## Impact
   [What's affected]
   
   ## Solution / Workaround
   [Resolution or mitigation]
   ```

3. **Update this index** with a link to the new document

---

## Related Documentation

- [How-To Guides](../how-to/) - Step-by-step procedures
- [Architecture](../architecture/) - System design documentation
- [Reference](../reference/) - API and configuration reference
