# ft() CASA Documentation Verification

**Date:** 2025-11-05  
**Status:** Documentation Check Complete

---

## CASA ft() Task Documentation

### Official Documentation

**CASA Documentation URL:** https://casadocs.readthedocs.io/en/v6.6.0/api/tt/casatasks.imaging.ft.html

### Key Findings from Official CASA Documentation (Verified via Ref MCP Tool)

**Function Signature:**
```python
ft(vis, field='', spw='', model='', nterms=1, reffreq='', complist='', incremental=False, usescratch=False)
```

**Complete Parameter List:**
1. `vis` (path) - Name of input visibility file
2. `field` (string='') - Select field using field id(s) or field name(s)
3. `spw` (string='') - Select spectral window/channels
4. `model` (variant='') - Name of input model image(s)
5. `nterms` (int=1) - Number of terms used to model the sky frequency dependence
6. `reffreq` (string='') - Reference frequency (required if nterms != 1)
7. `complist` (string='') - Name of component list
8. `incremental` (bool=False) - Add to the existing model visibility?
9. `usescratch` (bool=False) - If True, predicted visibility is stored in MODEL_DATA column

**NO `phasecenter` parameter exists** ✓ **CONFIRMED FROM OFFICIAL DOCS**

1. **`ft()` does NOT have a `phasecenter` parameter** ✓ **OFFICIALLY CONFIRMED**
   - Official CASA documentation shows complete parameter list
   - `phasecenter` is NOT in the function signature
   - Perplexity search also confirmed: "The CASA task **ft** does **not** have a direct **phasecenter** parameter"
   - This definitively confirms that we cannot pass `phasecenter` to `ft()` to override the phase center

2. **Recommended CASA Workflow**
   - Use **phaseshift** to adjust the MS phase center (we already do this)
   - Use **ft** to Fourier transform the model image, but without a phasecenter parameter
   - Phase center adjustments are done separately via **phaseshift**, not in `ft()`

3. **How `ft()` Determines Phase Center**
   - According to our investigation notes: "ft() uses 'phase center from first field'"
   - Documentation does NOT specify whether it uses `REFERENCE_DIR` or `PHASE_DIR`
   - Documentation does NOT specify how it handles phase center after rephasing
   - **Our tests showed:** `ft()` doesn't use `REFERENCE_DIR` or `PHASE_DIR` correctly after rephasing

4. **How `ft()` Handles Phase Center**
   - Documentation states: "ft converts a source model or a components list into model visibilities"
   - Documentation does NOT explain how `ft()` determines phase center
   - Documentation does NOT mention `REFERENCE_DIR` or `PHASE_DIR`
   - **Our empirical tests showed:** `ft()` doesn't use `REFERENCE_DIR` or `PHASE_DIR` correctly after rephasing

---

## Conclusion

**We cannot fix `ft()` by passing a `phasecenter` parameter because it doesn't exist.**

Therefore:
- ✓ **Manual calculation (`use_manual=True`) is the correct solution**
- ✓ The code change to `use_manual=True` is appropriate
- ✗ Testing `phasecenter` parameter would fail (it doesn't exist)

---

## Next Steps

1. **Keep the `use_manual=True` fix** - This is the correct solution
2. **Document why manual calculation is needed** - `ft()` doesn't support explicit phase center
3. **Proceed with MODEL_DATA recalculation** - Use the manual calculation method

---

## References

- **Official CASA ft() Documentation:** https://casadocs.readthedocs.io/en/v6.6.0/api/tt/casatasks.imaging.ft.html
  - Retrieved via Ref MCP tool - official CASA documentation
  - Function signature confirms NO `phasecenter` parameter
- **Perplexity Search Results:** Confirmed `ft()` does NOT support `phasecenter` parameter
- **Our investigation notes:** `docs/reports/MODEL_DATA_PHASE_STRUCTURE_INVESTIGATION.md`
- **CASA phaseshift Documentation:** https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.manipulation.phaseshift.html

