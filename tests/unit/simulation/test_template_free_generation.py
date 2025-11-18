"""Tests for template-free synthetic UVH5 generation."""

from pathlib import Path

import pytest
from pyuvdata import UVData

from dsa110_contimg.simulation.make_synthetic_uvh5 import (
    build_uvdata_from_scratch,
    load_reference_layout,
    load_telescope_config,
)


@pytest.fixture
def config():
    """Load test configuration."""
    repo_root = Path(__file__).resolve().parents[3]
    config_dir = repo_root / "src" / "dsa110_contimg" / "simulation" / "config"
    layout_meta = load_reference_layout(config_dir / "reference_layout.json")

    # Find telescope config
    pyuvsim_dir = config_dir.parent / "pyuvsim"
    telescope_config = pyuvsim_dir / "telescope.yaml"
    if not telescope_config.exists():
        pytest.skip("Telescope config not found")

    return load_telescope_config(telescope_config, layout_meta, "desc")


def test_build_uvdata_from_scratch(config):
    """Test building UVData from scratch without template."""
    uv = build_uvdata_from_scratch(config, nants=10, ntimes=5)

    # Check basic structure
    assert uv.Nants_telescope == 10
    assert uv.Ntimes == 5
    assert uv.Nfreqs == config.channels_per_subband
    assert uv.Npols == len(config.polarizations)

    # Check synthetic marking
    assert uv.extra_keywords.get("synthetic") is True
    assert uv.extra_keywords.get("template_free") is True

    # Check history
    assert "template-free" in uv.history.lower() or "from scratch" in uv.history.lower()


def test_template_free_generation_cli(tmp_path):
    """Test template-free generation via CLI."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "src" / "dsa110_contimg" / "simulation" / "make_synthetic_uvh5.py"

    # Run with template-free flag
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--template-free",
            "--output",
            str(tmp_path),
            "--start-time",
            "2025-01-01T00:00:00",
            "--subbands",
            "2",
            "--duration-minutes",
            "1",
            "--nants",
            "10",
            "--ntimes",
            "5",
        ],
        capture_output=True,
        text=True,
    )

    # Should succeed without template
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Check files were created
    hdf5_files = list(tmp_path.glob("*_sb*.hdf5"))
    assert len(hdf5_files) == 2, f"Expected 2 subbands, found {len(hdf5_files)}"

    # Verify files are readable
    for hdf5_file in hdf5_files:
        uv = UVData()
        uv.read(str(hdf5_file), file_type="uvh5", run_check=False)
        assert uv.extra_keywords.get("synthetic") is True


def test_provenance_marking_in_uvh5(config, tmp_path):
    """Test that synthetic UVH5 files are properly marked."""
    from astropy.time import Time

    from dsa110_contimg.simulation.make_synthetic_uvh5 import (
        build_time_arrays,
        build_uvw,
        write_subband_uvh5,
    )

    uv_template = build_uvdata_from_scratch(config, nants=10, ntimes=5)
    start_time = Time("2025-01-01T00:00:00", format="isot", scale="utc")

    nbls = uv_template.Nbls
    ntimes = uv_template.Ntimes
    unique_times, time_array, lst_array, integration_time = build_time_arrays(
        config, nbls, ntimes, start_time
    )
    uvw_array = build_uvw(
        config,
        unique_times,
        uv_template.ant_1_array[:nbls],
        uv_template.ant_2_array[:nbls],
        uv_template.Nants_telescope,
    )

    output_path = write_subband_uvh5(
        0,
        uv_template,
        config,
        start_time,
        time_array,
        lst_array,
        integration_time,
        uvw_array,
        25.0,
        tmp_path,
    )

    # Verify provenance marking
    uv = UVData()
    uv.read(str(output_path), file_type="uvh5", run_check=False)
    assert uv.extra_keywords.get("synthetic") is True
    assert uv.extra_keywords.get("synthetic_flux_jy") == 25.0
    assert "Synthetic" in uv.history
