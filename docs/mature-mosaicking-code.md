# Mature Mosaicking Architecture: Post-Refactoring Vision

_A concrete design for mosaicking after applying the complexity reduction principles. This shows what "simple, unified, and maintainable" looks like in practice._

---

## Executive Summary

**Current state:** Mosaicking is scattered across CLI scripts, manual workflows, and inconsistent job runners.

**Mature vision:** ABSURD-governed pipeline with three simple tiers, unified database state, and zero-intervention automation. The entire mosaicking system becomes ~500 lines of clear, testable code.

---

## Design Principles Applied

From the refactoring guide, we apply:

1. **Delete complexity:** No strategies, no flexibility theater, no premature abstraction
2. **Unify state:** Single database, single source of truth for all mosaic metadata
3. **Type safety:** Path objects everywhere, Pydantic validation
4. **Contract testing:** Real FITS files, real astrometry checks
5. **ABSURD orchestration:** Jobs, dependencies, automatic retries

---

## System Architecture

### High-Level Flow

┌─────────────────────────────────────────────────────┐
│ Event Sources │
│ • Cron (nightly) │
│ • API request (user-initiated) │
│ • ESE detection (science target) │
└─────────────────┬───────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────┐
│ ABSURD Pipeline Scheduler │
│ Selects tier, creates job graph, monitors │
└─────────────────┬───────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────┐
│ Job Execution (3 steps) │
│ │
│ 1. MosaicPlanningJob │
│ └─> Query images, select tier, validate │
│ │
│ 2. MosaicBuildJob (depends on #1) │
│ └─> Run reprojection, combine, write FITS │
│ │
│ 3. MosaicQAJob (depends on #2) │
│ └─> Astrometry, photometry, artifact detection │
└─────────────────┬───────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────┐
│ Unified Database Update │
│ • mosaic_plans table (metadata) │
│ • mosaics table (products) │
│ • mosaic_qa table (quality metrics) │
└─────────────────────────────────────────────────────┘

---

## Three Simple Tiers (No More!)

**Problem eliminated:** Current code has 6+ "tiers" with overlapping definitions, inconsistent parameters, and no clear selection logic.

**Solution:** Exactly three tiers, clearly defined:

| Tier          | Purpose              | Cadence           | Image Selection               | Alignment              | Typical Size |
| ------------- | -------------------- | ----------------- | ----------------------------- | ---------------------- | ------------ |
| **Quicklook** | Real-time monitoring | Every observation | Last 10 images                | Nearest-neighbor       | ~100 MB      |
| **Science**   | Publication-quality  | Nightly           | 24h window, RMS < threshold   | High-order SIP         | ~500 MB      |
| **Deep**      | Targeted integration | On-demand         | Multi-night, quality-filtered | Full astrometric solve | ~2 GB        |

**That's it.** No "tier 1.5", no experimental tiers, no config toggles.

### Tier Selection Logic

# backend/src/dsa110_contimg/mosaic/tiers.py

from enum import Enum
from dataclasses import dataclass
from typing import List
from pathlib import Path

class MosaicTier(Enum):
QUICKLOOK = "quicklook"
SCIENCE = "science"
DEEP = "deep"

@dataclass(frozen=True)
class TierConfig:
"""Immutable tier configuration"""
tier: MosaicTier
max_images: int
rms_threshold_jy: float
alignment_order: int # Reproject polynomial order
require_astrometry: bool
timeout_minutes: int

# The only three configs that exist

TIER_CONFIGS = {
MosaicTier.QUICKLOOK: TierConfig(
tier=MosaicTier.QUICKLOOK,
max_images=10,
rms_threshold_jy=0.01, # Permissive
alignment_order=1, # Fast nearest-neighbor
require_astrometry=False,
timeout_minutes=5
),
MosaicTier.SCIENCE: TierConfig(
tier=MosaicTier.SCIENCE,
max_images=100,
rms_threshold_jy=0.001, # Quality filter
alignment_order=3, # High-order SIP
require_astrometry=True,
timeout_minutes=30
),
MosaicTier.DEEP: TierConfig(
tier=MosaicTier.DEEP,
max_images=1000,
rms_threshold_jy=0.0005, # Best images only
alignment_order=5, # Full astrometric solve
require_astrometry=True,
timeout_minutes=120
)
}

def select_tier_for_request(
time_range_hours: float,
target_quality: str
) -> MosaicTier:
"""
Automatic tier selection based on request parameters

    No configuration sprawl—just clear logic:
    - Recent data (< 1 hour) → Quicklook
    - Daily range + quality → Science
    - Multi-day + "deep" requested → Deep
    """
    if time_range_hours < 1:
        return MosaicTier.QUICKLOOK
    elif target_quality == "deep" or time_range_hours > 48:
        return MosaicTier.DEEP
    else:
        return MosaicTier.SCIENCE

**No more:** Endless configuration knobs, tier confusion, or "which parameters do I use?"

---

## Database Schema (Unified)

**Single source of truth for all mosaic state.**

-- Mosaic planning metadata
CREATE TABLE mosaic_plans (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE NOT NULL,
tier TEXT NOT NULL CHECK(tier IN ('quicklook', 'science', 'deep')),

    -- Time range
    start_time INTEGER NOT NULL,  -- Unix timestamp
    end_time INTEGER NOT NULL,

    -- Image selection
    image_ids TEXT NOT NULL,  -- JSON array: [123, 456, 789]
    n_images INTEGER NOT NULL,

    -- Coverage statistics
    ra_min_deg REAL,
    ra_max_deg REAL,
    dec_min_deg REAL,
    dec_max_deg REAL,

    -- Metadata
    created_at INTEGER NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'building', 'completed', 'failed'))

);

