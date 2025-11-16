# Refactoring Recommendations Based on Lizard Complexity Metrics

## Summary

After analyzing the Codacy Lizard complexity warnings, several methods exceed
recommended complexity thresholds. This document outlines specific refactoring
opportunities to improve code maintainability.

## Critical Issues (Complexity > 15)

### 1. `create_mosaic_centered_on_calibrator` (orchestrator.py)

- **Complexity**: 61 (limit: 8) ⚠️ **CRITICAL**
- **Lines**: 371 (limit: 50)
- **Parameters**: 7 (limit: 8)

**Current Issues:**

- Single method handles: validation, MS file management, dry-run logic, workflow
  orchestration, and publication waiting
- Deeply nested conditionals (dry-run vs. normal execution)
- Multiple responsibilities violate Single Responsibility Principle

**Recommended Refactoring:**

```python
# Extract validation logic
def _validate_mosaic_plan(self, calibrator_name, start_time, end_time, ...):
    """Run comprehensive validation checks."""
    # Move all validation logic here (lines 808-1006)
    pass

# Extract dry-run logic
def _execute_dry_run(self, calibrator_name, window_info, ...):
    """Execute dry-run mode with validation."""
    # Move dry-run specific logic here
    pass

# Extract workflow execution
def _execute_mosaic_workflow(self, group_id, ms_paths, ...):
    """Execute the actual mosaic creation workflow."""
    # Move workflow processing logic here
    pass

# Main method becomes orchestrator
def create_mosaic_centered_on_calibrator(self, ...):
    """Orchestrate mosaic creation."""
    window_info = self.find_transit_centered_window(...)
    if dry_run:
        return self._execute_dry_run(...)
    else:
        return self._execute_mosaic_workflow(...)
```

**Expected Impact:**

- Reduce main method complexity from 61 to ~8-10
- Reduce main method length from 371 to ~50-80 lines
- Improve testability (each extracted method can be tested independently)

---

### 2. `list_available_transits` (calibrator_ms_service.py)

- **Complexity**: 22 (limit: 8) ⚠️ **HIGH**
- **Lines**: 157 (limit: 50)

**Current Issues:**

- Handles multiple concerns: time range calculation, database queries, transit
  finding, MS existence checking
- Complex nested loops and conditionals

**Recommended Refactoring:**

```python
def _calculate_time_range(self, max_days_back):
    """Calculate time range for transit search."""
    # Extract time range logic
    pass

def _find_transits_in_range(self, calibrator_name, start_time, end_time):
    """Find all transits in time range."""
    # Extract transit finding logic
    pass

def _enrich_transit_with_data(self, transit_info, groups):
    """Enrich transit info with HDF5 group data."""
    # Extract data enrichment logic
    pass

def list_available_transits(self, ...):
    """List available transits (orchestrator)."""
    time_range = self._calculate_time_range(...)
    transits = self._find_transits_in_range(...)
    return self._enrich_transit_with_data(transits, ...)
```

**Expected Impact:**

- Reduce complexity from 22 to ~6-8 per method
- Reduce main method length from 157 to ~40-50 lines

---

### 3. `index_hdf5_files` (hdf5_index.py)

- **Complexity**: 24 (limit: 8) ⚠️ **HIGH**
- **Lines**: 121 (limit: 50)

**Current Issues:**

- Handles file scanning, parsing, database operations, and batch processing
- Multiple nested try-except blocks

**Recommended Refactoring:**

```python
def _scan_hdf5_files(self, input_dir):
    """Scan directory for HDF5 files."""
    # Extract file scanning logic
    pass

def _parse_hdf5_metadata(self, file_path):
    """Parse metadata from HDF5 filename."""
    # Extract parsing logic
    pass

def _update_database_batch(self, conn, batch, indexed_at):
    """Update database with batch of files."""
    # Extract database update logic
    pass

def index_hdf5_files(self, ...):
    """Index HDF5 files (orchestrator)."""
    files = self._scan_hdf5_files(...)
    batches = self._group_into_batches(files)
    for batch in batches:
        self._update_database_batch(conn, batch, ...)
```

**Expected Impact:**

- Reduce complexity from 24 to ~6-8 per method
- Reduce main method length from 121 to ~40-50 lines

---

## Medium Priority Issues (Complexity 9-15)

### 4. `find_transit` (calibrator_ms_service.py)

- **Complexity**: 13 (limit: 8)
- **Lines**: 157 (limit: 50)

**Recommended Refactoring:**

- Extract transit calculation logic
- Extract MS file checking logic
- Simplify conditional chains

### 5. `generate_from_transit` (calibrator_ms_service.py)

- **Complexity**: 13 (limit: 8)
- **Lines**: 189 (limit: 50)
- **Parameters**: 11 (limit: 8) ⚠️

**Recommended Refactoring:**

- Use a configuration dataclass to reduce parameters
- Extract validation logic
- Extract conversion workflow

### 6. `_process_batch` (hdf5_index.py)

- **Complexity**: 11 (limit: 8)
- **Lines**: 76 (limit: 50)

**Recommended Refactoring:**

- Extract database update logic
- Extract error handling logic
- Simplify conditional chains

---

## Low Priority Issues (Complexity 8-10)

### 7. `_validate_inputs` (calibrator_ms_service.py)

- **Complexity**: 9 (limit: 8)

**Recommendation:** Minor refactoring - extract validation checks into separate
methods.

### 8. `_load_radec` (calibrator_ms_service.py)

- **Complexity**: 10 (limit: 8)

**Recommendation:** Extract catalog loading logic into separate methods.

---

## File-Level Recommendations

### Large Files (>500 lines)

1. **`hdf5_orchestrator.py`** (1441 lines)
   - Consider splitting into multiple modules:
     - `hdf5_reader.py` - File reading and parsing
     - `hdf5_converter.py` - Conversion logic
     - `hdf5_orchestrator.py` - Orchestration only

2. **`orchestrator.py`** (1463 lines)
   - Consider splitting:
     - `mosaic_orchestrator.py` - Main orchestration
     - `mosaic_validator.py` - Validation logic
     - `mosaic_workflow.py` - Workflow execution

3. **`calibrator_ms_service.py`** (1148 lines)
   - Consider splitting:
     - `calibrator_finder.py` - Transit finding
     - `calibrator_converter.py` - MS conversion
     - `calibrator_service.py` - Service orchestration

---

## Implementation Priority

### Phase 1 (High Impact, Low Risk)

1. Extract validation logic from `create_mosaic_centered_on_calibrator`
2. Extract dry-run logic from `create_mosaic_centered_on_calibrator`
3. Refactor `list_available_transits` into smaller methods

### Phase 2 (Medium Impact, Medium Risk)

4. Refactor `index_hdf5_files` into smaller methods
5. Refactor `find_transit` and `generate_from_transit`
6. Use dataclasses to reduce parameter counts

### Phase 3 (Long-term, High Risk)

7. Split large files into multiple modules
8. Comprehensive refactoring of workflow orchestration

---

## Benefits of Refactoring

1. **Maintainability**: Smaller, focused methods are easier to understand and
   modify
2. **Testability**: Isolated methods can be unit tested independently
3. **Reusability**: Extracted logic can be reused in other contexts
4. **Debugging**: Easier to identify and fix issues in smaller methods
5. **Code Review**: Smaller methods are easier to review and approve

---

## Notes

- All refactoring should maintain backward compatibility
- Comprehensive test coverage should be maintained/added
- Refactoring should be done incrementally, one method at a time
- Each refactoring should be validated with Codacy after completion
