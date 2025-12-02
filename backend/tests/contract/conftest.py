"""
Contract test fixtures using the simulation module.

These fixtures create REAL data files that can be inspected with standard
tools (casatools, astropy, etc.) to verify correctness.

Philosophy:
- Mock-free: Use real simulation code, not MagicMock
- Observable: All outputs can be inspected externally
- Realistic: Data matches DSA-110 telescope characteristics
- Self-documenting: Fixtures clearly state what they produce
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator, List, Optional

import numpy as np
import pytest

# Mark all tests in this module as slow (can be skipped with -m "not slow")
pytestmark = pytest.mark.slow


@pytest.fixture(scope="session")
def contract_test_dir() -> Generator[Path, None, None]:
    """Session-scoped temp directory for contract test artifacts.
    
    All contract test outputs are stored here for post-mortem inspection.
    Use /scratch for fast NVMe access.
    """
    base_dir = Path(os.getenv("CONTRACT_TEST_DIR", "/scratch/contract-tests"))
    base_dir.mkdir(parents=True, exist_ok=True)
    
    test_dir = base_dir / f"run-{os.getpid()}"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    yield test_dir
    
    # Cleanup after all tests (can be disabled with KEEP_CONTRACT_ARTIFACTS=1)
    if not os.getenv("KEEP_CONTRACT_ARTIFACTS"):
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def synthetic_uvh5_files(contract_test_dir: Path) -> Generator[List[Path], None, None]:
    """Create a complete set of 16 synthetic UVH5 subband files.
    
    These files are realistic representations of DSA-110 correlator output:
    - 16 subbands (sb00-sb15) covering 1.28-1.53 GHz
    - 384 channels per subband
    - 63 antennas (1953 baselines including autos)
    - Complex visibilities with realistic noise
    - Proper UVW coordinates
    - DSA-110 antenna positions
    
    Yields:
        List of 16 Path objects to UVH5 files
    """
    from dsa110_contimg.simulation.make_synthetic_uvh5 import (
        TelescopeConfig,
        load_reference_layout,
        load_telescope_config,
        build_uvdata_from_scratch,
        write_subband_uvh5,
        PACKAGE_ROOT,
        CONFIG_DIR,
    )
    
    output_dir = contract_test_dir / "uvh5"
    output_dir.mkdir(exist_ok=True)
    
    # Load telescope configuration
    config_path = CONFIG_DIR / "dsa110_measured_parameters.yaml"
    layout_path = CONFIG_DIR / "reference_layout.json"
    
    if not config_path.exists():
        pytest.skip("Simulation config not found - install simulation module")
    
    layout_meta = load_reference_layout(layout_path)
    config = load_telescope_config(config_path, layout_meta, freq_order="desc")
    
    # Generate base UVData object
    # Use reduced parameters for faster tests
    config.total_duration_sec = 30.0  # 30 seconds instead of full 5 minutes
    config.num_subbands = 16
    
    uvdata = build_uvdata_from_scratch(config)
    
    # Write 16 subband files
    files = []
    timestamp = "2025-01-01T00_00_00"
    
    for sb_idx in range(16):
        sb_path = output_dir / f"{timestamp}_sb{sb_idx:02d}.hdf5"
        write_subband_uvh5(uvdata, sb_path, sb_idx, config)
        files.append(sb_path)
    
    yield files


@pytest.fixture(scope="function")
def synthetic_uvh5_minimal(tmp_path: Path) -> Generator[List[Path], None, None]:
    """Create minimal UVH5 files for fast unit-contract tests.
    
    This fixture creates smaller files (fewer times, channels) for
    quick validation without full integration overhead.
    
    Yields:
        List of 4 Path objects to UVH5 files (subbands 0-3)
    """
    from dsa110_contimg.simulation.make_synthetic_uvh5 import (
        load_reference_layout,
        load_telescope_config,
        build_uvdata_from_scratch,
        write_subband_uvh5,
        CONFIG_DIR,
    )
    
    config_path = CONFIG_DIR / "dsa110_measured_parameters.yaml"
    layout_path = CONFIG_DIR / "reference_layout.json"
    
    if not config_path.exists():
        pytest.skip("Simulation config not found")
    
    layout_meta = load_reference_layout(layout_path)
    config = load_telescope_config(config_path, layout_meta, freq_order="desc")
    
    # Minimal configuration for speed
    config.total_duration_sec = 12.88  # Single integration
    config.num_subbands = 4  # Only 4 subbands
    
    uvdata = build_uvdata_from_scratch(config)
    
    files = []
    timestamp = "2025-01-01T00_00_00"
    
    for sb_idx in range(4):
        sb_path = tmp_path / f"{timestamp}_sb{sb_idx:02d}.hdf5"
        write_subband_uvh5(uvdata, sb_path, sb_idx, config)
        files.append(sb_path)
    
    yield files


@pytest.fixture(scope="session")
def synthetic_ms(
    contract_test_dir: Path,
    synthetic_uvh5_files: List[Path],
) -> Generator[Path, None, None]:
    """Convert synthetic UVH5 to a valid Measurement Set.
    
    This fixture tests the full conversion pipeline by:
    1. Loading 16 UVH5 subband files
    2. Combining them with pyuvdata
    3. Writing to MS format
    4. Configuring for CASA imaging
    
    The resulting MS can be inspected with:
    - casatools.table
    - CASA listobs
    - Any CASA imaging task
    
    Yields:
        Path to valid Measurement Set directory
    """
    from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
    from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
    from pyuvdata import UVData
    
    output_dir = contract_test_dir / "ms"
    output_dir.mkdir(exist_ok=True)
    
    ms_path = output_dir / "synthetic_observation.ms"
    
    # Combine subbands
    combined = None
    for uvh5_path in sorted(synthetic_uvh5_files):
        uv = UVData()
        uv.read(str(uvh5_path), file_type="uvh5")
        if combined is None:
            combined = uv
        else:
            combined += uv
    
    # Write to MS
    writer = DirectSubbandWriter(
        combined,
        ms_path,
        file_list=synthetic_uvh5_files,
    )
    writer.write()
    
    # Configure for imaging
    configure_ms_for_imaging(ms_path)
    
    yield ms_path


@pytest.fixture(scope="function")
def synthetic_fits_image(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a synthetic FITS image with known sources.
    
    The image contains:
    - 5 point sources at known positions
    - Gaussian noise background
    - Standard FITS headers (WCS, beam info)
    - DSA-110 compatible pixel scale
    
    Yields:
        Path to valid FITS file
    """
    from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits
    
    fits_path = tmp_path / "synthetic_image.fits"
    
    # Create image with known sources
    sources = [
        {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 0.1, "name": "Source_A"},
        {"ra_deg": 180.1, "dec_deg": 35.1, "flux_jy": 0.05, "name": "Source_B"},
        {"ra_deg": 179.9, "dec_deg": 34.9, "flux_jy": 0.08, "name": "Source_C"},
        {"ra_deg": 180.2, "dec_deg": 35.0, "flux_jy": 0.03, "name": "Source_D"},
        {"ra_deg": 180.0, "dec_deg": 35.2, "flux_jy": 0.06, "name": "Source_E"},
    ]
    
    create_synthetic_fits(
        fits_path,
        ra_deg=180.0,
        dec_deg=35.0,
        image_size=256,
        pixel_scale_arcsec=2.0,
        noise_level_jy=0.001,
        sources=sources,
        beam_fwhm_pix=5.0,
        mark_synthetic=True,
    )
    
    yield fits_path


