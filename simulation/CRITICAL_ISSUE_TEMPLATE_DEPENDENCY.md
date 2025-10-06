# CRITICAL ISSUE: Template UVH5 File Dependency

## Problem Summary

The `make_synthetic_uvh5.py` script **cannot generate synthetic data from scratch**. Despite having `--layout-meta` and `--telescope-config` options, the script still requires a template UVH5 file to exist.

## Root Cause

**Line 322-328** in `make_synthetic_uvh5.py`:
```python
uv_template = UVData()
uv_template.read(
    args.template,
    file_type='uvh5',
    run_check=False,
    run_check_acceptability=False,
    strict_uvw_antpos_check=False,
)
```

The script reads the template file unconditionally, then uses it to:
1. Extract antenna positions, baselines, and array geometry
2. Build time arrays (Line 330)
3. Build UVW coordinates (Line 333)
4. Scaffold subband metadata (Lines 336-351)

## Impact

- **Phase 1 improvements BLOCKED**: Cannot test basic_generation.sh without existing data
- **Documentation misleading**: README claims script generates from scratch
- **Circular dependency**: Need real UVH5 file to generate synthetic UVH5 files

## Error Encountered

```bash
$ ./simulation/examples/basic_generation.sh
FileNotFoundError: Unable to synchronously open file (name = '/workspaces/dsa110-contimg/output/ms/test_8subbands_concatenated.hdf5', errno = 2, error message = 'No such file or directory')
```

## Required Fix

**Option 1: Template-Free Mode** (RECOMMENDED)
Refactor to build `UVData` from scratch when template not provided:
- Use `pipeline/utils/antpos.py` to get antenna positions
- Build baseline array from antenna pairs
- Construct empty UVData object with proper dimensions
- Populate metadata from `reference_layout.json` + `telescope.yaml`

**Option 2: Provide Reference Template**
- Include a minimal reference UVH5 file in the repository
- Document that template is required
- Update README to reflect limitation

**Option 3: Hybrid Approach**
- Check if template exists
- If not, build UVData from scratch using Option 1
- If yes, use template for scaffolding

## Files Requiring Changes

1. `simulation/make_synthetic_uvh5.py`:
   - Lines 310-360: Refactor template reading to be optional
   - Add `build_uvdata_from_scratch()` function
   - Update `main()` to handle both modes

2. `simulation/README.md`:
   - Add warning about template dependency (short term)
   - Or document template-free mode (after fix)

3. `simulation/examples/basic_generation.sh`:
   - Remove/comment `--template` argument (after fix)

4. `.github/copilot-instructions.md`:
   - Document this limitation until fixed
   - Add guidance for future refactoring

## Temporary Workaround

**None available** - simulation module is currently non-functional without existing DSA-110 observation data.

## Next Steps

1. **URGENT**: Inform user of this blocking issue
2. Decide on fix approach (Option 1 vs 2 vs 3)
3. Implement chosen solution
4. Update Phase 1 deliverables to reflect actual state
5. Re-test example scripts after fix

## Timeline Estimate

- **Option 1** (template-free): 2-3 hours implementation + testing
- **Option 2** (provide template): 30 min (if template available)
- **Option 3** (hybrid): 3-4 hours implementation + testing

## Related Files

- `simulation/make_synthetic_uvh5.py` (lines 310-360)
- `simulation/config/reference_layout.json` (frequency metadata)
- `simulation/pyuvsim/telescope.yaml` (telescope config)
- `pipeline/pipeline/utils/antpos.py` (antenna positions)
- `simulation/README.md` (misleading documentation)
- `simulation/PHASE1_SUMMARY.md` (incomplete metrics)

---

**Discovered**: 2025-10-06  
**Status**: BLOCKING  
**Priority**: CRITICAL
