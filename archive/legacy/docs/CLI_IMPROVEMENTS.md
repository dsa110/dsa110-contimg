# CLI Architecture Improvements

## Executive Summary

This document analyzes the CLI codebase in `/src/dsa110_contimg/` (particularly modules we recently edited) and proposes improvements to make the code more elegant, maintainable, and user-friendly.

## Current State Analysis

### Strengths

1. **Good separation in `conversion/cli.py`**: Clean delegator pattern using subcommands
2. **Modular utilities**: New modules (`qa.py`, `export.py`, `nvss_tools.py`) are well-organized
3. **Consistent subcommand pattern**: All CLIs use `argparse` subparsers

### Issues Identified

#### 1. Code Duplication

**CASA Log Directory Setup** (repeated in 5+ files):
```python
# Repeated in: calibration/cli.py, imaging/cli.py, pointing/cli.py, conversion/cli.py
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    casa_log_dir = derive_casa_log_dir()
    os.chdir(str(casa_log_dir))
except Exception:
    pass
```

**Precondition Checks** (repeated validation patterns):
- File/directory existence and permissions
- MS validation (readable, not empty, required columns)
- Reference antenna validation
- Field validation
- Disk space checks

**Argument Parsing Patterns**:
- Repeated argument definitions for similar concepts (e.g., MS path, field selection)
- Similar flag patterns across modules

#### 2. Large Files

- `calibration/cli.py`: 852 lines (complex, mixed validation + execution)
- `imaging/cli.py`: 956 lines (complex, mixed validation + execution)
- `hdf5_orchestrator.py`: 964 lines (orchestration + validation)

#### 3. Inconsistent Patterns

- Some CLIs validate early (`calibration/cli.py`), others validate late
- Different error message formats
- Inconsistent use of logging vs print statements

#### 4. User Experience Issues

- Long help output (many flags, some poorly documented)
- Error messages sometimes technical rather than actionable
- No unified way to show progress across operations

## Proposed Improvements

### 1. Create Shared CLI Utilities Module

**File**: `src/dsa110_contimg/utils/cli_helpers.py`

```python
"""
Shared utilities for CLI modules to reduce duplication and ensure consistency.
"""

from contextmanager import contextmanager
from pathlib import Path
from typing import Optional, List
import os
import logging

def setup_casa_environment() -> None:
    """Configure CASA logging directory. Call at the start of CLI main() functions."""
    try:
        from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
        casa_log_dir = derive_casa_log_dir()
        os.chdir(str(casa_log_dir))
    except Exception:
        pass  # Best-effort; continue if setup fails


@contextmanager
def casa_log_environment():
    """Context manager for CASA operations that need log directory."""
    log_dir = derive_casa_log_dir()
    old_cwd = os.getcwd()
    try:
        os.chdir(log_dir)
        yield log_dir
    finally:
        os.chdir(old_cwd)


def validate_file_path(path: str, must_exist: bool = True, 
                       must_readable: bool = True) -> Path:
    """Validate a file path with clear error messages."""
    p = Path(path)
    if must_exist and not p.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    if must_readable and not os.access(path, os.R_OK):
        raise PermissionError(f"File is not readable: {path}")
    return p


def validate_directory(path: str, must_exist: bool = True,
                      must_readable: bool = False, 
                      must_writable: bool = False) -> Path:
    """Validate a directory path with clear error messages."""
    p = Path(path)
    if must_exist:
        if not p.exists():
            raise FileNotFoundError(f"Directory does not exist: {path}")
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
    if must_readable and not os.access(path, os.R_OK):
        raise PermissionError(f"Directory is not readable: {path}")
    if must_writable and not os.access(path, os.W_OK):
        raise PermissionError(f"Directory is not writable: {path}")
    return p


def validate_ms(ms_path: str, check_empty: bool = True,
                check_columns: Optional[List[str]] = None) -> None:
    """Validate a Measurement Set with clear error messages."""
    from casacore.tables import table
    
    validate_file_path(ms_path, must_exist=True, must_readable=True)
    
    try:
        with table(ms_path, readonly=True) as tb:
            if check_empty and tb.nrows() == 0:
                raise ValueError(f"MS is empty: {ms_path}")
            
            if check_columns:
                missing = [c for c in check_columns if c not in tb.colnames()]
                if missing:
                    raise ValueError(
                        f"MS missing required columns: {missing}. "
                        f"Path: {ms_path}"
                    )
    except RuntimeError:
        raise
    except Exception as e:
        raise ValueError(f"MS is not readable: {ms_path}. Error: {e}") from e


def add_common_ms_args(parser: argparse.ArgumentParser, 
                       ms_required: bool = True) -> None:
    """Add common MS-related arguments to a parser."""
    parser.add_argument(
        "--ms", required=ms_required,
        help="Path to Measurement Set"
    )


def add_common_field_args(parser: argparse.ArgumentParser) -> None:
    """Add common field selection arguments."""
    parser.add_argument(
        "--field", default="",
        help="Field selection (name, index, or range)"
    )


def add_common_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add common logging arguments."""
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level"
    )


def configure_logging_from_args(args) -> logging.Logger:
    """Configure logging based on CLI arguments."""
    level = logging.DEBUG if getattr(args, 'verbose', False) else logging.INFO
    if hasattr(args, 'log_level'):
        level = getattr(logging, args.log_level.upper(), level)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)
```

