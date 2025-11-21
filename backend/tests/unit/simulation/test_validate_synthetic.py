"""Tests for synthetic UVH5 validation helpers."""

import json
from pathlib import Path

import pytest

from dsa110_contimg.simulation.validate_synthetic import (
    validate_subband_group,
    validate_uvh5_file,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
UVH5_DIR = REPO_ROOT / "data-samples" / "uvh5"


@pytest.mark.skipif(
    not UVH5_DIR.exists(), reason="Synthetic UVH5 samples not available"
)
def test_all_sample_uvh5_files_are_valid():
    layout_path = (
        REPO_ROOT
        / "src"
        / "dsa110_contimg"
        / "simulation"
        / "config"
        / "reference_layout.json"
    )
    layout = json.loads(layout_path.read_text()) if layout_path.exists() else None
    files = sorted(UVH5_DIR.glob("*_sb??.hdf5"))
    assert files, "Expected synthetic UVH5 files in data-samples/uvh5"

    for path in files:
        ok, errors = validate_uvh5_file(path, layout_meta=layout)
        assert ok, f"{path.name} invalid: {errors}"


@pytest.mark.skipif(
    not UVH5_DIR.exists(), reason="Synthetic UVH5 samples not available"
)
def test_complete_subband_group_validates():
    layout_path = (
        REPO_ROOT
        / "src"
        / "dsa110_contimg"
        / "simulation"
        / "config"
        / "reference_layout.json"
    )
    layout = json.loads(layout_path.read_text()) if layout_path.exists() else None
    files = sorted(UVH5_DIR.glob("*_sb??.hdf5"))
    assert files, "Expected synthetic UVH5 files in data-samples/uvh5"
    timestamp = files[0].stem.split("_sb")[0]

    ok, errors = validate_subband_group(UVH5_DIR, timestamp, layout_meta=layout)
    assert ok, f"Subband group {timestamp} invalid: {errors}"
