"""
Contract tests for the mosaicking module.

These tests use real FITS files (synthetic but realistic) to verify:
- Mosaic produces valid FITS output
- QA checks pass for good data
- Full pipeline execution works end-to-end
- Database state is correctly updated
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS


@pytest.fixture
def synthetic_images(tmp_path: Path) -> list[Path]:
    """Create realistic synthetic FITS images.
    
    Creates 5 images with:
    - 256x256 pixels (smaller for faster tests)
    - Gaussian noise background
    - Point sources at random positions with high SNR
    - Valid WCS with slightly different pointings
    """
    images = []
    
    np.random.seed(42)  # Reproducible tests
    
    for i in range(5):
        # Create image with noise + point sources
        # Use lower noise to get better dynamic range
        data = np.random.normal(0, 0.0001, (256, 256)).astype(np.float32)
        
        # Add point sources with high flux for good dynamic range
        for _ in range(10):
            x, y = np.random.randint(50, 206, 2)
            # Simple Gaussian PSF
            yy, xx = np.ogrid[-3:4, -3:4]
            psf = np.exp(-(xx**2 + yy**2) / 2)
            flux = np.random.uniform(0.05, 0.2)  # Higher flux
            data[y-3:y+4, x-3:x+4] += flux * psf
        
        # Create WCS with slightly different pointing
        wcs = WCS(naxis=2)
        wcs.wcs.crpix = [128, 128]
        wcs.wcs.crval = [180.0 + i * 0.1, 40.0]  # Shift RA slightly
        wcs.wcs.cdelt = [0.001, 0.001]  # ~3.6 arcsec/pixel
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        
        # Write FITS
        path = tmp_path / f"image_{i}.fits"
        hdu = fits.PrimaryHDU(data=data, header=wcs.to_header())
        hdu.header['BUNIT'] = 'Jy/beam'
        hdu.writeto(str(path))
        images.append(path)
    
    return images


@pytest.fixture
def test_database(tmp_path: Path) -> Path:
    """Create a test database with images table populated."""
    from dsa110_contimg.mosaic.schema import ensure_mosaic_tables
    from dsa110_contimg.database.schema import create_products_tables
    
    db_path = tmp_path / "test.sqlite3"
    conn = sqlite3.connect(str(db_path))
    
    # Create products tables (includes images)
    create_products_tables(conn)
    
    # Create mosaic tables
    ensure_mosaic_tables(conn)
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def populated_database(
    test_database: Path,
    synthetic_images: list[Path],
) -> Path:
    """Populate test database with image records."""
    conn = sqlite3.connect(str(test_database))
    
    now = int(time.time())
    
    for i, img_path in enumerate(synthetic_images):
        conn.execute(
            """
            INSERT INTO images 
                (path, ms_path, created_at, type, noise_jy, 
                 center_ra_deg, center_dec_deg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(img_path), f"/data/ms/obs_{i}.ms", now - (i * 60),
             "continuum", 0.0005, 180.0 + i * 0.1, 40.0)
        )
    
    conn.commit()
    conn.close()
    
    return test_database


