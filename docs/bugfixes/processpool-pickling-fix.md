# ProcessPoolExecutor Pickling Error Fix

## Issue
The `_preprocess_subband_worker` method was originally an instance method of the `UnifiedHDF5Converter` class. When attempting to submit it to a `ProcessPoolExecutor`, Python's multiprocessing module requires pickling (serialization) of the callable object. Instance methods cannot be pickled by default, causing a `PicklingError` or `TypeError` at runtime.

## Root Cause
`ProcessPoolExecutor` uses multiprocessing, which requires serialization of callable objects. Instance methods reference `self`, which cannot be pickled without special handling. The code attempted to submit `self._preprocess_subband_worker` directly to the executor.

## Solution
Refactored `_preprocess_subband_worker` from an instance method to a **module-level function**:

1. **Moved function outside class**: The function is now defined at module level (line 789), not as a class method
2. **Updated function signature**: Changed from `def _preprocess_subband_worker(self, ...)` to `def _preprocess_subband_worker(filepath, ...)`
3. **Updated executor call**: Changed from `executor.submit(self._preprocess_subband_worker, ...)` to `executor.submit(_preprocess_subband_worker, ...)`
4. **Removed orphaned code**: Cleaned up incorrectly indented code that was causing syntax errors

## Code Changes

### Before (Broken)
```python
class UnifiedHDF5Converter:
    def _process_subbands_parallel(self, ...):
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(self._preprocess_subband_worker, *args): i  # ❌ Pickling error
                ...
            }
    
    def _preprocess_subband_worker(self, ...):  # ❌ Instance method
        ...
```

### After (Fixed)
```python
class UnifiedHDF5Converter:
    def _process_subbands_parallel(self, ...):
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(_preprocess_subband_worker, *args): i  # ✅ Module-level function
                ...
            }

# Module-level function (can be pickled)
def _preprocess_subband_worker(
    filepath: str,
    ra: Optional[u.Quantity],
    ...
) -> Dict:
    """Worker function for preprocessing a single sub-band.
    
    Module-level function (not instance method) to allow pickling for ProcessPoolExecutor.
    """
    ...
```

## Verification
- ✅ File compiles without syntax errors: `/opt/miniforge/envs/casa6/bin/python -m py_compile unified_converter.py`
- ✅ Function is module-level (not indented as class method)
- ✅ Executor correctly references module-level function
- ✅ All required parameters are passed as function arguments (not accessed via `self`)

## Files Modified
- `archive/legacy/conversion_pipeline/conversion/unified_converter.py`
  - Moved `_preprocess_subband_worker` to module level (line 789)
  - Updated executor.submit call (line 734)
  - Removed orphaned code causing syntax errors (lines 868-900)

## Related Issues
- ProcessPoolExecutor requires picklable callables
- Instance methods cannot be pickled without special handling (using `functools.partial` or `multiprocessing.Manager`)
- Module-level functions are the simplest solution for ProcessPoolExecutor workers

## Testing Recommendations
When testing the parallel sub-band processing:
1. Verify worker processes start successfully (no pickling errors)
2. Check that all sub-bands are processed correctly
3. Verify data integrity in the output Measurement Set
4. Monitor for any multiprocessing-related errors in logs
