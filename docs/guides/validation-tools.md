# Validation Tools

Tools for validating DSA-110 continuum imaging pipeline data products
and configuration.

## Measurement Set Validation

### Unified MS Validator (Recommended)

**Location**: `backend/src/dsa110_contimg/validation/ms_validator.py`

The unified MS validator consolidates all MS validation functionality into
a single, comprehensive module. Use this instead of the legacy scripts.

**Python API**:

```python
from dsa110_contimg.validation import validate_ms, MSValidator

# Quick validation
report = validate_ms("/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms")
print(report.summary())

# With calibrator check
report = validate_ms(
    "/path/to/file.ms",
    calibrator_name="3C286",
    calibrator_ra_deg=202.7845,
    calibrator_dec_deg=30.5091,
)

# JSON output
import json
print(json.dumps(report.to_dict(), indent=2))

# Access individual results
if report.passed:
    print("All checks passed!")
else:
    for error in report.errors:
        print(f"FAILED: {error.name}: {error.message}")
```

**CLI**:

```bash
# Basic validation
python -m dsa110_contimg.validation.ms_validator /path/to/file.ms

# With calibrator alignment check
python -m dsa110_contimg.validation.ms_validator /path/to/file.ms \
    --calibrator 3C286 --cal-ra 202.7845 --cal-dec 30.5091

# JSON output
python -m dsa110_contimg.validation.ms_validator /path/to/file.ms --json

# Skip data check (faster)
python -m dsa110_contimg.validation.ms_validator /path/to/file.ms --no-data
```

**Validation Checks**:

| Check                  | Description                           | Severity |
| ---------------------- | ------------------------------------- | -------- |
| `ms_exists`            | MS path exists and is valid directory | error    |
| `required_tables`      | All required subtables present        | error    |
| `properties_extracted` | Basic properties readable             | error    |
| `phase_center_valid`   | Phase center has valid coordinates    | error    |
| `rephase_status`       | REFERENCE_DIR vs PHASE_DIR comparison | info     |
| `calibrator_alignment` | Field aligned with calibrator         | warning  |
| `data_nonzero`         | DATA column has non-zero values       | error    |
| `flagging`             | Flag fraction check                   | info     |
| `timing_duration`      | Observation duration check            | warning  |

**Output Properties**:

- `nrows`: Number of data rows
- `nants`: Number of antennas
- `nfields`: Number of fields
- `field_names`: List of field names
- `nspw`: Number of spectral windows
- `total_channels`: Total frequency channels
- `data_shape`: Shape of DATA column
- `time_start`, `time_end`: Observation time range
- `duration_seconds`: Observation duration
- `phase_centers`: List of field phase centers

---

### Legacy Scripts (Archived)

The following scripts have been **archived** to `scripts/archive/validation/`.
Use the unified `ms_validator` instead.

| Archived Script              | Replacement                                                  |
| ---------------------------- | ------------------------------------------------------------ |
| `check_ms_properties.py`     | `validate_ms()` - properties in report                       |
| `check_ms_phasing.py`        | `validate_ms(calibrator_ra_deg=..., calibrator_dec_deg=...)` |
| `check_ms_rephase_status.py` | `report.properties["rephase_status"]`                        |
| `validate_ms_timing.py`      | `report.properties["time_start"]`, `duration_seconds`        |

---

## Configuration Validation

All configuration validation tools are **portable** - they auto-detect the
project root and can run from any directory or CI environment.

## Tools

### `preflight-check.sh`

**Purpose**: Comprehensive pre-deployment validation

**Features**:

- Environment checks (conda, Node.js, Python)
- Script existence validation
- Systemd service status
- Port availability
- Build artifact verification

**Usage**:

```bash
# Auto-detect project root from script location
/path/to/scripts/preflight-check.sh

# Explicit project root
/path/to/scripts/preflight-check.sh /custom/project/root

# Run from project directory
./scripts/preflight-check.sh
```

**Exit codes**:

- `0` - All checks passed
- `1` - Critical checks failed

**Output**:

- :check: Green: Pass
- :warning: Yellow: Warning (non-critical)
- :cross: Red: Error (critical failure)

