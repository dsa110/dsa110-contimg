"""
Tests for subband filename normalization.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from dsa110_contimg.conversion.streaming.normalize import (
    build_subband_filename,
    normalize_subband_path,
    normalize_subband_on_ingest,
    normalize_directory,
    parse_subband_info,
)


class TestParseSubbandInfo:
    """Tests for parse_subband_info."""

    def test_valid_filename(self):
        """Test parsing valid subband filename."""
        result = parse_subband_info(Path("/data/2025-01-15T12:00:00_sb05.hdf5"))
        assert result == ("2025-01-15T12:00:00", 5)

    def test_valid_filename_sb00(self):
        """Test parsing sb00."""
        result = parse_subband_info(Path("2025-01-15T12:00:00_sb00.hdf5"))
        assert result == ("2025-01-15T12:00:00", 0)

    def test_valid_filename_sb15(self):
        """Test parsing sb15."""
        result = parse_subband_info(Path("2025-01-15T12:00:00_sb15.hdf5"))
        assert result == ("2025-01-15T12:00:00", 15)

    def test_invalid_filename(self):
        """Test parsing invalid filename returns None."""
        assert parse_subband_info(Path("not_a_subband.hdf5")) is None
        assert parse_subband_info(Path("2025-01-15_sb05.hdf5")) is None


class TestBuildSubbandFilename:
    """Tests for build_subband_filename."""

    def test_basic(self):
        """Test basic filename construction."""
        result = build_subband_filename("2025-01-15T12:00:00", 5)
        assert result == "2025-01-15T12:00:00_sb05.hdf5"

    def test_zero_padded(self):
        """Test subband index is zero-padded to 2 digits."""
        assert build_subband_filename("2025-01-15T12:00:00", 0) == "2025-01-15T12:00:00_sb00.hdf5"
        assert build_subband_filename("2025-01-15T12:00:00", 15) == "2025-01-15T12:00:00_sb15.hdf5"


class TestNormalizeSubbandPath:
    """Tests for normalize_subband_path."""

    def test_already_normalized(self, tmp_path: Path):
        """Test file already has correct name."""
        file_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        file_path.touch()

        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00"
        )

        assert new_path == file_path
        assert was_renamed is False

    def test_rename_needed(self, tmp_path: Path):
        """Test file needs to be renamed."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.touch()

        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00"
        )

        assert new_path == tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert was_renamed is True
        assert new_path.exists()
        assert not file_path.exists()

    def test_dry_run(self, tmp_path: Path):
        """Test dry run doesn't actually rename."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.touch()

        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00", dry_run=True
        )

        assert new_path == tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert was_renamed is True
        assert file_path.exists()  # Still exists
        assert not new_path.exists()  # Not created

    def test_invalid_filename(self, tmp_path: Path):
        """Test ValueError on invalid filename."""
        file_path = tmp_path / "not_a_subband.hdf5"
        file_path.touch()

        with pytest.raises(ValueError, match="does not match"):
            normalize_subband_path(file_path, "2025-01-15T12:00:00")

    def test_file_not_found(self, tmp_path: Path):
        """Test FileNotFoundError on missing file."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"

        with pytest.raises(FileNotFoundError):
            normalize_subband_path(file_path, "2025-01-15T12:00:00")

    def test_target_exists(self, tmp_path: Path):
        """Test OSError when target already exists."""
        source_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        target_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        source_path.touch()
        target_path.touch()

        with pytest.raises(OSError, match="already exists"):
            normalize_subband_path(source_path, "2025-01-15T12:00:00")


class TestNormalizeSubbandOnIngest:
    """Tests for normalize_subband_on_ingest."""

    def test_no_rename_needed(self, tmp_path: Path):
        """Test when source and target group_id match."""
        file_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        file_path.touch()

        result = normalize_subband_on_ingest(
            file_path,
            target_group_id="2025-01-15T12:00:00",
            source_group_id="2025-01-15T12:00:00",
        )

        assert result == file_path

    def test_rename_needed(self, tmp_path: Path):
        """Test when rename is needed."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.touch()

        result = normalize_subband_on_ingest(
            file_path,
            target_group_id="2025-01-15T12:00:00",
            source_group_id="2025-01-15T12:00:01",
        )

        assert result == tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert result.exists()


class TestNormalizeDirectory:
    """Tests for normalize_directory."""

    def test_empty_directory(self, tmp_path: Path):
        """Test empty directory."""
        stats = normalize_directory(tmp_path)
        assert stats["files_scanned"] == 0
        assert stats["files_renamed"] == 0

    def test_dry_run_default(self, tmp_path: Path):
        """Test dry_run is True by default."""
        (tmp_path / "2025-01-15T12:00:01_sb05.hdf5").touch()
        (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").touch()

        stats = normalize_directory(tmp_path)  # dry_run=True by default

        # File should still have old name
        assert (tmp_path / "2025-01-15T12:00:01_sb05.hdf5").exists()

    def test_actual_rename(self, tmp_path: Path):
        """Test actual file renaming."""
        (tmp_path / "2025-01-15T12:00:01_sb05.hdf5").touch()
        (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").touch()

        stats = normalize_directory(tmp_path, dry_run=False)

        assert stats["files_scanned"] == 2
        assert stats["files_renamed"] == 1
        assert (tmp_path / "2025-01-15T12:00:00_sb05.hdf5").exists()
        assert not (tmp_path / "2025-01-15T12:00:01_sb05.hdf5").exists()

    def test_custom_tolerance(self, tmp_path: Path):
        """Test custom cluster tolerance."""
        # Files 70 seconds apart
        (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").touch()
        (tmp_path / "2025-01-15T12:01:10_sb01.hdf5").touch()

        # With 60s tolerance, should be separate groups
        stats = normalize_directory(tmp_path, cluster_tolerance_s=60.0, dry_run=True)
        assert stats["groups_found"] == 2
        assert stats["files_renamed"] == 0

        # With 90s tolerance, should be same group
        stats = normalize_directory(tmp_path, cluster_tolerance_s=90.0, dry_run=True)
        assert stats["groups_found"] == 1
        assert stats["files_renamed"] == 1

    def test_not_a_directory(self, tmp_path: Path):
        """Test ValueError when path is not a directory."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="Not a directory"):
            normalize_directory(file_path)
