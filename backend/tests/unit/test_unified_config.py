"""
Tests for unified Pydantic Settings configuration.

Tests verify:
- Default values load correctly
- Environment variable overrides work
- Type coercion is correct
- Validation catches errors

Note: Each test creates a fresh Settings instance to avoid cached singleton issues.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before each test."""
    from dsa110_contimg.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestPathSettings:
    """Tests for PathSettings domain."""
    
    def test_default_paths(self):
        """Default paths should be set correctly."""
        from dsa110_contimg.config import PathSettings
        
        paths = PathSettings()
        
        assert paths.input_dir == Path("/data/incoming")
        assert paths.scratch_dir == Path("/stage/dsa110-contimg")
        assert paths.state_dir == Path("/data/dsa110-contimg/state/db")
    
    def test_scratch_subdirs_default_to_scratch(self):
        """Subdirectories should default to scratch_dir children."""
        from dsa110_contimg.config import PathSettings
        
        paths = PathSettings()
        
        assert paths.ms_dir == Path("/stage/dsa110-contimg/ms")
        assert paths.caltables_dir == Path("/stage/dsa110-contimg/caltables")
        assert paths.images_dir == Path("/stage/dsa110-contimg/images")
        assert paths.mosaics_dir == Path("/stage/dsa110-contimg/mosaics")
        assert paths.logs_dir == Path("/stage/dsa110-contimg/logs")
    
    def test_custom_scratch_dir_propagates(self):
        """Custom scratch_dir should propagate to subdirectories."""
        from dsa110_contimg.config import PathSettings
        
        with patch.dict(os.environ, {"CONTIMG_SCRATCH_DIR": "/custom/scratch"}):
            paths = PathSettings()
        
        assert paths.scratch_dir == Path("/custom/scratch")
        assert paths.ms_dir == Path("/custom/scratch/ms")
        assert paths.images_dir == Path("/custom/scratch/images")
    
    def test_explicit_subdir_overrides_default(self):
        """Explicit subdirectory env var should override derived default."""
        from dsa110_contimg.config import PathSettings
        
        with patch.dict(os.environ, {
            "CONTIMG_SCRATCH_DIR": "/scratch",
            "CONTIMG_MS_DIR": "/fast/nvme/ms",
        }):
            paths = PathSettings()
        
        assert paths.scratch_dir == Path("/scratch")
        assert paths.ms_dir == Path("/fast/nvme/ms")  # Explicit override
        assert paths.images_dir == Path("/scratch/images")  # Still derived


class TestDatabaseSettings:
    """Tests for DatabaseSettings domain - unified database design."""
    
    def test_default_database_paths(self):
        """Default database path should point to unified pipeline.sqlite3."""
        from dsa110_contimg.config import DatabaseSettings
        
        db = DatabaseSettings()
        
        # Unified database is the primary path
        assert db.path == Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
        assert db.timeout == 30.0
        
    def test_legacy_properties_return_unified_path(self):
        """Deprecated properties should return unified path for backwards compat."""
        from dsa110_contimg.config import DatabaseSettings
        
        db = DatabaseSettings()
        
        # All legacy properties now point to unified path
        assert db.products_db == db.path
        assert db.ingest_db == db.path
        assert db.cal_registry_db == db.path
        assert db.unified_db == db.path
    
    def test_legacy_env_var_aliases(self):
        """Legacy PIPELINE_DB env var should work."""
        from dsa110_contimg.config import DatabaseSettings
        
        with patch.dict(os.environ, {
            "PIPELINE_DB": "/custom/pipeline.sqlite3",
        }):
            db = DatabaseSettings()
        
        assert db.path == Path("/custom/pipeline.sqlite3")
        # Legacy properties also reflect this
        assert db.products_db == Path("/custom/pipeline.sqlite3")


