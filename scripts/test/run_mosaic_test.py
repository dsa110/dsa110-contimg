#!/opt/miniforge/envs/casa6/bin/python
"""
Run the 15-minute mosaic creation pipeline with all latest features:
- MODEL_DATA seeding after calibration
- WSClean imaging with MODEL_DATA validation
- Photometry measurement
- Publishing gated on photometry completion
"""

import os
import sqlite3
from pathlib import Path

from dsa110_contimg.conversion.transit_precalc import precalculate_transits_for_calibrator
from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator
from dsa110_contimg.photometry.manager import PhotometryConfig

# Set environment
os.environ["PIPELINE_STATE_DIR"] = "/data/dsa110-contimg/state"

state_dir = Path("/data/dsa110-contimg/state")
vla_catalog_path = state_dir / "catalogs" / "vla_calibrators.sqlite3"

print("=" * 70)
print("DSA-110 15-Minute Mosaic Creation Pipeline")
print("=" * 70)
print(f"State directory: {state_dir}")
print(f"VLA catalog: {vla_catalog_path}")
print(f"Catalog exists: {vla_catalog_path.exists()}")
print("")

# Ensure transit times are pre-calculated
print("Checking transit pre-calculation...")
products_db_path = state_dir / "products.sqlite3"
products_db = ensure_products_db(products_db_path)

catalog_db = state_dir / "catalogs" / "vla_calibrators.sqlite3"
cat_conn = sqlite3.connect(str(catalog_db))
cursor = cat_conn.cursor()
cursor.execute("SELECT ra_deg, dec_deg FROM calibrators WHERE name = '0834+555'")
cal = cursor.fetchone()
cat_conn.close()

if cal:
    ra_deg, dec_deg = cal
    cursor = products_db.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM calibrator_transits 
        WHERE calibrator_name = '0834+555' AND has_data = 1
    """
    )
    existing_count = cursor.fetchone()[0]

    if existing_count == 0:
        print(f"Pre-calculating transit times for 0834+555...")
        transits_with_data = precalculate_transits_for_calibrator(
            products_db=products_db,
            calibrator_name="0834+555",
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            max_days_back=60,
        )
        print(f"✓ Pre-calculated {transits_with_data} transits with available data")
    else:
        print(f"✓ Transit times already pre-calculated ({existing_count} transits with data)")
else:
    print("ERROR: Calibrator 0834+555 not found in catalog")
    exit(1)

# Initialize orchestrator with photometry enabled
print("")
print("=" * 70)
print("Initializing MosaicOrchestrator")
print("=" * 70)

photometry_config = {
    "catalog": "nvss",
    "radius_deg": 1.0,
    "min_flux_mjy": 10.0,
    "method": "peak",
    "normalize": False,
    "detect_ese": False,
}

orchestrator = MosaicOrchestrator(
    enable_photometry=True,
    photometry_config=photometry_config,
)

print(f"✓ Photometry enabled: {orchestrator.enable_photometry}")
if orchestrator.photometry_manager:
    print(f"✓ PhotometryManager initialized")
    print(f"  - Catalog: {orchestrator.photometry_manager.default_config.catalog}")
    print(f"  - Method: {orchestrator.photometry_manager.default_config.method}")
    print(f"  - Min flux: {orchestrator.photometry_manager.default_config.min_flux_mjy} mJy")

# Verify calibrator service
if orchestrator.calibrator_service:
    sqlite_catalogs = [
        c for c in orchestrator.calibrator_service.catalogs if str(c).endswith(".sqlite3")
    ]
    if sqlite_catalogs:
        print(f"✓ Using SQLite catalog: {sqlite_catalogs[0]}")

print("")
print("=" * 70)
print("Creating 3-tile mosaic (15 minutes) centered on 0834+555")
print("=" * 70)
print("")
print("⏱️  EXPECTED WORKFLOW:")
print("1. HDF5→MS conversion (if needed)")
print("2. MODEL_DATA seeding after calibration")
print("3. Calibration solve (BP + Gain)")
print("4. MODEL_DATA validation before imaging")
print("5. WSClean imaging")
print("6. Mosaic creation")
print("7. Photometry measurement (NVSS sources)")
print("8. Publish gating (waits for photometry_status='completed')")
print("")
print("Starting pipeline...")
print("=" * 70)
print("")

try:
    mosaic_path = orchestrator.create_mosaic_centered_on_calibrator(
        calibrator_name="0834+555",
        timespan_minutes=15,
        wait_for_published=True,
        dry_run=False,
        overwrite=False,
    )

    print("")
    print("=" * 70)
    if mosaic_path:
        print(f"✓ SUCCESS: Mosaic created at: {mosaic_path}")
        print("=" * 70)

        # Verify photometry was completed
        registry_db = state_dir / "data_registry.sqlite3"
        if registry_db.exists():
            conn = sqlite3.connect(str(registry_db))
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data_id, photometry_status, photometry_job_id 
                FROM data_registry 
                WHERE data_type='mosaic' 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            )
            result = cursor.fetchone()
            conn.close()

            if result:
                data_id, phot_status, job_id = result
                print("")
                print("📊 PHOTOMETRY STATUS:")
                print(f"  - Mosaic ID: {data_id}")
                print(f"  - Photometry status: {phot_status}")
                print(f"  - Batch job ID: {job_id}")

                # Count measurements
                products_conn = sqlite3.connect(str(products_db_path))
                cursor = products_conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*), AVG(peak_jyb), AVG(peak_err_jyb)
                    FROM photometry
                    WHERE image_path LIKE ?
                """,
                    (f"%{Path(mosaic_path).name}%",),
                )
                count, avg_flux, avg_err = cursor.fetchone()
                products_conn.close()

                if count and count > 0:
                    print(f"  - Measurements: {count} sources")
                    print(f"  - Avg flux: {avg_flux:.4f} Jy/beam")
                    print(f"  - Avg error: {avg_err:.4f} Jy/beam")
                else:
                    print(f"  ⚠️  No photometry measurements found")

        print("=" * 70)
        print("✅ Pipeline completed successfully!")
    else:
        print(f"✗ FAILED: Mosaic creation returned None")
        print("=" * 70)
        exit(1)

except Exception as e:
    print("")
    print("=" * 70)
    print(f"❌ Pipeline failed with exception:")
    print(f"{type(e).__name__}: {e}")
    print("=" * 70)
    import traceback

    traceback.print_exc()
    exit(1)