-- Mosaic products
CREATE TABLE mosaics (
id INTEGER PRIMARY KEY AUTOINCREMENT,
plan_id INTEGER NOT NULL REFERENCES mosaic_plans(id),

    -- File location
    path TEXT UNIQUE NOT NULL,  -- /data/mosaics/science/mosaic_20250101_0300.fits

    -- Product metadata
    tier TEXT NOT NULL,
    n_images INTEGER NOT NULL,
    median_rms_jy REAL,

    -- Quality assessment
    qa_status TEXT CHECK(qa_status IN ('PASS', 'WARN', 'FAIL')),
    qa_details TEXT,  -- JSON: {"astrometry_rms_arcsec": 0.1, ...}

    -- Timestamps
    created_at INTEGER NOT NULL,

    -- Indexes for fast lookup
    INDEX idx_mosaic_tier ON mosaics(tier),
    INDEX idx_mosaic_created ON mosaics(created_at)

);

-- Quality assessment results
CREATE TABLE mosaic_qa (
id INTEGER PRIMARY KEY AUTOINCREMENT,
mosaic_id INTEGER NOT NULL REFERENCES mosaics(id),

    -- Astrometric quality
    astrometry_rms_arcsec REAL,
    n_reference_stars INTEGER,

    -- Photometric quality
    median_noise_jy REAL,
    dynamic_range REAL,

    -- Artifacts
    has_artifacts BOOLEAN,
    artifact_score REAL,  -- 0.0 (clean) to 1.0 (severe)

    -- Overall
    passed BOOLEAN NOT NULL,
    warnings TEXT,  -- JSON array of warning messages

    created_at INTEGER NOT NULL

);

**Why this works:**

- One query gets complete mosaic history
- JOINs across tables are simple
- Status tracking is clear
- No cross-database confusion

---

## Job Implementation (ABSURD Pipeline)

### Job 1: Planning

# backend/src/dsa110_contimg/mosaic/jobs.py

