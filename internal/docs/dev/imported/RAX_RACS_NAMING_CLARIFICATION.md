# RAX vs RACS Naming Clarification

## Date: 2025-11-10

## Issue

The codebase uses "RAX" as a catalog identifier, but research indicates this likely refers to **RACS (Rapid ASKAP Continuum Survey)**, not a separate "RAX" survey.

## Research Findings

### RAX (Radio Aurora eXplorer)
- **Type:** CubeSat mission (not a radio survey)
- **Purpose:** Ionospheric research using radar techniques
- **Not:** An astronomical radio source catalog

### RACS (Rapid ASKAP Continuum Survey)
- **Type:** Large-scale radio continuum survey
- **Telescope:** ASKAP (Australian Square Kilometre Array Pathfinder)
- **Purpose:** Astronomical radio source catalog
- **Specifications:**
  - Sky coverage: ~90% of sky (declination -80° to +48°)
  - Frequency bands: 887.5 MHz (low), 1367.5 MHz (mid), 1655.5 MHz (high)
  - Resolution: 8-25 arcsec (depending on band)
  - Sensitivity: ~200 µJy PSF⁻¹
  - Sources: ~2-3 million sources

## Current Codebase Usage

The codebase uses "RAX" in:
- `src/dsa110_contimg/catalog/build_rax_strip_cli.py`
- `src/dsa110_contimg/catalog/builders.py::build_rax_strip_db()`
- `src/dsa110_contimg/pipeline/stages_impl.py::CatalogSetupStage`
- Catalog query system (`catalog_type="rax"`)

## Recommendation

### Option 1: Update to RACS (Recommended)
- Rename "RAX" references to "RACS" throughout codebase
- Update CLI scripts, function names, and catalog identifiers
- More accurate and aligns with actual survey name

### Option 2: Document as Alias
- Keep "RAX" as a codebase alias for RACS
- Document that "RAX" refers to RACS
- Add comments/clarifications in code

### Option 3: Support Both
- Support both "RAX" and "RACS" as catalog identifiers
- Map "RAX" → "RACS" internally
- Maintain backward compatibility

## Action Items

1. **Verify:** Confirm with team whether "RAX" intentionally refers to RACS or if there's a different survey
2. **Document:** Update documentation to clarify RAX/RACS relationship
3. **Consider:** Whether to rename "RAX" to "RACS" for clarity
4. **Update:** Catalog comparison document with RACS specifications

## Related Files

- `docs/reference/RADIO_SURVEY_CATALOG_COMPARISON.md` - Survey comparison (updated with RACS)
- `src/dsa110_contimg/catalog/build_rax_strip_cli.py` - RAX CLI script
- `src/dsa110_contimg/catalog/builders.py` - RAX builder function
- `src/dsa110_contimg/catalog/query.py` - Catalog query system

## Status

✅ **DOCUMENTED** - RAX/RACS naming clarified in documentation.

Awaiting confirmation on whether to rename "RAX" to "RACS" or maintain as alias.

