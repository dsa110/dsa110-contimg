# Synthetic Data Path Configuration

**Date:** 2025-11-12  
**Status:** Implemented  
**Purpose:** Configure default path for synthetic/test data

---

## Summary

The pipeline now supports a configurable default path for synthetic/test data. Synthetic images and MS files are stored in `/data/dsa110-contimg/state/synth/` by default, separate from real observational data.

---

## Configuration

### Default Path

**Synthetic data directory:** `/data/dsa110-contimg/state/synth/`

**Subdirectories:**
- Images: `/data/dsa110-contimg/state/synth/images/`
- MS files: `/data/dsa110-contimg/state/synth/ms/`

### Environment Variable

Set `PIPELINE_SYNTHETIC_DIR` to override the default:

```bash
export PIPELINE_SYNTHETIC_DIR="/custom/path/to/synth"
```

**Default:** `state/synth` (relative to project root) or `{PIPELINE_STATE_DIR}/synth`

---

## Code Changes

### 1. PipelineConfig (`src/dsa110_contimg/pipeline/config.py`)

**Added to `PathsConfig`:**
```python
synthetic_dir: Path = Field(
    default=Path("state/synth"), 
    description="Directory for synthetic/test data (images, MS files, etc.)"
)

@property
def synthetic_images_dir(self) -> Path:
    """Path to synthetic images directory."""
    return self.synthetic_dir / "images"

@property
def synthetic_ms_dir(self) -> Path:
    """Path to synthetic MS files directory."""
    return self.synthetic_dir / "ms"
```

**Updated `from_env()` method:**
- Reads `PIPELINE_SYNTHETIC_DIR` environment variable
- Defaults to `{PIPELINE_STATE_DIR}/synth` if not set

### 2. create_synthetic_images.py

**Updated paths:**
```python
SYNTHETIC_DIR = Path(os.getenv("PIPELINE_SYNTHETIC_DIR", "/data/dsa110-contimg/state/synth"))
IMAGES_DIR = SYNTHETIC_DIR / "images"
```

**MS paths now use:**
```python
ms_path = str(SYNTHETIC_DIR / "ms" / f"{ms_name}.ms")
```

---

## Registry Updates

**Completed:**
- ✅ Updated all 5 synthetic tile paths in products database
- ✅ Changed from `/data/dsa110-contimg/state/images/` to `/data/dsa110-contimg/state/synth/images/`
- ✅ All synthetic tiles verified to exist in new location

**Query to find synthetic tiles:**
```sql
SELECT i.path, dt.tag
FROM images i
JOIN data_tags dt ON dt.data_id = CAST(i.id AS TEXT)
WHERE dt.tag = 'synthetic';
```

---

## Directory Structure

```
/data/dsa110-contimg/state/
├── synth/                    # Synthetic/test data
│   ├── images/              # Synthetic images
│   │   └── *.pbcor.fits
│   └── ms/                  # Synthetic MS files
│       └── *.ms
├── images/                  # Real data images (if any)
├── ms/                      # Real data MS files (if any)
└── products.sqlite3         # Products database
```

---

## Usage

### Creating Synthetic Images

The `create_synthetic_images.py` script now automatically uses the synthetic directory:

```bash
# Uses default: /data/dsa110-contimg/state/synth/images/
python scripts/create_synthetic_images.py

# Or override with environment variable
PIPELINE_SYNTHETIC_DIR=/custom/synth python scripts/create_synthetic_images.py
```

### Accessing Synthetic Directory in Code

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
synthetic_images_dir = config.paths.synthetic_images_dir
synthetic_ms_dir = config.paths.synthetic_ms_dir
```

---

## Benefits

1. **Separation:** Synthetic data is clearly separated from real observational data
2. **Configurable:** Can be overridden via environment variable
3. **Consistent:** All synthetic data tools use the same path
4. **Organized:** Clear directory structure for different data types

---

## Migration Notes

- **Registry:** All synthetic tile paths have been updated in the database
- **Files:** Synthetic images moved from `/data/dsa110-contimg/state/images/` to `/data/dsa110-contimg/state/synth/images/`
- **Backward Compatibility:** Old paths in database have been updated; no code changes needed for existing entries

---

**Last Updated:** 2025-11-12

