import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dsa110.pipeline.stages.mosaicking_stage import MosaickingStage

@pytest.fixture
def mock_config():
    return {
        'mosaicking': {'mosaic_type': 'optimal', 'mosaic_nx': 1024, 'mosaic_ny': 1024},
        'paths': {'mosaics_dir': '/tmp/test_mosaics'}
    }

@pytest.fixture
def mosaicking_stage(mock_config):
    return MosaickingStage(mock_config)

@pytest.mark.asyncio
async def test_calculate_mosaic_center(mosaicking_stage):
    with patch('os.path.exists', return_value=True):
        with patch('astropy.io.fits.open') as mock_fits:
            mock_fits.return_value.__enter__.return_value = [Mock()]
            result = mosaicking_stage._calculate_mosaic_center(['test1.fits', 'test2.fits'])
            assert result is None or isinstance(result, str)

@pytest.mark.asyncio
async def test_create_mosaic_invalid_inputs(mosaicking_stage):
    result = await mosaicking_stage.create_mosaic([], [], Mock())
    assert not result['success']
    assert 'Invalid input lists' in result['error']

@pytest.mark.asyncio
async def test_assess_mosaic_quality(mosaicking_stage):
    with patch('casacore.tables.table') as mock_table:
        mock_table.return_value.__enter__.return_value.getcol.return_value = [1, 2, 3]
        result = await mosaicking_stage._assess_mosaic_quality('test.image', 'test.weight')
        assert 'overall_quality_score' in result