# CASA C++ Shutdown Error in pytest

**Status:** ✅ Resolved  
**Date Fixed:** November 29, 2025  
**Affects:** Unit tests that import CASA modules (casatools, casacore)

---

## Symptom

After running pytest, the test suite would pass but then crash with:

```
terminate called after throwing an instance of 'std::runtime_error'
  what():  casatools::get_state( ) called after shutdown initiated
Aborted (core dumped)
```

Exit code was 134 (SIGABRT) even though all tests passed.

---

## Root Cause

CASA's C++ backend (casatools) starts a gRPC service when imported. During
Python's normal shutdown sequence (atexit handlers, module cleanup), the C++
destructors try to access internal CASA state that has already been marked as
"shutting down."

The issue is exacerbated in pytest because:

1. Tests use `unittest.mock.patch.dict('sys.modules', ...)` to mock dependencies
2. This temporarily adds CASA modules during test execution
3. When the patch context exits, modules are removed from `sys.modules`
4. But the C++ shared libraries remain loaded in memory
5. During Python shutdown, C++ destructors run and throw the exception

### Why Standard Cleanup Didn't Work

Several approaches were tried and failed:

| Approach                         | Why It Failed                                              |
| -------------------------------- | ---------------------------------------------------------- |
| `atexit.register(cleanup)`       | Runs too late - CASA already in shutdown state             |
| `gc.collect()` + clear modules   | C++ code still in memory even after Python modules cleared |
| `casatools.ctsys.shutdown()`     | Triggers the error immediately if called explicitly        |
| `casatools.ctsys.remove_service` | Doesn't actually stop the gRPC service                     |
| Signal handler for SIGABRT       | C++ `terminate()` bypasses Python signal handling          |

---

## Solution

The fix is implemented in `backend/tests/conftest.py`:

### 1. Track CASA Imports During Tests

```python
_casa_cpp_loaded = False

def _check_casa_loaded():
    """Check if CASA C++ modules are currently loaded."""
    return any('casatools' in m or '__casac__' in m for m in sys.modules)

def pytest_runtest_call(item):
    """Check for CASA modules after each test runs."""
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True

def pytest_runtest_teardown(item, nextitem):
    """Double-check after each test completes."""
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True
```

### 2. Use `os._exit(0)` for Clean Shutdown

```python
def pytest_sessionfinish(session, exitstatus):
    """Skip Python's normal shutdown if CASA was loaded."""
    global _casa_cpp_loaded
    
    _cleanup_casa()  # Clear modules from sys.modules
    
    if exitstatus == 0 and _casa_cpp_loaded:
        # Skip Python's normal shutdown to avoid C++ destructor issues
        os._exit(0)
```

### Why This Works

- `os._exit(0)` terminates the process immediately without running atexit
  handlers or C++ destructors
- Only used when tests pass (exitstatus == 0) so failures are properly reported
- Only used when CASA was actually imported during the test session
- Tests that don't use CASA show full pytest output ("X passed in Y.Zs")

---

## Verification

```bash
# Run tests - should exit cleanly with no error
cd /data/dsa110-contimg/backend
conda activate casa6
python -m pytest tests/unit/ -q
# Output: ........ [100%]
# Exit code: 0

# Test failures are still reported
python -m pytest tests/unit/test_routes.py -q
# Output: 14 passed in 0.60s (full output shown for non-CASA tests)

# Failed tests still show proper exit code
python -m pytest tests/unit/ -k "nonexistent" 
# Exit code: 5 (no tests collected)
```

---

## Files Modified

- `backend/tests/conftest.py` - Added CASA tracking and clean shutdown logic

---

## Related Issues

- [CASA Issue Tracker](https://open-jira.nrao.edu/) - Known issue in CASA 6.x
- This is a common problem in radio astronomy pipelines using CASA

---

## Alternative Approaches (Not Recommended)

### Suppressing the Error Output

You could redirect stderr at the shell level:

```bash
python -m pytest tests/unit/ 2>&1 | grep -v "casatools::get_state"
```

**Not recommended** because it hides the exit code and masks real errors.

### pytest-forked Plugin

Running each test in a subprocess would avoid the issue:

```bash
pip install pytest-forked
python -m pytest tests/unit/ --forked
```

**Not recommended** because:
- Significantly slower (subprocess per test)
- Breaks fixtures that need shared state
- Overkill for this specific issue

---

## Notes

- The `os._exit(0)` approach is safe because we only use it after confirming all
  tests passed
- If you add new test fixtures that need cleanup at session end, ensure they run
  before `pytest_sessionfinish`
- This fix has no impact on tests that don't import CASA modules
