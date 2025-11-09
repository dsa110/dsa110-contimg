# Moffat Rotation - Deferred Decision

**Date:** 2025-01-27  
**Status:** DEFERRED  
**Decision:** To be added after validating more fundamental stages

---

## Decision Summary

Moffat rotation support has been **deferred** to focus on validating more fundamental stages of the pipeline first.

---

## Current State

### What Works Now
- ✅ **Gaussian fitting** - Supports rotation (elliptical sources)
- ✅ **Moffat fitting** - Works for circular sources
- ✅ **Region mask integration** - Complete and verified

### Known Limitation
- ⚠️ **Moffat fitting** - Circular only (no rotation support)
- ⚠️ For elliptical sources, users should use Gaussian

### Workaround
- Use **Gaussian** for elliptical sources (already works)
- Use **Moffat** for circular/extended sources
- Document limitation clearly

---

## Context

### Beam Shape Analysis
- **Beam ratio:** ~3.2:1 (highly elliptical)
- **Sources appear:** Elliptical (due to beam convolution)
- **Current solution:** Gaussian handles elliptical sources correctly

### Science Goals
- **ESE detection:** Uses forced photometry (not fitting)
- **Interactive analysis:** Gaussian works for elliptical sources
- **Moffat rotation:** Feature parity, not critical functionality

---

## Rationale for Deferral

### 1. Focus on Core Functionality
- Validate fundamental stages first
- Ensure core features work correctly
- Add polish features later

### 2. Current Tools Are Sufficient
- Gaussian already handles elliptical sources
- Moffat works for circular sources
- Users have working tools for all cases

### 3. Resource Prioritization
- Medium-high effort (4-8 hours)
- Medium value (feature parity)
- Better to validate core features first

### 4. Can Be Added Later
- No blocking dependencies
- Can be added when needed
- Low risk of deferral

---

## Documentation

### User-Facing Documentation
- Document that Moffat is circular-only
- Recommend Gaussian for elliptical sources
- Note that Moffat rotation will be added later

### Developer Documentation
- Implementation approach documented in roadmap
- Can be implemented when prioritized
- No technical blockers

---

## When to Revisit

### Triggers for Re-evaluation
1. **User requests** - If users frequently need Moffat for elliptical sources
2. **Core validation complete** - After fundamental stages validated
3. **Extended source analysis** - If extended elliptical sources become important
4. **Feature parity** - When polishing for production release

### Implementation Readiness
- ✅ Implementation approach documented
- ✅ Technical feasibility confirmed
- ✅ No blocking dependencies
- ✅ Can be added quickly when prioritized

---

## Next Steps

1. **Document limitation** - Update user docs to note Moffat is circular-only
2. **Recommend Gaussian** - For elliptical sources in documentation
3. **Focus on Priority 3** - Residual Visualization (more universally useful)
4. **Revisit later** - After core validation complete

---

## Related Documents

- `docs/analysis/PHASE2_LIMITATIONS_ROADMAP.md` - Full roadmap
- `docs/analysis/MOFFAT_ROTATION_VALUE.md` - Value analysis
- `docs/analysis/MOFFAT_ROTATION_ESE_SCIENCE.md` - ESE science context
- `docs/analysis/MOFFAT_ROTATION_UNRESOLVED_SOURCES.md` - Unresolved sources analysis

---

**Status:** DEFERRED - To be added after validating more fundamental stages