### 2. Create Validation Module

**File**: `src/dsa110_contimg/utils/validation.py`

```python
"""
Centralized validation functions for CLI and pipeline operations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import shutil
import numpy as np
from casacore.tables import table


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_ms_for_calibration(ms_path: str, field: Optional[str] = None,
                                 refant: Optional[str] = None) -> Dict[str, Any]:
    """
    Comprehensive MS validation for calibration operations.
    
    Returns a dict with validation results and recommendations.
    """
    results = {
        'ms_valid': False,
        'fields_available': [],
        'fields_valid': False,
        'refant_valid': False,
        'refant_suggestions': [],
        'warnings': [],
        'errors': []
    }
    
    try:
        # MS existence and readability
        if not os.path.exists(ms_path):
            results['errors'].append(f"MS does not exist: {ms_path}")
            return results
        
        # MS structure validation
        with table(ms_path, readonly=True) as tb:
            if tb.nrows() == 0:
                results['errors'].append(f"MS is empty: {ms_path}")
                return results
            
            # Get available fields
            field_ids = tb.getcol('FIELD_ID')
            results['fields_available'] = sorted(set(field_ids))
            
            # Validate field selection if provided
            if field:
                from dsa110_contimg.calibration.calibration import _resolve_field_ids
                target_ids = _resolve_field_ids(ms_path, field)
                if not target_ids:
                    results['errors'].append(f"Cannot resolve field: {field}")
                else:
                    missing = set(target_ids) - set(results['fields_available'])
                    if missing:
                        results['errors'].append(
                            f"Field(s) not found: {sorted(missing)}. "
                            f"Available: {results['fields_available']}"
                        )
                    else:
                        results['fields_valid'] = True
            
            # Validate reference antenna if provided
            if refant:
                ant1 = tb.getcol('ANTENNA1')
                ant2 = tb.getcol('ANTENNA2')
                all_antennas = set(ant1) | set(ant2)
                
                refant_int = int(refant) if isinstance(refant, str) else refant
                if refant_int not in all_antennas:
                    # Suggest alternatives
                    from dsa110_contimg.utils.antenna_classification import (
                        select_outrigger_refant, get_outrigger_antennas
                    )
                    outrigger_refant = select_outrigger_refant(
                        list(all_antennas), preferred_refant=refant_int
                    )
                    if outrigger_refant:
                        results['refant_suggestions'].append(outrigger_refant)
                    results['errors'].append(
                        f"Reference antenna {refant} not found. "
                        f"Available: {sorted(all_antennas)}"
                    )
                else:
                    results['refant_valid'] = True
            
            # Check flagged data fraction
            flags = tb.getcol('FLAG')
            unflagged_fraction = np.sum(~flags) / flags.size if flags.size > 0 else 0
            if unflagged_fraction < 0.1:
                results['warnings'].append(
                    f"Very little unflagged data: {unflagged_fraction*100:.1f}%"
                )
        
        results['ms_valid'] = len(results['errors']) == 0
        
    except Exception as e:
        results['errors'].append(f"Validation failed: {e}")
    
    return results


def validate_corrected_data_quality(ms_path: str, sample_size: int = 10000) -> Dict[str, Any]:
    """Validate CORRECTED_DATA column quality."""
    results = {
        'has_corrected_data': False,
        'non_zero_fraction': 0.0,
        'warnings': []
    }
    
    try:
        with table(ms_path, readonly=True) as tb:
            if 'CORRECTED_DATA' not in tb.colnames():
                return results
            
            results['has_corrected_data'] = True
            n_rows = tb.nrows()
            sample_size = min(sample_size, n_rows)
            
            corrected_data = tb.getcol('CORRECTED_DATA', startrow=0, nrow=sample_size)
            flags = tb.getcol('FLAG', startrow=0, nrow=sample_size)
            
            unflagged = corrected_data[~flags]
            if len(unflagged) > 0:
                nonzero_count = np.count_nonzero(np.abs(unflagged) > 1e-10)
                results['non_zero_fraction'] = nonzero_count / len(unflagged)
                
                if results['non_zero_fraction'] < 0.01:
                    results['warnings'].append(
                        "CORRECTED_DATA appears unpopulated "
                        f"({results['non_zero_fraction']*100:.1f}% non-zero)"
                    )
    
    except Exception as e:
        results['warnings'].append(f"Validation error: {e}")
    
    return results


def check_disk_space(path: str, min_bytes: Optional[int] = None) -> Dict[str, Any]:
    """Check available disk space for a path."""
    results = {
        'available_bytes': 0,
        'sufficient': True,
        'warnings': []
    }
    
    try:
        output_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(output_dir, exist_ok=True)
        available = shutil.disk_usage(output_dir).free
        results['available_bytes'] = available
        
        if min_bytes and available < min_bytes:
            results['sufficient'] = False
            results['warnings'].append(
                f"Insufficient disk space: need {min_bytes/1e9:.1f} GB, "
                f"available {available/1e9:.1f} GB"
            )
    except Exception as e:
        results['warnings'].append(f"Failed to check disk space: {e}")
    
    return results
```