---

### `validate-script-refs.sh`

**Purpose**: Validates script references in `package.json` and systemd service
files

**Features**:

- Extracts bash script paths from `frontend/package.json`
- Validates `ExecStart`/`ExecStartPre` paths in systemd services
- Reports missing files

**Usage**:

```bash
# Auto-detect project root
/path/to/scripts/validate-script-refs.sh

# Explicit project root
/path/to/scripts/validate-script-refs.sh /custom/project/root
```

**Exit codes**:

- `0` - All references valid
- `1` - Missing script references found

**Use cases**:

- Pre-commit hook
- CI validation
- After script reorganization

---

### `check-environment.sh`

**Purpose**: Quick environment check for frontend development

**Features**:

- Node.js version
- npm version
- casa6 environment detection
- node_modules existence

**Usage**:

```bash
# Auto-detect project root
/path/to/scripts/check-environment.sh

# Explicit project root
/path/to/scripts/check-environment.sh /custom/project/root
```

**Exit codes**:

- `0` - Environment OK
- `1` - Missing critical dependencies

---

## Portability Features

All scripts support:

1. **Auto-detection**: Uses `SCRIPT_DIR` to find project root automatically
2. **Parameter override**: Accepts explicit project root as first argument
3. **Path-independent**: Works from any working directory
4. **CI-friendly**: No hardcoded paths or assumptions

**Implementation pattern**:

```bash
# Auto-detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(dirname "$SCRIPT_DIR")}"
```

## Integration

### VS Code Tasks

Configured in `.vscode/tasks.json`:

- ":search: Preflight Check" - Runs before startup
- Auto-runs when folder opens (requires `"task.allowAutomaticTasks": "on"`)

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
scripts/validate-script-refs.sh || exit 1
```

### CI/CD

Example GitHub Actions:

```yaml
- name: Validate script references
  run: scripts/validate-script-refs.sh

- name: Preflight check
  run: scripts/preflight-check.sh
```

### Docker

Example Dockerfile:

```dockerfile
COPY scripts/preflight-check.sh /scripts/
RUN /scripts/preflight-check.sh /app
```

## Common Use Cases

### Development Setup

```bash
# Check environment before starting dev work
scripts/check-environment.sh

# Full validation before committing
scripts/preflight-check.sh
```

### Deployment Validation

```bash
# Before deploying to production
scripts/preflight-check.sh

# After script reorganization
scripts/validate-script-refs.sh
```

### CI Pipeline

```bash
# In Jenkins/GitHub Actions/GitLab CI
scripts/validate-script-refs.sh
scripts/preflight-check.sh
```

## Troubleshooting

### Script not found errors

**Symptom**: `validate-script-refs.sh` reports missing scripts

**Fix**: Run from project root or provide explicit path:

```bash
scripts/validate-script-refs.sh /data/dsa110-contimg
```

### Permission denied

**Symptom**: `bash: ./script.sh: Permission denied`

**Fix**: Ensure scripts are executable:

```bash
chmod +x scripts/*.sh
```

### Wrong project root detected

**Symptom**: Scripts check wrong directory

**Fix**: Provide explicit project root:

```bash
/path/to/scripts/preflight-check.sh /correct/project/root
```

## Maintenance

### Adding new validation checks

Edit `preflight-check.sh` and use the helper functions:

```bash
# Critical check (exit on failure)
check "Description" "test_command"

# Warning (don't exit on failure)
warn "Description" "test_command"
```

### Adding new script references

1. Add script to appropriate location
2. Update reference in `package.json` or systemd service
3. Run `validate-script-refs.sh` to verify

### Testing changes

```bash
# Test from different directories
cd /tmp && /data/dsa110-contimg/scripts/preflight-check.sh
cd ~ && /data/dsa110-contimg/scripts/validate-script-refs.sh

# Test with explicit parameter
/data/dsa110-contimg/scripts/preflight-check.sh /data/dsa110-contimg
```

## Related Documentation

- [Development Workflow](../docs/guides/development_workflow.md)
- [System Context](../docs/SYSTEM_CONTEXT.md)
- [Operations Guide](../docs/operations/README.md)
