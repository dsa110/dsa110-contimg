"""
Unit tests for the synthetic UVH5 generator.

Tests data generation, validation, and integration with conversion pipeline.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
from pyuvdata import UVData


def test_import_simulation_module():
    """Test that simulation module can be imported."""
    import sys
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root / 'simulation'))
    
    import make_synthetic_uvh5
    assert hasattr(make_synthetic_uvh5, 'main')
    assert hasattr(make_synthetic_uvh5, 'write_subband_uvh5')


def test_reference_layout_json_exists():
    """Test that reference layout JSON file exists and is valid."""
    layout_path = Path(__file__).resolve().parents[3] / 'simulation' / 'config' / 'reference_layout.json'
    assert layout_path.exists(), f"Reference layout not found at {layout_path}"
    
    with open(layout_path) as f:
        layout = json.load(f)
    
    # Check required fields
    assert 'channel_width_hz' in layout
    assert 'freq_array_hz' in layout
    assert 'integration_time_sec' in layout
    
    # Validate data types
    assert isinstance(layout['channel_width_hz'], (int, float))
    assert isinstance(layout['freq_array_hz'], list)
    assert isinstance(layout['integration_time_sec'], (int, float))
    
    # Check reasonable values
    assert layout['channel_width_hz'] != 0
    assert len(layout['freq_array_hz']) > 0
    assert layout['integration_time_sec'] > 0


def test_telescope_yaml_exists():
    """Test that telescope configuration YAML exists."""
    telescope_path = Path(__file__).resolve().parents[3] / 'simulation' / 'pyuvsim' / 'telescope.yaml'
    assert telescope_path.exists(), f"Telescope config not found at {telescope_path}"


@pytest.mark.skipif(not Path('/workspaces/dsa110-contimg/simulation/make_synthetic_uvh5.py').exists(),
                    reason="Simulation script not found")
def test_synthetic_uvh5_cli_help():
    """Test that CLI help works."""
    import subprocess
    import sys
    
    script_path = Path(__file__).resolve().parents[3] / 'simulation' / 'make_synthetic_uvh5.py'
    result = subprocess.run(
        [sys.executable, str(script_path), '--help'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower() or 'Synthetic DSA-110' in result.stdout


def test_validate_freq_array_structure():
    """Test frequency array structure from reference layout."""
    layout_path = Path(__file__).resolve().parents[3] / 'simulation' / 'config' / 'reference_layout.json'
    
    with open(layout_path) as f:
        layout = json.load(f)
    
    freq_array = np.array(layout['freq_array_hz'])
    channel_width = layout['channel_width_hz']
    
    # Check for descending order (negative channel width)
    if channel_width < 0:
        assert freq_array[0] > freq_array[-1], "Frequencies should be descending for negative channel width"
        # Check that frequencies decrease monotonically
        assert np.all(np.diff(freq_array) < 0), "Frequencies should decrease monotonically"
    else:
        assert freq_array[0] < freq_array[-1], "Frequencies should be ascending for positive channel width"
        assert np.all(np.diff(freq_array) > 0), "Frequencies should increase monotonically"
    
    # Check channel spacing
    freq_diffs = np.diff(freq_array)
    expected_diff = abs(channel_width)
    # Allow small numerical errors
    assert np.allclose(np.abs(freq_diffs), expected_diff, rtol=1e-5), \
        f"Channel spacing should be uniform: {expected_diff} Hz"


def test_subband_filename_pattern():
    """Test that subband filename pattern is correct."""
    from datetime import datetime
    
    timestamp = datetime(2025, 10, 6, 12, 0, 0)
    timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
    
    for sb_idx in range(16):
        filename = f"{timestamp_str}_sb{sb_idx:02d}.hdf5"
        
        # Verify format
        assert filename.startswith('2025-10-06T12:00:00_sb')
        assert filename.endswith('.hdf5')
        assert f'_sb{sb_idx:02d}' in filename


def test_integration_time_reasonable():
    """Test that integration time is reasonable for DSA-110."""
    layout_path = Path(__file__).resolve().parents[3] / 'simulation' / 'config' / 'reference_layout.json'
    
    with open(layout_path) as f:
        layout = json.load(f)
    
    int_time = layout['integration_time_sec']
    
    # DSA-110 typical integration time is ~12-13 seconds
    assert 10.0 < int_time < 20.0, f"Integration time {int_time}s seems unusual for DSA-110"


@pytest.mark.slow
@pytest.mark.skipif(not Path('/workspaces/dsa110-contimg/simulation/make_synthetic_uvh5.py').exists(),
                    reason="Simulation script not found")
def test_generate_single_subband(tmp_path):
    """Test generating a single subband file (if template available)."""
    import sys
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root / 'simulation'))
    
    # Check if template exists
    template_path = project_root / 'output' / 'ms' / 'test_8subbands_concatenated.hdf5'
    if not template_path.exists():
        pytest.skip(f"Template file not found: {template_path}")
    
    import make_synthetic_uvh5
    from astropy.time import Time
    
    # Load configurations
    layout_path = project_root / 'simulation' / 'config' / 'reference_layout.json'
    telescope_path = project_root / 'simulation' / 'pyuvsim' / 'telescope.yaml'
    
    layout_meta = make_synthetic_uvh5.load_reference_layout(layout_path)
    config = make_synthetic_uvh5.load_telescope_config(telescope_path, layout_meta, 'desc')
    
    # Load template
    uv_template = UVData()
    uv_template.read(str(template_path), file_type='uvh5', run_check=False,
                     run_check_acceptability=False, strict_uvw_antpos_check=False)
    
    # Generate time/UVW arrays
    start_time = Time('2025-10-06T12:00:00', format='isot', scale='utc')
    unique_times, time_array, lst_array, integration_time = \
        make_synthetic_uvh5.build_time_arrays(config, uv_template, start_time)
    uvw_array = make_synthetic_uvh5.build_uvw(uv_template, config, unique_times)
    
    # Write single subband
    output_path = make_synthetic_uvh5.write_subband_uvh5(
        subband_index=0,
        template=uv_template,
        config=config,
        start_time=start_time,
        times_mjd=time_array,
        lst_array=lst_array,
        integration_time=integration_time,
        uvw_array=uvw_array,
        amplitude_jy=25.0,
        output_dir=tmp_path
    )
    
    # Verify file was created
    assert output_path.exists()
    assert output_path.suffix == '.hdf5'
    assert '_sb00.hdf5' in output_path.name
    
    # Verify file can be read
    uv_test = UVData()
    uv_test.read(str(output_path), file_type='uvh5', run_check=False,
                 strict_uvw_antpos_check=False)
    
    # Verify metadata
    assert uv_test.Nants_telescope == uv_template.Nants_telescope
    assert uv_test.Npols == uv_template.Npols
    assert uv_test.Nfreqs == config.channels_per_subband
    assert uv_test.Ntimes == uv_template.Ntimes


def test_schema_validation():
    """Test JSON schema validation for reference layout."""
    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    schema_path = Path(__file__).resolve().parents[3] / 'simulation' / 'config' / 'schema.json'
    layout_path = Path(__file__).resolve().parents[3] / 'simulation' / 'config' / 'reference_layout.json'
    
    if not schema_path.exists():
        pytest.skip(f"Schema file not found: {schema_path}")
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    with open(layout_path) as f:
        layout = json.load(f)
    
    # This should not raise
    validate(instance=layout, schema=schema)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