### 3. Refactor Large CLI Files

#### Strategy for `calibration/cli.py`

**Before**: 852 lines, validation mixed with execution

**After**: Split into:
1. `calibration/cli.py` (~200 lines): Argument parsing + delegation
2. `calibration/cli_validate.py` (~150 lines): Validation logic
3. `calibration/cli_execute.py` (~300 lines): Execution logic
4. Use shared utilities for common patterns

#### Strategy for `imaging/cli.py`

**Before**: 956 lines, validation mixed with execution

**After**: Split into:
1. `imaging/cli.py` (~250 lines): Argument parsing + delegation
2. `imaging/cli_validate.py` (~100 lines): Validation logic
3. `imaging/cli_execute.py` (~400 lines): Core imaging logic
4. Use shared utilities

### 4. Improve User Experience

#### Progress Indicators

Create `utils/progress.py`:
```python
"""Progress indicators for long-running CLI operations."""

from typing import Optional, Callable
from contextlib import contextmanager
import sys

@contextmanager
def progress_context(total: Optional[int] = None, 
                    desc: str = "Processing",
                    show_percent: bool = True):
    """Context manager for showing progress."""
    if total:
        print(f"{desc}: 0/{total} (0%)", end='\r', file=sys.stderr)
    else:
        print(f"{desc}...", end='', flush=True, file=sys.stderr)
    
    count = 0
    def increment():
        nonlocal count
        count += 1
        if total:
            percent = int(100 * count / total)
            print(f"{desc}: {count}/{total} ({percent}%)", 
                  end='\r', file=sys.stderr)
    
    try:
        yield increment
    finally:
        print(file=sys.stderr)  # New line
```

#### Better Error Messages

Create `utils/error_messages.py`:
```python
"""User-friendly error messages."""

def format_validation_error(errors: List[str], context: str = "") -> str:
    """Format validation errors for user display."""
    msg = f"Validation failed{': ' + context if context else ''}\n\n"
    msg += "Issues found:\n"
    for i, error in enumerate(errors, 1):
        msg += f"  {i}. {error}\n"
    msg += "\nPlease fix the issues above and try again."
    return msg


def suggest_fix(error_type: str, details: Dict[str, Any]) -> str:
    """Suggest fixes for common errors."""
    suggestions = {
        'ms_not_found': lambda d: f"Check that the MS path is correct: {d.get('path')}",
        'field_not_found': lambda d: (
            f"Field '{d.get('field')}' not found. "
            f"Available fields: {d.get('available', [])}"
        ),
        'refant_not_found': lambda d: (
            f"Reference antenna {d.get('refant')} not found. "
            f"Available: {d.get('available', [])}. "
            f"Suggested: {d.get('suggested', 'N/A')}"
        ),
    }
    suggester = suggestions.get(error_type)
    return suggester(details) if suggester else "No suggestion available"
```

## Implementation Plan

### Phase 1: Foundation (Low Risk)
1. Create `utils/cli_helpers.py` with shared utilities
2. Create `utils/validation.py` with validation functions
3. Update one CLI module (e.g., `pointing/cli.py`) as proof-of-concept

### Phase 2: Refactoring (Medium Risk)
1. Refactor `pointing/cli.py` to use new utilities
2. Refactor `conversion/cli.py` (already clean, minimal changes)
3. Refactor `calibration/cli.py` (split validation/execution)
4. Refactor `imaging/cli.py` (split validation/execution)

### Phase 3: UX Improvements (Low Risk)
1. Add progress indicators to long operations
2. Improve error messages with suggestions
3. Add `--dry-run` flags where appropriate
4. Improve help text with examples

### Phase 4: Documentation (Low Risk)
1. Document shared utilities
2. Add CLI usage examples to docs
3. Create troubleshooting guide

## Benefits

1. **Reduced duplication**: ~30-40% reduction in repetitive code
2. **Easier maintenance**: Changes to validation logic in one place
3. **Better UX**: Consistent error messages, progress indicators
4. **Faster development**: New CLIs can use shared utilities
5. **Better testing**: Validation functions can be unit tested separately

## Risks and Mitigation

**Risk**: Breaking changes during refactoring
- **Mitigation**: Implement incrementally, test each module after refactoring

**Risk**: Over-abstraction
- **Mitigation**: Keep utilities simple and focused, avoid premature optimization

**Risk**: Performance impact
- **Mitigation**: Validation is fast relative to actual operations, any impact is negligible

## Metrics for Success

1. **Code reduction**: Target 30% reduction in CLI-related code
2. **Consistency**: All CLIs use same validation patterns
3. **User feedback**: Improved error messages reduce support requests
4. **Developer experience**: New CLIs are easier to create

## Next Steps

1. Review and approve this proposal
2. Create shared utilities module (Phase 1)
3. Refactor one CLI as proof-of-concept
4. Iterate based on feedback