class TestConversionSettings:
    """Tests for ConversionSettings domain."""
    
    def test_default_conversion_settings(self):
        """Conversion defaults should match DSA-110 requirements."""
        from dsa110_contimg.config import ConversionSettings
        
        conv = ConversionSettings()
        
        assert conv.expected_subbands == 16
        assert conv.chunk_minutes == 5.0
        assert conv.cluster_tolerance_s == 60.0
    
    def test_env_override(self):
        """Environment variables should override defaults."""
        from dsa110_contimg.config import ConversionSettings
        
        with patch.dict(os.environ, {"CONTIMG_EXPECTED_SUBBANDS": "8"}):
            conv = ConversionSettings()
        
        assert conv.expected_subbands == 8


class TestImagingSettings:
    """Tests for ImagingSettings domain."""
    
    def test_default_imaging_settings(self):
        """Imaging defaults should be sensible."""
        from dsa110_contimg.config import ImagingSettings
        
        img = ImagingSettings()
        
        assert img.imsize == 2048
        assert img.robust == 0.0
        assert img.niter == 10000
    
    def test_env_override(self):
        """IMG_* prefixed env vars should work."""
        from dsa110_contimg.config import ImagingSettings
        
        with patch.dict(os.environ, {"IMG_IMSIZE": "4096", "IMG_ROBUST": "-0.5"}):
            img = ImagingSettings()
        
        assert img.imsize == 4096
        assert img.robust == -0.5


class TestGPUSettings:
    """Tests for GPUSettings domain."""
    
    def test_default_gpu_enabled(self):
        """GPU should be enabled by default."""
        from dsa110_contimg.config import GPUSettings
        
        gpu = GPUSettings()
        
        assert gpu.enabled is True
        assert gpu.gridder == "idg"
        assert gpu.idg_mode == "hybrid"
    
    def test_memory_fraction_validation(self):
        """Memory fraction should be between 0 and 1."""
        from dsa110_contimg.config import GPUSettings
        
        with patch.dict(os.environ, {"PIPELINE_GPU_MEMORY_FRACTION": "0.75"}):
            gpu = GPUSettings()
            assert gpu.memory_fraction == 0.75
        
        # Invalid values should raise
        with patch.dict(os.environ, {"PIPELINE_GPU_MEMORY_FRACTION": "1.5"}):
            with pytest.raises(Exception):  # ValidationError
                GPUSettings()


class TestAPISettings:
    """Tests for APISettings domain."""
    
    def test_default_api_settings(self):
        """API defaults should be development-friendly."""
        from dsa110_contimg.config import APISettings, Environment
        
        api = APISettings()
        
        assert api.environment == Environment.DEVELOPMENT
        assert api.debug is False
        assert api.port == 8000
    
    def test_api_keys_parsing(self):
        """API keys should be parsed from comma-separated string."""
        from dsa110_contimg.config import APISettings
        
        with patch.dict(os.environ, {"DSA110_API_KEYS_CSV": "key1,key2, key3 "}):
            api = APISettings()
        
        # api_keys is now a property that parses api_keys_csv
        assert api.api_keys == {"key1", "key2", "key3"}
    
    def test_empty_api_keys(self):
        """Empty API keys env var should result in empty set."""
        from dsa110_contimg.config import APISettings
        
        with patch.dict(os.environ, {"DSA110_API_KEYS_CSV": ""}, clear=False):
            api = APISettings()
        
        assert api.api_keys == set()


class TestQASettings:
    """Tests for QASettings domain."""
    
    def test_default_qa_thresholds(self):
        """QA thresholds should have sensible defaults."""
        from dsa110_contimg.config import QASettings
        
        qa = QASettings()
        
        assert qa.ms_max_flagged == 0.5
        assert qa.cal_max_phase_scatter == 90.0
        assert qa.img_min_dynamic_range == 5.0


