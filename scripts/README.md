# DSA-110 Scripts

Consolidated scripts directory for the DSA-110 continuum imaging pipeline.

## Structure

- `ops/` - Operational scripts (calibration, imaging, deployment, diagnostics)
- `backend/` - Backend utility scripts  
- `frontend/` → `../frontend/scripts/` - Frontend build/test scripts (symlink)
- `archive/` - Legacy/experimental scripts

## Usage

Most scripts require the `casa6` conda environment:

```bash
conda activate casa6
./scripts/ops/health_check.sh
```