@pytest.fixture(scope="function")
def test_pipeline_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an in-memory-like test database with full schema.
    
    This fixture creates a real SQLite database (not mocked) that:
    - Has all pipeline tables (ms_index, images, calibration, etc.)
    - Can be queried with standard SQL
    - Validates foreign key constraints
    - Can be inspected with sqlite3 CLI
    
    Yields:
        Path to SQLite database file
    """
    from dsa110_contimg.database.unified import Database, UNIFIED_SCHEMA
    
    db_path = tmp_path / "test_pipeline.sqlite3"
    
    # Initialize with full schema using the Database class
    db = Database(db_path)
    
    # Execute the unified schema to create all tables
    db.conn.executescript(UNIFIED_SCHEMA)
    db.conn.commit()
    
    yield db_path


@pytest.fixture(scope="function")
def populated_pipeline_db(
    test_pipeline_db: Path,
    synthetic_fits_image: Path,
) -> Generator[Path, None, None]:
    """Test database pre-populated with sample records.
    
    Contains:
    - 3 MS index entries
    - 5 image records
    - 2 calibration table entries
    
    Yields:
        Path to populated SQLite database
    """
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(test_pipeline_db)
    cursor = conn.cursor()
    
    # Add MS index entries
    for i in range(3):
        cursor.execute(
            """
            INSERT INTO ms_index (
                ms_path, group_id, mid_time_mjd, dec_deg, 
                n_integrations, n_channels, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"/stage/ms/observation_{i}.ms",
                f"group_{i}",
                60000.0 + i,
                35.0 + i * 0.5,
                24,
                6144,
                datetime.now().isoformat(),
            ),
        )
    
    # Add image entries
    for i in range(5):
        cursor.execute(
            """
            INSERT INTO images (
                image_path, ms_path, field_id, rms_jy,
                peak_jy, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"/stage/images/image_{i}.fits",
                f"/stage/ms/observation_{i % 3}.ms",
                i % 24,
                0.001 * (i + 1),
                0.1 * (i + 1),
                datetime.now().isoformat(),
            ),
        )
    
    conn.commit()
    conn.close()
    
    yield test_pipeline_db