from absurd import Job, JobResult
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class MosaicPlanningJob(Job):
"""
Select images for mosaicking based on time range and tier

    Inputs:
        - start_time, end_time (Unix timestamps)
        - tier (quicklook/science/deep)

    Outputs:
        - plan_id (database row)
        - image_ids (list of selected images)
    """
    job_type = "mosaic_planning"

    start_time: int
    end_time: int
    tier: str
    mosaic_name: str

    def execute(self) -> JobResult:
        from dsa110_contimg.database import Database
        from dsa110_contimg.mosaic.tiers import TIER_CONFIGS, MosaicTier

        db = Database(self.config.database_path)
        tier_enum = MosaicTier(self.tier)
        tier_config = TIER_CONFIGS[tier_enum]

        # Query images in time range with quality filter
        query = """
            SELECT id, path, rms_jy, ra_deg, dec_deg
            FROM images
            WHERE created_at BETWEEN ? AND ?
              AND rms_jy < ?
            ORDER BY rms_jy ASC
            LIMIT ?
        """

        images = db.query(
            query,
            (self.start_time, self.end_time,
             tier_config.rms_threshold_jy, tier_config.max_images)
        )

        if len(images) == 0:
            return JobResult.failure("No images found in time range")

        # Calculate coverage statistics
        coverage = {
            'ra_min_deg': min(img['ra_deg'] for img in images),
            'ra_max_deg': max(img['ra_deg'] for img in images),
            'dec_min_deg': min(img['dec_deg'] for img in images),
            'dec_max_deg': max(img['dec_deg'] for img in images),
        }

        # Insert plan into database
        image_ids = [img['id'] for img in images]
        plan_id = db.execute(
            """
            INSERT INTO mosaic_plans
                (name, tier, start_time, end_time, image_ids, n_images,
                 ra_min_deg, ra_max_deg, dec_min_deg, dec_max_deg, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (self.mosaic_name, self.tier, self.start_time, self.end_time,
             json.dumps(image_ids), len(images),
             coverage['ra_min_deg'], coverage['ra_max_deg'],
             coverage['dec_min_deg'], coverage['dec_max_deg'],
             int(time.time()))
        )

        return JobResult.success(
            outputs={'plan_id': plan_id, 'image_ids': image_ids, 'n_images': len(images)},
            message=f"Selected {len(images)} images for {self.tier} mosaic"
        )

### Job 2: Building

@dataclass
class MosaicBuildJob(Job):
"""
Build mosaic from planned images using reproject

    Inputs:
        - plan_id (from planning job)

    Outputs:
        - mosaic_id (database row)
        - mosaic_path (FITS file)
    """
    job_type = "mosaic_build"

    plan_id: int

    def execute(self) -> JobResult:
        from dsa110_contimg.database import Database
        from dsa110_contimg.mosaic.builder import build_mosaic
        from dsa110_contimg.mosaic.tiers import TIER_CONFIGS, MosaicTier
        import json
        import time

        db = Database(self.config.database_path)

        # Get plan details
        plan = db.query(
            "SELECT * FROM mosaic_plans WHERE id = ?",
            (self.plan_id,)
        )[0]

        # Update status
        db.execute(
            "UPDATE mosaic_plans SET status = 'building' WHERE id = ?",
            (self.plan_id,)
        )

        # Get image paths
        image_ids = json.loads(plan['image_ids'])
        images = db.query(
            f"SELECT path FROM images WHERE id IN ({','.join('?' * len(image_ids))})",
            tuple(image_ids)
        )
        image_paths = [Path(img['path']) for img in images]

        # Get tier configuration
        tier_config = TIER_CONFIGS[MosaicTier(plan['tier'])]

        # Build mosaic (actual work happens here)
        output_path = self.config.mosaic_dir / f"{plan['name']}.fits"

        try:
            result = build_mosaic(
                image_paths=image_paths,
                output_path=output_path,
                alignment_order=tier_config.alignment_order,
                timeout_minutes=tier_config.timeout_minutes
            )
        except Exception as e:
            db.execute(
                "UPDATE mosaic_plans SET status = 'failed' WHERE id = ?",
                (self.plan_id,)
            )
            return JobResult.failure(f"Mosaic build failed: {e}")

        # Register mosaic in database
        mosaic_id = db.execute(
            """
            INSERT INTO mosaics
                (plan_id, path, tier, n_images, median_rms_jy, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.plan_id, str(output_path), plan['tier'],
             len(image_paths), result.median_rms, int(time.time()))
        )

        db.execute(
            "UPDATE mosaic_plans SET status = 'completed' WHERE id = ?",
            (self.plan_id,)
        )

        return JobResult.success(
            outputs={'mosaic_id': mosaic_id, 'mosaic_path': str(output_path)},
            message=f"Built mosaic: {output_path}"
        )

