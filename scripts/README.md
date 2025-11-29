# DSA-110 Scripts

Consolidated scripts directory for the DSA-110 continuum imaging pipeline.

## Structure

- `ops/` - Operational scripts (calibration, imaging, deployment, diagnostics)
- `backend/` - Backend utility scripts
- `frontend/` :arrow_right: `../frontend/scripts/` - Frontend build/test scripts (symlink)
- `archive/` - Legacy/experimental scripts

## Validation Tools

**Portable validation scripts** for CI/deployment:

- `preflight-check.sh` - Comprehensive pre-deployment validation
- `validate-script-refs.sh` - Validates script references in package.json and
  systemd
- `check-environment.sh` - Quick environment check

See [VALIDATION_TOOLS.md](VALIDATION_TOOLS.md) for detailed documentation.

## Usage

Most scripts require the `casa6` conda environment:

```bash
conda activate casa6
./scripts/ops/health_check.sh
```