class TestRootSettings:
    """Tests for the root Settings class."""
    
    def test_settings_loads_all_domains(self):
        """Root settings should load all domain configs."""
        from dsa110_contimg.config import Settings
        
        settings = Settings()
        
        # Check all domains are present
        assert hasattr(settings, "paths")
        assert hasattr(settings, "database")
        assert hasattr(settings, "conversion")
        assert hasattr(settings, "calibration")
        assert hasattr(settings, "imaging")
        assert hasattr(settings, "gpu")
        assert hasattr(settings, "qa")
        assert hasattr(settings, "logging")
        assert hasattr(settings, "api")
        assert hasattr(settings, "redis")
        assert hasattr(settings, "alerting")
        assert hasattr(settings, "disk")
        assert hasattr(settings, "tls")
    
    def test_global_settings_cached(self):
        """get_settings should return cached value on multiple calls."""
        from dsa110_contimg.config import get_settings
        
        # Call twice - should return same object (cached)
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
    
    def test_production_validation_catches_auth_disabled(self):
        """Production validation should catch disabled auth."""
        from dsa110_contimg.config import Settings, Environment
        
        settings = Settings()
        settings.api.environment = Environment.PRODUCTION
        settings.api.auth_disabled = True
        
        errors = settings.validate_production()
        
        assert any("Authentication" in e for e in errors)
    
    def test_production_validation_catches_missing_api_keys(self):
        """Production validation should catch missing API keys."""
        from dsa110_contimg.config import Settings, Environment
        
        settings = Settings()
        settings.api.environment = Environment.PRODUCTION
        settings.api.api_keys_csv = ""  # Empty means no api_keys
        
        errors = settings.validate_production()
        
        assert any("API key" in e for e in errors)
    
    def test_telescope_name_default(self):
        """Telescope name should default to DSA_110 for EveryBeam."""
        from dsa110_contimg.config import Settings
        
        settings = Settings()
        
        assert settings.telescope_name == "DSA_110"


class TestConvenienceAccessors:
    """Tests for backwards compatibility accessors."""
    
    def test_get_scratch_dir(self):
        """get_scratch_dir should return paths.scratch_dir."""
        from dsa110_contimg.config import get_scratch_dir, settings
        
        assert get_scratch_dir() == settings.paths.scratch_dir
    
    def test_get_state_dir(self):
        """get_state_dir should return paths.state_dir."""
        from dsa110_contimg.config import get_state_dir, settings
        
        assert get_state_dir() == settings.paths.state_dir
    
    def test_get_unified_db_path(self):
        """get_unified_db_path should return database.unified_db."""
        from dsa110_contimg.config import get_unified_db_path, settings
        
        assert get_unified_db_path() == settings.database.unified_db


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variable handling."""
    
    def test_env_prefix_contimg(self):
        """CONTIMG_ prefixed vars should work for path settings."""
        from dsa110_contimg.config import PathSettings
        
        with patch.dict(os.environ, {
            "CONTIMG_INPUT_DIR": "/test/input",
            "CONTIMG_OUTPUT_DIR": "/test/output",
        }):
            paths = PathSettings()
        
        assert paths.input_dir == Path("/test/input")
        assert paths.output_dir == Path("/test/output")
    
    def test_env_prefix_dsa110(self):
        """DSA110_ prefixed vars should work for API settings."""
        from dsa110_contimg.config import APISettings
        
        with patch.dict(os.environ, {
            "DSA110_HOST": "127.0.0.1",
            "DSA110_PORT": "9000",
        }):
            api = APISettings()
        
        assert api.host == "127.0.0.1"
        assert api.port == 9000
    
    def test_mixed_prefixes_work(self):
        """Different prefixes for different domains should all work."""
        from dsa110_contimg.config import Settings
        
        with patch.dict(os.environ, {
            "CONTIMG_SCRATCH_DIR": "/custom/scratch",
            "DSA110_PORT": "8080",
            "IMG_IMSIZE": "1024",
            "PIPELINE_GPU_ENABLED": "false",
        }):
            settings = Settings()
        
        assert settings.paths.scratch_dir == Path("/custom/scratch")
        assert settings.api.port == 8080
        assert settings.imaging.imsize == 1024
        assert settings.gpu.enabled is False