### Job 3: Quality Assessment

@dataclass
class MosaicQAJob(Job):
"""
Run quality checks on completed mosaic

    Inputs:
        - mosaic_id (from build job)

    Outputs:
        - qa_status (PASS/WARN/FAIL)
        - qa_metrics (dict)
    """
    job_type = "mosaic_qa"

    mosaic_id: int

    def execute(self) -> JobResult:
        from dsa110_contimg.database import Database
        from dsa110_contimg.mosaic.qa import run_qa_checks
        import json
        import time

        db = Database(self.config.database_path)

        # Get mosaic details
        mosaic = db.query(
            "SELECT * FROM mosaics WHERE id = ?",
            (self.mosaic_id,)
        )[0]

        # Run QA checks
        qa_result = run_qa_checks(
            mosaic_path=Path(mosaic['path']),
            tier=mosaic['tier']
        )

        # Determine overall status
        if qa_result.critical_failures:
            qa_status = 'FAIL'
        elif qa_result.warnings:
            qa_status = 'WARN'
        else:
            qa_status = 'PASS'

        # Store QA results
        db.execute(
            """
            INSERT INTO mosaic_qa
                (mosaic_id, astrometry_rms_arcsec, n_reference_stars,
                 median_noise_jy, dynamic_range, has_artifacts, artifact_score,
                 passed, warnings, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.mosaic_id, qa_result.astrometry_rms, qa_result.n_stars,
             qa_result.median_noise, qa_result.dynamic_range,
             qa_result.has_artifacts, qa_result.artifact_score,
             qa_status == 'PASS', json.dumps(qa_result.warnings),
             int(time.time()))
        )

        # Update mosaic record
        db.execute(
            """
            UPDATE mosaics
            SET qa_status = ?, qa_details = ?
            WHERE id = ?
            """,
            (qa_status, json.dumps(qa_result.to_dict()), self.mosaic_id)
        )

        return JobResult.success(
            outputs={'qa_status': qa_status, 'qa_metrics': qa_result.to_dict()},
            message=f"QA complete: {qa_status}"
        )

---

## Core Mosaic Builder (The Actual Work)

**This is where reproject happens. ~150 lines total.**

# backend/src/dsa110_contimg/mosaic/builder.py

from pathlib import Path
from typing import List
from dataclasses import dataclass
from astropy.io import fits
from astropy.wcs import WCS
from reproject import reproject_interp
from reproject.mosaicking import reproject_and_coadd
import numpy as np

@dataclass
class MosaicResult:
"""Result of mosaic build operation"""
output_path: Path
n_images: int
median_rms: float
coverage_sq_deg: float

def build_mosaic(
image_paths: List[Path],
output_path: Path,
alignment_order: int = 3,
timeout_minutes: int = 30
) -> MosaicResult:
"""
Build mosaic from list of FITS images

    This is the ONE function that does mosaicking. No strategies,
    no configuration sprawl, no flexibility theater.

    Args:
        image_paths: List of input FITS files
        output_path: Where to write output mosaic
        alignment_order: Polynomial order for reprojection (1=fast, 5=accurate)
        timeout_minutes: Maximum execution time

    Returns:
        MosaicResult with metadata
    """

    # Read input images and WCS
    hdus = [fits.open(str(p))[0] for p in image_paths]

    # Compute optimal output WCS (covers all inputs)
    output_wcs = compute_optimal_wcs(hdus)

    # Reproject all images to common grid
    arrays = []
    footprints = []

    for hdu in hdus:
        array, footprint = reproject_interp(
            hdu,
            output_wcs,
            shape_out=output_wcs.array_shape,
            order=alignment_order
        )
        arrays.append(array)
        footprints.append(footprint)

    # Combine with weighted average (weight by 1/rms^2)
    weights = compute_weights(hdus)
    combined = np.average(arrays, axis=0, weights=weights)
    combined_footprint = np.sum(footprints, axis=0) > 0

    # Compute statistics
    median_rms = np.median([compute_rms(arr) for arr in arrays])
    coverage_sq_deg = np.sum(combined_footprint) * output_wcs.proj_plane_pixel_scales()[0]**2

    # Write output FITS
    output_hdu = fits.PrimaryHDU(data=combined, header=output_wcs.to_header())
    output_hdu.header['NIMAGES'] = len(image_paths)
    output_hdu.header['MEDRMS'] = median_rms
    output_hdu.writeto(str(output_path), overwrite=True)

    return MosaicResult(
        output_path=output_path,
        n_images=len(image_paths),
        median_rms=median_rms,
        coverage_sq_deg=coverage_sq_deg
    )

def compute_optimal_wcs(hdus: List[fits.HDUList]) -> WCS:
"""Compute WCS that covers all input images""" # Find min/max RA/Dec across all images
all_corners = []
for hdu in hdus:
wcs = WCS(hdu.header)
ny, nx = hdu.data.shape
corners = wcs.pixel_to_world([0, nx, nx, 0], [0, 0, ny, ny])
all_corners.extend(corners)

    # Compute bounding box
    ra_min = min(c.ra.deg for c in all_corners)
    ra_max = max(c.ra.deg for c in all_corners)
    dec_min = min(c.dec.deg for c in all_corners)
    dec_max = max(c.dec.deg for c in all_corners)

    # Create new WCS centered on field
    # (Implementation details of WCS construction)
    # ...

    return output_wcs

def compute_weights(hdus: List[fits.HDUList]) -> np.ndarray:
"""Compute inverse-variance weights for images"""
weights = []
for hdu in hdus:
rms = compute_rms(hdu.data)
weights.append(1.0 / rms\*\*2)
return np.array(weights)

def compute_rms(data: np.ndarray) -> float:
"""Compute RMS noise in image"""
return np.std(data[np.isfinite(data)])

**That's it. ~150 lines does all the mosaicking.**

**No:**

- Strategy pattern for different combiners
- Pluggable weight schemes
- Configuration files for every parameter
- Abstract base classes

**Just:** A function that does one thing well.

---

## Quality Assessment (Simple Contract)

# backend/src/dsa110_contimg/mosaic/qa.py

from pathlib import Path
from dataclasses import dataclass
from typing import List
from astropy.io import fits
from astropy.wcs import WCS
from astroquery.gaia import Gaia

@dataclass
class QAResult:
"""Results of quality assessment"""
astrometry_rms: float # arcsec
n_stars: int
median_noise: float # Jy
dynamic_range: float
has_artifacts: bool
artifact_score: float # 0-1
warnings: List[str]
critical_failures: List[str]

    def to_dict(self):
        return self.__dict__

def run_qa_checks(mosaic_path: Path, tier: str) -> QAResult:
"""
Run quality checks on mosaic

    Three checks:
    1. Astrometry (compare to Gaia)
    2. Photometry (noise, dynamic range)
    3. Artifacts (visual inspection heuristics)
    """

    hdu = fits.open(str(mosaic_path))[0]
    wcs = WCS(hdu.header)
    data = hdu.data

    warnings = []
    failures = []

    # 1. Astrometric check
    astro_result = check_astrometry(wcs, data)
    if astro_result.rms_arcsec > 1.0:  # > 1 arcsec is bad
        failures.append(f"Astrometry RMS: {astro_result.rms_arcsec:.2f} arcsec")
    elif astro_result.rms_arcsec > 0.5:
        warnings.append(f"Astrometry RMS: {astro_result.rms_arcsec:.2f} arcsec")

    # 2. Photometric check
    photo_result = check_photometry(data)
    if photo_result.dynamic_range < 100:
        failures.append(f"Low dynamic range: {photo_result.dynamic_range:.1f}")

    # 3. Artifact check
    artifact_result = check_artifacts(data)
    if artifact_result.score > 0.5:
        warnings.append(f"Possible artifacts detected (score: {artifact_result.score:.2f})")

    return QAResult(
        astrometry_rms=astro_result.rms_arcsec,
        n_stars=astro_result.n_stars,
        median_noise=photo_result.median_noise,
        dynamic_range=photo_result.dynamic_range,
        has_artifacts=artifact_result.score > 0.3,
        artifact_score=artifact_result.score,
        warnings=warnings,
        critical_failures=failures
    )

---

## Pipeline Definitions

**How jobs connect together:**

# backend/src/dsa110_contimg/mosaic/pipeline.py

from absurd import Pipeline, CronTrigger
from dsa110_contimg.mosaic.jobs import (
MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
)

class NightlyMosaicPipeline(Pipeline):
"""
Nightly science-tier mosaic

    Runs at 03:00 UTC, processes previous 24 hours
    """
    pipeline_name = "nightly_mosaic"

    def __init__(self, config):
        super().__init__(config)

        import time
        end_time = int(time.time())
        start_time = end_time - 86400  # 24 hours ago

        # Job graph with dependencies
        self.add_job(
            MosaicPlanningJob,
            job_id='plan',
            params={
                'start_time': start_time,
                'end_time': end_time,
                'tier': 'science',
                'mosaic_name': f'nightly_{time.strftime("%Y%m%d")}'
            }
        )

        self.add_job(
            MosaicBuildJob,
            job_id='build',
            params={'plan_id': '${plan.plan_id}'},
            dependencies=['plan']
        )

        self.add_job(
            MosaicQAJob,
            job_id='qa',
            params={'mosaic_id': '${build.mosaic_id}'},
            dependencies=['build']
        )

        # Retry policy
        self.set_retry_policy(max_retries=2, backoff='exponential')

        # Notifications
        self.add_notification(
            on_failure='qa',
            channels=['email'],
            recipients=['observer@dsa110.org']
        )

class OnDemandMosaicPipeline(Pipeline):
"""
User-requested mosaic via API

    Same job structure, different trigger
    """
    pipeline_name = "on_demand_mosaic"

    def __init__(self, config, request_params):
        super().__init__(config)

        # Same three jobs, parameterized by request
        self.add_job(
            MosaicPlanningJob,
            job_id='plan',
            params={
                'start_time': request_params['start_time'],
                'end_time': request_params['end_time'],
                'tier': request_params.get('tier', 'science'),
                'mosaic_name': request_params['name']
            }
        )

        # ... same build and QA jobs

---

## API Endpoints (Simple)

# backend/src/dsa110_contimg/api/mosaic.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dsa110_contimg.mosaic.pipeline import OnDemandMosaicPipeline
from dsa110_contimg.database import Database

router = APIRouter(prefix="/api/mosaic")

class MosaicRequest(BaseModel):
name: str
start_time: int # Unix timestamp
end_time: int
tier: str = "science" # quicklook/science/deep

@router.post("/create")
async def create_mosaic(request: MosaicRequest):
"""
Create mosaic from time range

    This is the ONLY mosaic creation endpoint. Simple API.
    """

    # Validate
    if request.end_time <= request.start_time:
        raise HTTPException(400, "Invalid time range")

    if request.tier not in ['quicklook', 'science', 'deep']:
        raise HTTPException(400, f"Invalid tier: {request.tier}")

    # Launch pipeline
    pipeline = OnDemandMosaicPipeline(
        config=app_config,
        request_params=request.dict()
    )

    execution_id = pipeline.start()

    return {
        'status': 'accepted',
        'execution_id': execution_id,
        'message': f'Mosaic creation started: {request.name}'
    }

@router.get("/status/{name}")
async def get_mosaic_status(name: str):
"""Query mosaic build status"""
db = Database(app_config.database_path)

    plan = db.query(
        "SELECT * FROM mosaic_plans WHERE name = ?",
        (name,)
    )

    if not plan:
        raise HTTPException(404, "Mosaic not found")

    plan = plan[0]

    # Get mosaic if completed
    mosaic = None
    if plan['status'] == 'completed':
        mosaic = db.query(
            "SELECT * FROM mosaics WHERE plan_id = ?",
            (plan['id'],)
        )[0]

    return {
        'name': name,
        'status': plan['status'],
        'tier': plan['tier'],
        'n_images': plan['n_images'],
        'mosaic_path': mosaic['path'] if mosaic else None,
        'qa_status': mosaic['qa_status'] if mosaic else None
    }

**That's it. Two endpoints:**

1. POST `/create` - Start mosaic
2. GET `/status/{name}` - Check status

**No:**

- `/api/v1/mosaic/advanced/create`
- `/api/v2/mosaic/experimental/build`
- `/api/mosaic/legacy/run`

---

## Contract Tests (High Confidence)

# tests/contracts/test_mosaic_complete.py

import pytest
from pathlib import Path
from dsa110_contimg.mosaic.builder import build_mosaic
from dsa110_contimg.mosaic.qa import run_qa_checks
from astropy.io import fits
import numpy as np

@pytest.fixture
def synthetic_images(tmp_path):
"""Create realistic synthetic FITS images"""
images = []
for i in range(5): # Create 1024x1024 image with noise + point sources
data = np.random.normal(0, 0.001, (1024, 1024))

        # Add point sources
        for _ in range(10):
            x, y = np.random.randint(100, 924, 2)
            data[y-2:y+2, x-2:x+2] += np.random.uniform(0.01, 0.1)

        # Create WCS (slightly different pointing each)
        from astropy.wcs import WCS
        wcs = WCS(naxis=2)
        wcs.wcs.crpix = [512, 512]
        wcs.wcs.crval = [180.0 + i*0.1, 40.0]  # Shift RA slightly
        wcs.wcs.cdelt = [0.001, 0.001]
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]

        # Write FITS
        path = tmp_path / f"image_{i}.fits"
        hdu = fits.PrimaryHDU(data=data, header=wcs.to_header())
        hdu.writeto(str(path))
        images.append(path)

    return images

def test_mosaic_creates_valid_fits(synthetic_images, tmp_path):
"""Verify mosaic produces valid FITS file"""
output = tmp_path / "mosaic.fits"

    result = build_mosaic(
        image_paths=synthetic_images,
        output_path=output,
        alignment_order=3
    )

    # File exists and is valid FITS
    assert output.exists()
    hdu = fits.open(str(output))[0]

    # Has data and WCS
    assert hdu.data is not None
    assert hdu.data.shape[0] > 1000  # Reasonable size
    assert 'CRPIX1' in hdu.header  # Has WCS

    # Metadata correct
    assert hdu.header['NIMAGES'] == len(synthetic_images)
    assert result.n_images == len(synthetic_images)

def test_mosaic_qa_passes(synthetic_images, tmp_path):
"""Verify QA runs and passes for good data"""
output = tmp_path / "mosaic.fits"

    build_mosaic(
        image_paths=synthetic_images,
        output_path=output,
        alignment_order=3
    )

    qa_result = run_qa_checks(output, tier='science')

    # Should pass with clean synthetic data
    assert qa_result.critical_failures == []
    assert qa_result.astrometry_rms < 1.0  # < 1 arcsec
    assert qa_result.dynamic_range > 10  # Reasonable DR

def test_full_pipeline_execution(synthetic_images, tmp_path, monkeypatch):
"""Integration test: Planning → Build → QA"""
from dsa110_contimg.database import Database
from dsa110_contimg.mosaic.jobs import (
MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
)
import time
import json

    # Set up test database
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    # Populate images table
    for i, img_path in enumerate(synthetic_images):
        db.execute(
            """INSERT INTO images
               (path, rms_jy, ra_deg, dec_deg, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (str(img_path), 0.001, 180.0 + i*0.1, 40.0, int(time.time()))
        )

    # Run planning job
    plan_job = MosaicPlanningJob(
        start_time=int(time.time()) - 3600,
        end_time=int(time.time()),
        tier='science',
        mosaic_name='test_mosaic'
    )
    plan_result = plan_job.execute()
    assert plan_result.success
    plan_id = plan_result.outputs['plan_id']

    # Run build job
    build_job = MosaicBuildJob(plan_id=plan_id)
    build_result = build_job.execute()
    assert build_result.success
    mosaic_id = build_result.outputs['mosaic_id']

    # Run QA job
    qa_job = MosaicQAJob(mosaic_id=mosaic_id)
    qa_result = qa_job.execute()
    assert qa_result.success
    assert qa_result.outputs['qa_status'] in ['PASS', 'WARN']

    # Verify database state
    mosaic = db.query("SELECT * FROM mosaics WHERE id = ?", (mosaic_id,))[0]
    assert mosaic['qa_status'] in ['PASS', 'WARN']

**These tests:**

- Use real FITS files (synthetic but realistic)
- Test full pipeline execution
- Verify database state
- Catch real bugs (not mock call order)

---

## What We Eliminated

**Complexity removed from current system:**

| Current Problem                     | Mature Solution                        |
| ----------------------------------- | -------------------------------------- |
| 6+ overlapping tiers                | Exactly 3 tiers with clear definitions |
| Tier selection scattered in 8 files | One 20-line function                   |
| Multiple orchestration systems      | ABSURD only                            |
| Strategy pattern for combiners      | One function: `build_mosaic()`         |
| Configuration in 12 places          | Three `TierConfig` dataclasses         |
| Database state split across 5 DBs   | Three tables in `pipeline.sqlite3`     |
| Mock-heavy tests                    | Contract tests with real FITS          |
| Manual cron jobs                    | ABSURD scheduler with auto-retry       |
| CLI scripts for every operation     | Two API endpoints                      |

**Code size:**

- Current: ~3,000 lines across 25 files
- Mature: ~800 lines across 8 files
- **Reduction: 73%**

---

## Migration Path

**Phase 1: Build ABSURD jobs alongside existing system**

- Implement three job classes
- Run in parallel with current manual workflows
- Compare outputs (should be identical)

**Phase 2: Database migration**

- Create three new tables in unified DB
- Migrate mosaic history
- Switch jobs to use new schema

**Phase 3: Switch traffic**

- Route 10% of requests to ABSURD pipeline
- Monitor for discrepancies
- Gradually increase to 100%

**Phase 4: Decommission legacy**

- Delete old CLI scripts
- Remove cron jobs
- Archive old code

**Timeline:** 6-8 weeks with careful validation

---

## Success Metrics

**How we know it worked:**

1. **Simplicity**

   - Onboard new developer: Explain entire system in 30 minutes
   - Tiers: Can recite all three from memory
   - Code: Read full implementation in 1 hour

2. **Reliability**

   - Nightly mosaics: 100% success rate
   - QA failures: Detected automatically
   - Bugs: Contract tests catch regressions

3. **Performance**

   - Quicklook: < 5 minutes
   - Science: < 30 minutes
   - Deep: < 2 hours

4. **Maintainability**
   - Add new QA check: < 50 lines, 1 hour
   - Change tier config: Edit 3 lines in one file
   - Debug failure: Single 15-line stack trace

---

## Summary

**The mature mosaicking system is:**

✅ **Simple:** 800 lines total, 8 files, 3 tiers  
✅ **Unified:** One database, one orchestrator, one API  
✅ **Testable:** Contract tests with real FITS files  
✅ **Automated:** Zero-intervention nightly operation  
✅ **Clear:** Any developer can understand full system in 30 minutes

**The opposite of the current system:**

❌ ~~Scattered across 25 files~~  
❌ ~~6+ overlapping tier definitions~~  
❌ ~~Multiple orchestration approaches~~  
❌ ~~Mock-heavy tests that give false confidence~~  
❌ ~~Manual cron jobs and CLI scripts~~

**This is what "complexity reduction" produces in practice: dramatic simplification without loss of capability.**