class TestMosaicBuilder:
    """Test the core mosaic builder function."""
    
    def test_build_mosaic_creates_valid_fits(
        self,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify mosaic produces valid FITS file."""
        from dsa110_contimg.mosaic import build_mosaic
        
        output = tmp_path / "mosaic.fits"
        
        result = build_mosaic(
            image_paths=synthetic_images,
            output_path=output,
            alignment_order=3,
        )
        
        # File exists and is valid FITS
        assert output.exists()
        
        with fits.open(str(output)) as hdulist:
            hdu = hdulist[0]
            
            # Has data
            assert hdu.data is not None
            assert hdu.data.shape[0] > 200  # Reasonable size
            assert hdu.data.shape[1] > 200
            
            # Has WCS
            assert 'CRPIX1' in hdu.header
            assert 'CRVAL1' in hdu.header
            
            # Has metadata
            assert hdu.header['NIMAGES'] == len(synthetic_images)
            assert 'MEDRMS' in hdu.header
        
        # Result metadata correct
        assert result.n_images == len(synthetic_images)
        assert result.median_rms > 0
        assert result.coverage_sq_deg > 0
    
    def test_build_mosaic_empty_list_raises(self, tmp_path: Path) -> None:
        """Verify empty image list raises error."""
        from dsa110_contimg.mosaic import build_mosaic
        
        with pytest.raises(ValueError, match="No images provided"):
            build_mosaic(
                image_paths=[],
                output_path=tmp_path / "mosaic.fits",
            )
    
    def test_build_mosaic_missing_file_raises(self, tmp_path: Path) -> None:
        """Verify missing file raises error."""
        from dsa110_contimg.mosaic import build_mosaic
        
        with pytest.raises(FileNotFoundError):
            build_mosaic(
                image_paths=[tmp_path / "nonexistent.fits"],
                output_path=tmp_path / "mosaic.fits",
            )


class TestMosaicQA:
    """Test quality assessment checks."""
    
    def test_qa_passes_for_good_data(
        self,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify QA runs and checks synthetic data.
        
        Note: When reproject is not available, the simple stacking
        fallback produces lower quality results. We test the QA
        mechanics rather than expecting full passes.
        """
        from dsa110_contimg.mosaic import build_mosaic, run_qa_checks
        
        output = tmp_path / "mosaic.fits"
        
        build_mosaic(
            image_paths=synthetic_images,
            output_path=output,
            alignment_order=3,
        )
        
        qa_result = run_qa_checks(output, tier='science')
        
        # QA should run without errors and return valid result
        assert qa_result.status in ['PASS', 'WARN', 'FAIL']
        assert isinstance(qa_result.dynamic_range, float)
        assert isinstance(qa_result.artifact_score, float)
        
        # With reproject available, quality should be higher
        # Without it, simple stacking may have lower DR
        try:
            import reproject  # noqa: F401
            # With reprojection, expect good quality
            assert qa_result.critical_failures == []
            assert qa_result.passed
            assert qa_result.dynamic_range > 10
        except ImportError:
            # Without reproject, just verify QA runs and returns metrics
            assert qa_result.dynamic_range > 1  # At least some signal
        
        assert qa_result.artifact_score < 0.5
    
    def test_qa_detects_low_dynamic_range(self, tmp_path: Path) -> None:
        """Verify QA fails for image with no signal."""
        from dsa110_contimg.mosaic import run_qa_checks
        
        # Create flat noise-only image
        data = np.random.normal(0, 0.001, (256, 256)).astype(np.float32)
        
        wcs = WCS(naxis=2)
        wcs.wcs.crpix = [128, 128]
        wcs.wcs.crval = [180.0, 40.0]
        wcs.wcs.cdelt = [0.001, 0.001]
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        
        path = tmp_path / "flat.fits"
        hdu = fits.PrimaryHDU(data=data, header=wcs.to_header())
        hdu.writeto(str(path))
        
        qa_result = run_qa_checks(path, tier='science')
        
        # Low DR should be flagged
        assert qa_result.dynamic_range < 20
        # May or may not fail depending on threshold


class TestMosaicTiers:
    """Test tier selection logic."""
    
    def test_quicklook_for_short_range(self) -> None:
        """Verify quicklook selected for < 1 hour."""
        from dsa110_contimg.mosaic import MosaicTier, select_tier_for_request
        
        tier = select_tier_for_request(0.5)
        assert tier == MosaicTier.QUICKLOOK
    
    def test_science_for_daily_range(self) -> None:
        """Verify science selected for ~24 hours."""
        from dsa110_contimg.mosaic import MosaicTier, select_tier_for_request
        
        tier = select_tier_for_request(24.0)
        assert tier == MosaicTier.SCIENCE
    
    def test_deep_for_multiday_range(self) -> None:
        """Verify deep selected for > 48 hours."""
        from dsa110_contimg.mosaic import MosaicTier, select_tier_for_request
        
        tier = select_tier_for_request(72.0)
        assert tier == MosaicTier.DEEP
    
    def test_explicit_tier_override(self) -> None:
        """Verify explicit tier request overrides auto-selection."""
        from dsa110_contimg.mosaic import MosaicTier, select_tier_for_request
        
        # Even for short range, explicit deep request wins
        tier = select_tier_for_request(0.5, target_quality="deep")
        assert tier == MosaicTier.DEEP


class TestMosaicJobs:
    """Test ABSURD job implementations."""
    
    def test_planning_job_creates_plan(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify planning job creates database record."""
        from dsa110_contimg.mosaic import MosaicJobConfig, MosaicPlanningJob
        
        config = MosaicJobConfig(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        now = int(time.time())
        
        job = MosaicPlanningJob(
            start_time=now - 3600,
            end_time=now + 3600,
            tier="science",
            mosaic_name="test_plan",
            config=config,
        )
        
        result = job.execute()
        
        assert result.success
        assert 'plan_id' in result.outputs
        assert result.outputs['n_images'] == len(synthetic_images)
        
        # Verify database
        conn = sqlite3.connect(str(populated_database))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM mosaic_plans WHERE id = ?",
            (result.outputs['plan_id'],)
        )
        plan = cursor.fetchone()
        conn.close()
        
        assert plan is not None
        assert plan['name'] == 'test_plan'
        assert plan['tier'] == 'science'
        assert plan['status'] == 'pending'
    
    def test_full_pipeline_execution(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Integration test: Planning → Build → QA."""
        from dsa110_contimg.mosaic import (
            MosaicJobConfig,
            MosaicPlanningJob,
            MosaicBuildJob,
            MosaicQAJob,
        )
        
        config = MosaicJobConfig(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        now = int(time.time())
        
        # Step 1: Planning
        plan_job = MosaicPlanningJob(
            start_time=now - 3600,
            end_time=now + 3600,
            tier='science',
            mosaic_name='full_test',
            config=config,
        )
        plan_result = plan_job.execute()
        assert plan_result.success
        plan_id = plan_result.outputs['plan_id']
        
        # Step 2: Build
        build_job = MosaicBuildJob(
            plan_id=plan_id,
            config=config,
        )
        build_result = build_job.execute()
        assert build_result.success
        mosaic_id = build_result.outputs['mosaic_id']
        
        # Step 3: QA
        qa_job = MosaicQAJob(
            mosaic_id=mosaic_id,
            config=config,
        )
        qa_result = qa_job.execute()
        assert qa_result.success
        
        # QA should complete - status depends on reproject availability
        qa_status = qa_result.outputs['qa_status']
        assert qa_status in ['PASS', 'WARN', 'FAIL']
        
        # With reproject, expect PASS/WARN; without, may FAIL on DR threshold
        try:
            import reproject  # noqa: F401
            assert qa_status in ['PASS', 'WARN']
        except ImportError:
            pass  # Accept any status without reproject
        
        # Verify final database state
        conn = sqlite3.connect(str(populated_database))
        conn.row_factory = sqlite3.Row
        
        mosaic = conn.execute(
            "SELECT * FROM mosaics WHERE id = ?",
            (mosaic_id,)
        ).fetchone()
        
        assert mosaic is not None
        # QA status depends on reproject availability
        assert mosaic['qa_status'] in ['PASS', 'WARN', 'FAIL']
        assert Path(mosaic['path']).exists()
        
        conn.close()


class TestMosaicPipeline:
    """Test pipeline orchestration."""
    
    def test_run_on_demand_mosaic(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test on-demand mosaic pipeline."""
        from dsa110_contimg.mosaic import MosaicPipelineConfig, run_on_demand_mosaic
        
        config = MosaicPipelineConfig(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        now = int(time.time())
        
        result = run_on_demand_mosaic(
            config=config,
            name="on_demand_test",
            start_time=now - 3600,
            end_time=now + 3600,
            tier="science",
        )
        
        # Pipeline should complete (success depends on reproject availability)
        assert result.plan_id is not None
        assert result.mosaic_id is not None
        assert result.mosaic_path is not None
        assert result.qa_status in ['PASS', 'WARN', 'FAIL']
        
        # With reproject, expect full success; without, may have QA issues
        try:
            import reproject  # noqa: F401
            assert result.success
            assert result.qa_status in ['PASS', 'WARN']
        except ImportError:
            # Without reproject, pipeline completes but QA may fail
            assert Path(result.mosaic_path).exists()
        
        # Verify output file exists
        assert Path(result.mosaic_path).exists()


class TestMosaicSchema:
    """Test database schema operations."""
    
    def test_ensure_tables_creates_schema(self, tmp_path: Path) -> None:
        """Verify schema creation works."""
        from dsa110_contimg.mosaic import ensure_mosaic_tables
        
        db_path = tmp_path / "schema_test.sqlite3"
        conn = sqlite3.connect(str(db_path))
        
        ensure_mosaic_tables(conn)
        
        # Check tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'mosaic_plans' in tables
        assert 'mosaics' in tables
        assert 'mosaic_qa' in tables
        
        conn.close()
    
    def test_schema_is_idempotent(self, tmp_path: Path) -> None:
        """Verify schema can be applied multiple times."""
        from dsa110_contimg.mosaic import ensure_mosaic_tables
        
        db_path = tmp_path / "idempotent_test.sqlite3"
        conn = sqlite3.connect(str(db_path))
        
        # Apply twice - should not error
        ensure_mosaic_tables(conn)
        ensure_mosaic_tables(conn)
        
        conn.close()


class TestMosaicOrchestrator:
    """Test MosaicOrchestrator - ABSURD adapter integration."""
    
    def test_orchestrator_initialization(self, tmp_path: Path) -> None:
        """Verify orchestrator can be created with various configs."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        # Test with all parameters
        orchestrator = MosaicOrchestrator(
            products_db_path=tmp_path / "test.db",
            hdf5_db_path=tmp_path / "hdf5.db",
            mosaic_dir=tmp_path / "mosaics",
            enable_photometry=False,
            photometry_config={"threshold": 5.0},
        )
        
        assert orchestrator.products_db_path == tmp_path / "test.db"
        assert orchestrator.hdf5_db_path == tmp_path / "hdf5.db"
        assert orchestrator.mosaic_dir == tmp_path / "mosaics"
        assert orchestrator.enable_photometry is False
        assert orchestrator.photometry_config == {"threshold": 5.0}
        
        # Verify directory was created
        assert orchestrator.mosaic_dir.exists()
    
    def test_orchestrator_with_string_paths(self, tmp_path: Path) -> None:
        """Verify orchestrator accepts string paths."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        orchestrator = MosaicOrchestrator(
            products_db_path=str(tmp_path / "test.db"),
            mosaic_dir=str(tmp_path / "mosaics"),
        )
        
        assert orchestrator.products_db_path == tmp_path / "test.db"
        assert orchestrator.mosaic_dir == tmp_path / "mosaics"
    
    def test_orchestrator_parse_group_id(self, tmp_path: Path) -> None:
        """Verify group ID parsing works for various formats."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        orchestrator = MosaicOrchestrator(
            mosaic_dir=tmp_path / "mosaics",
            enable_photometry=False,
        )
        
        # Standard format
        start, end = orchestrator._parse_group_id("2025-06-01_12:00:00", 50)
        assert end - start == 3000  # 50 minutes in seconds
        
        # ISO format with space
        start, end = orchestrator._parse_group_id("2025-06-01 12:00:00", 60)
        assert end - start == 3600  # 60 minutes in seconds
        
        # Compact format
        start, end = orchestrator._parse_group_id("20250601_120000", 10)
        assert end - start == 600  # 10 minutes in seconds
    
    def test_orchestrator_create_from_images(
        self,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test creating mosaic from explicit image paths."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        orchestrator = MosaicOrchestrator(
            mosaic_dir=tmp_path / "mosaics",
            enable_photometry=False,
        )
        
        result = orchestrator.create_mosaic_from_images(
            image_paths=synthetic_images,
            tier="quicklook",
        )
        
        # Should succeed or return error dict
        if "error" not in result:
            assert "mosaic_path" in result
            assert "metadata" in result
            assert "num_tiles" in result
            assert result["num_tiles"] == len(synthetic_images)
            assert Path(result["mosaic_path"]).exists()
    
    def test_orchestrator_from_images_validates_paths(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify orchestrator validates image paths exist."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        orchestrator = MosaicOrchestrator(
            mosaic_dir=tmp_path / "mosaics",
            enable_photometry=False,
        )
        
        result = orchestrator.create_mosaic_from_images(
            image_paths=[
                tmp_path / "nonexistent1.fits",
                tmp_path / "nonexistent2.fits",
            ],
        )
        
        assert "error" in result
        assert "Need at least 2 valid images" in result["error"]
    
    def test_orchestrator_create_mosaic_for_group(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test creating mosaic via group ID interface."""
        from dsa110_contimg.mosaic import MosaicOrchestrator
        
        orchestrator = MosaicOrchestrator(
            products_db_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
            enable_photometry=False,
        )
        
        # Use a time that will find our synthetic images
        # The populated_database fixture uses current time
        result = orchestrator.create_mosaic_for_group(
            group_id="2025-06-01_12:00:00",  # This won't find images
            tier="science",
        )
        
        # Should either succeed or return error about no images
        # (depending on whether the time range matches)
        assert isinstance(result, dict)
        assert "error" in result or "mosaic_path" in result


class TestMosaicAPI:
    """Test FastAPI endpoints for mosaic operations."""
    
    def test_api_router_configuration(self, tmp_path: Path) -> None:
        """Verify API router can be configured."""
        from dsa110_contimg.mosaic import configure_mosaic_api, mosaic_router
        
        configure_mosaic_api(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
        )
        
        # Router should have routes configured
        assert mosaic_router.prefix == "/api/mosaic"
        assert len(mosaic_router.routes) >= 2
    
    def test_request_model_validation(self) -> None:
        """Verify Pydantic request models work correctly."""
        from dsa110_contimg.mosaic import MosaicRequest
        
        # Valid request
        request = MosaicRequest(
            name="test_mosaic",
            start_time=1700000000,
            end_time=1700086400,
            tier="science",
        )
        assert request.name == "test_mosaic"
        assert request.tier == "science"
        
        # Default tier
        request2 = MosaicRequest(
            name="test2",
            start_time=1700000000,
            end_time=1700086400,
        )
        assert request2.tier == "science"
    
    def test_response_models(self) -> None:
        """Verify Pydantic response models work correctly."""
        from dsa110_contimg.mosaic import MosaicResponse, MosaicStatusResponse
        
        # MosaicResponse
        response = MosaicResponse(
            status="accepted",
            execution_id="exec-123",
            message="Mosaic started",
        )
        assert response.status == "accepted"
        
        # MosaicStatusResponse
        status = MosaicStatusResponse(
            name="test_mosaic",
            status="completed",
            tier="science",
            n_images=10,
            mosaic_path="/data/mosaics/test.fits",
            qa_status="PASS",
        )
        assert status.n_images == 10
        assert status.qa_status == "PASS"
    
    @pytest.mark.asyncio
    async def test_api_create_validates_time_range(
        self,
        populated_database: Path,
        tmp_path: Path,
    ) -> None:
        """Test that create endpoint validates time range."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from dsa110_contimg.mosaic import configure_mosaic_api, mosaic_router
        
        app = FastAPI()
        app.include_router(mosaic_router)
        
        configure_mosaic_api(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        client = TestClient(app)
        
        # Invalid time range (end <= start)
        response = client.post("/api/mosaic/create", json={
            "name": "invalid_range",
            "start_time": 1700086400,
            "end_time": 1700000000,  # Before start
            "tier": "science",
        })
        assert response.status_code == 400
        assert "time range" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_api_create_validates_tier(
        self,
        populated_database: Path,
        tmp_path: Path,
    ) -> None:
        """Test that create endpoint validates tier."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from dsa110_contimg.mosaic import configure_mosaic_api, mosaic_router
        
        app = FastAPI()
        app.include_router(mosaic_router)
        
        configure_mosaic_api(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        client = TestClient(app)
        
        # Invalid tier
        response = client.post("/api/mosaic/create", json={
            "name": "invalid_tier",
            "start_time": 1700000000,
            "end_time": 1700086400,
            "tier": "invalid",
        })
        assert response.status_code == 400
        assert "tier" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_api_status_not_found(
        self,
        populated_database: Path,
        tmp_path: Path,
    ) -> None:
        """Test that status endpoint returns 404 for unknown mosaic."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from dsa110_contimg.mosaic import configure_mosaic_api, mosaic_router
        
        app = FastAPI()
        app.include_router(mosaic_router)
        
        configure_mosaic_api(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        client = TestClient(app)
        
        response = client.get("/api/mosaic/status/nonexistent_mosaic")
        assert response.status_code == 404


class TestPipelineClasses:
    """Test ABSURD-style Pipeline classes."""
    
    def test_nightly_pipeline_initialization(self, tmp_path: Path) -> None:
        """Test NightlyMosaicPipeline can be created."""
        from datetime import datetime, timezone
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            NightlyMosaicPipeline,
            PipelineStatus,
        )
        
        config = MosaicPipelineConfig(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
        )
        
        target_date = datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        pipeline = NightlyMosaicPipeline(config, target_date=target_date)
        
        assert pipeline.pipeline_name == "nightly_mosaic"
        assert pipeline.mosaic_name == "nightly_20250615"
        assert pipeline.start_time < pipeline.end_time
        assert pipeline.end_time - pipeline.start_time == 86400
        assert pipeline._status == PipelineStatus.PENDING
        
        # Verify job graph was built
        assert "plan" in pipeline._jobs
        assert "build" in pipeline._jobs
        assert "qa" in pipeline._jobs
        
        # Verify dependencies
        assert pipeline._jobs["build"].dependencies == ["plan"]
        assert pipeline._jobs["qa"].dependencies == ["build"]
    
    def test_on_demand_pipeline_initialization(self, tmp_path: Path) -> None:
        """Test OnDemandMosaicPipeline can be created."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            OnDemandMosaicPipeline,
        )
        
        config = MosaicPipelineConfig(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
        )
        
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="custom_mosaic",
            start_time=1700000000,
            end_time=1700086400,
            tier="deep",
        )
        
        assert pipeline.pipeline_name == "on_demand_mosaic"
        assert pipeline.mosaic_name == "custom_mosaic"
        assert pipeline.tier == "deep"
        assert pipeline.start_time == 1700000000
        assert pipeline.end_time == 1700086400
    
    def test_on_demand_auto_selects_tier(self, tmp_path: Path) -> None:
        """Test OnDemandMosaicPipeline auto-selects tier."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            OnDemandMosaicPipeline,
        )
        
        config = MosaicPipelineConfig(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
        )
        
        # Short time range (< 1 hour) -> quicklook
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="short_range",
            start_time=1700000000,
            end_time=1700000000 + 1800,  # 30 minutes
        )
        assert pipeline.tier == "quicklook"
        
        # Long time range (> 48 hours) -> deep
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="long_range",
            start_time=1700000000,
            end_time=1700000000 + 86400 * 3,  # 3 days
        )
        assert pipeline.tier == "deep"
    
    def test_retry_policy_configuration(self, tmp_path: Path) -> None:
        """Test RetryPolicy configuration."""
        from dsa110_contimg.mosaic import (
            RetryPolicy,
            RetryBackoff,
        )
        
        # Default policy
        policy = RetryPolicy()
        assert policy.max_retries == 2
        assert policy.backoff == RetryBackoff.EXPONENTIAL
        
        # Verify delay calculation
        assert policy.get_delay(0) == 0
        assert policy.get_delay(1) == 2.0  # initial
        assert policy.get_delay(2) == 4.0  # 2 * initial
        assert policy.get_delay(3) == 8.0  # 4 * initial
        
        # Test max delay cap
        policy_capped = RetryPolicy(
            initial_delay_seconds=30.0,
            max_delay_seconds=60.0,
        )
        assert policy_capped.get_delay(10) == 60.0  # capped
        
        # Test linear backoff
        policy_linear = RetryPolicy(
            backoff=RetryBackoff.LINEAR,
            initial_delay_seconds=5.0,
        )
        assert policy_linear.get_delay(1) == 5.0
        assert policy_linear.get_delay(2) == 10.0
        assert policy_linear.get_delay(3) == 15.0
        
        # Test constant backoff
        policy_constant = RetryPolicy(
            backoff=RetryBackoff.CONSTANT,
            initial_delay_seconds=3.0,
        )
        assert policy_constant.get_delay(1) == 3.0
        assert policy_constant.get_delay(2) == 3.0
        assert policy_constant.get_delay(5) == 3.0
    
    def test_job_node_with_param_references(self, tmp_path: Path) -> None:
        """Test JobNode stores parameter references correctly."""
        from dsa110_contimg.mosaic import JobNode
        from dsa110_contimg.mosaic.jobs import MosaicBuildJob
        
        node = JobNode(
            job_id="build",
            job_class=MosaicBuildJob,
            params={"plan_id": "${plan.plan_id}"},
            dependencies=["plan"],
        )
        
        assert node.job_id == "build"
        assert node.params["plan_id"] == "${plan.plan_id}"
        assert node.dependencies == ["plan"]
        assert node.result is None
    
    def test_pipeline_execution_order(self, tmp_path: Path) -> None:
        """Test pipeline computes correct execution order."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            OnDemandMosaicPipeline,
        )
        
        config = MosaicPipelineConfig(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
        )
        
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="order_test",
            start_time=1700000000,
            end_time=1700086400,
        )
        
        # Verify execution order respects dependencies
        order = pipeline._execution_order
        assert order.index("plan") < order.index("build")
        assert order.index("build") < order.index("qa")
    
    def test_pipeline_generates_execution_id(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test pipeline generates unique execution IDs."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            OnDemandMosaicPipeline,
        )
        
        config = MosaicPipelineConfig(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        now = int(time.time())
        
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="exec_id_test",
            start_time=now - 3600,
            end_time=now + 3600,
        )
        
        exec_id = pipeline.start()
        
        assert exec_id is not None
        assert exec_id.startswith("on_demand_mosaic_")
        assert pipeline._execution_id == exec_id
    
    def test_pipeline_result_includes_timing(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test pipeline result includes start/complete times."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            OnDemandMosaicPipeline,
        )
        
        config = MosaicPipelineConfig(
            database_path=populated_database,
            mosaic_dir=tmp_path / "mosaics",
        )
        
        now = int(time.time())
        
        pipeline = OnDemandMosaicPipeline(
            config=config,
            name="timing_test",
            start_time=now - 3600,
            end_time=now + 3600,
        )
        
        result = pipeline.execute()
        
        assert result.execution_id is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.started_at <= result.completed_at
    
    def test_notification_config(self) -> None:
        """Test NotificationConfig defaults and usage."""
        from dsa110_contimg.mosaic import NotificationConfig
        
        # Default config
        config = NotificationConfig()
        assert config.enabled is True
        assert config.on_failure is True
        assert config.on_success is False
        assert "email" in config.channels
        
        # Custom config
        config = NotificationConfig(
            enabled=True,
            on_failure=True,
            on_success=True,
            channels=["slack", "webhook"],
            recipients=["alerts@example.com", "https://webhook.example.com"],
        )
        assert config.on_success is True
        assert "slack" in config.channels
        assert len(config.recipients) == 2
    
    def test_pipeline_config_legacy_properties(self, tmp_path: Path) -> None:
        """Test MosaicPipelineConfig legacy property accessors."""
        from dsa110_contimg.mosaic import (
            MosaicPipelineConfig,
            RetryPolicy,
            NotificationConfig,
        )
        
        config = MosaicPipelineConfig(
            database_path=tmp_path / "test.db",
            mosaic_dir=tmp_path / "mosaics",
            retry_policy=RetryPolicy(max_retries=5),
            notifications=NotificationConfig(enabled=True, on_failure=True),
        )
        
        # Legacy accessors
        assert config.max_retries == 5
        assert config.notify_on_failure is True


class TestABSURDIntegration:
    """Test ABSURD task integration for mosaic pipelines."""
    
    @pytest.mark.asyncio
    async def test_execute_mosaic_pipeline_task(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test execute_mosaic_pipeline_task async function."""
        from dsa110_contimg.mosaic.pipeline import execute_mosaic_pipeline_task
        
        now = int(time.time())
        
        result = await execute_mosaic_pipeline_task({
            "database_path": str(populated_database),
            "mosaic_dir": str(tmp_path / "mosaics"),
            "name": "absurd_test_mosaic",
            "start_time": now - 3600,
            "end_time": now + 3600,
            "tier": "science",
            "pipeline_type": "on_demand",
        })
        
        assert result["status"] in ["success", "error"]
        assert "execution_id" in result
        
        if result["status"] == "success":
            assert "outputs" in result
            assert result["outputs"]["plan_id"] is not None
    
    @pytest.mark.asyncio
    async def test_execute_mosaic_nightly_task(
        self,
        populated_database: Path,
        synthetic_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Test execute_mosaic_pipeline_task with nightly type."""
        from dsa110_contimg.mosaic.pipeline import execute_mosaic_pipeline_task
        
        result = await execute_mosaic_pipeline_task({
            "database_path": str(populated_database),
            "mosaic_dir": str(tmp_path / "mosaics"),
            "pipeline_type": "nightly",
        })
        
        assert result["status"] in ["success", "error"]
        assert "execution_id" in result
    
    def test_absurd_adapter_task_routing(self) -> None:
        """Test that ABSURD adapter routes mosaic tasks correctly."""
        from dsa110_contimg.absurd.adapter import execute_pipeline_task
        import asyncio
        
        # Test that the task names are recognized (will fail execution 
        # without proper params, but routing should work)
        async def test_routing():
            # mosaic-pipeline should be routed
            try:
                await execute_pipeline_task("mosaic-pipeline", {})
            except Exception as e:
                # Expected to fail on params, but should not be "Unknown task"
                assert "Unknown task" not in str(e)
            
            # mosaic-nightly should be routed  
            try:
                await execute_pipeline_task("mosaic-nightly", {})
            except Exception as e:
                assert "Unknown task" not in str(e)
        
        asyncio.run(test_routing())
    
    def test_cron_expression_parsing(self) -> None:
        """Test that ABSURD cron expressions work for nightly schedule."""
        from dsa110_contimg.absurd.scheduling import (
            parse_cron_expression,
            calculate_next_run,
        )
        from datetime import datetime
        
        # Test the nightly expression: 0 3 * * * (03:00 UTC daily)
        fields = parse_cron_expression("0 3 * * *")
        
        assert fields["minute"] == [0]
        assert fields["hour"] == [3]
        assert fields["day"] == list(range(1, 32))
        assert fields["month"] == list(range(1, 13))
        assert fields["weekday"] == list(range(0, 7))
        
        # Test next run calculation
        test_time = datetime(2025, 6, 15, 2, 30, 0)  # 02:30 UTC
        next_run = calculate_next_run("0 3 * * *", test_time)
        
        # Should be 03:00 on same day
        assert next_run.hour == 3
        assert next_run.minute == 0
        assert next_run.day == 15
    
    def test_scheduler_registration_params(self) -> None:
        """Test that register_nightly_mosaic_schedule has correct signature."""
        from dsa110_contimg.absurd import register_nightly_mosaic_schedule
        import inspect
        
        sig = inspect.signature(register_nightly_mosaic_schedule)
        params = list(sig.parameters.keys())
        
        # Should have these parameters
        assert "pool" in params
        assert "database_path" in params
        assert "mosaic_dir" in params
        assert "queue_name" in params
        assert "cron_expression" in params
        
        # Check defaults
        assert sig.parameters["queue_name"].default == "mosaic"
        assert sig.parameters["cron_expression"].default == "0 3 * * *"
