import pytest
import numpy as np
from unittest.mock import Mock, patch
from astropy.table import Table
from astropy.time import Time
from dsa110.pipeline.stages.photometry_stage import PhotometryStage

@pytest.fixture
def mock_config():
    return {
        'photometry': {'detection': {'fwhm_pixels': 3.0, 'threshold_sigma': 5.0}},
        'paths': {'photometry_dir': '/tmp/test_photometry'}
    }

@pytest.fixture
def photometry_stage(mock_config):
    return PhotometryStage(mock_config)

@pytest.fixture
def mock_sources():
    return Table({
        'id': [1, 2, 3],
        'ra': [180.0, 181.0, 182.0],
        'dec': [0.0, 1.0, 2.0],
        'flux': [0.1, 0.2, 0.3]
    })

@pytest.mark.asyncio
async def test_process_mosaic_missing_file(photometry_stage):
    result = await photometry_stage.process_mosaic('nonexistent.fits', Time.now())
    assert not result['success']
    assert 'not found' in result['error']

def test_calculate_photometry_quality_score(photometry_stage):
    metrics = {
        'flux_precision': 0.05,
        'source_detection_rate': 0.9,
        'reference_stability': 0.03,
        'warnings': [],
        'errors': []
    }
    score = photometry_stage._calculate_photometry_quality_score(metrics)
    assert 0 <= score <= 10