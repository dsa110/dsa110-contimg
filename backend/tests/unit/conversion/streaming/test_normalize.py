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
)


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
        """Test file that already has correct name."""
        # Create file with correct name
        file_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        file_path.touch()
        
        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00"
        )
        
        assert new_path == file_path
        assert was_renamed is False
        assert file_path.exists()
    
    def test_needs_rename(self, tmp_path: Path):
        """Test file that needs to be renamed."""
        # Create file with different timestamp
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.write_text("test content")
        
        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00"
        )
        
        assert new_path == tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert was_renamed is True
        assert new_path.exists()
        assert not file_path.exists()
        assert new_path.read_text() == "test content"
    
    def test_dry_run(self, tmp_path: Path):
        """Test dry run doesn't actually rename."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.touch()
        
        new_path, was_renamed = normalize_subband_path(
            file_path, "2025-01-15T12:00:00", dry_run=True
        )
        
        assert new_path == tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert was_renamed is True
        # Original file should still exist
        assert file_path.exists()
        # New path should NOT exist
        assert not new_path.exists()
    
    def test_invalid_pattern(self, tmp_path: Path):
        """Test file with invalid name pattern."""
        file_path = tmp_path / "not_a_subband.hdf5"
        file_path.touch()
        
        with pytest.raises(ValueError, match="does not match subband pattern"):
            normalize_subband_path(file_path, "2025-01-15T12:00:00")
    
    def test_file_not_found(self, tmp_path: Path):
        """Test handling of non-existent file."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        # Don't create the file
        
        with pytest.raises(FileNotFoundError):
            normalize_subband_path(file_path, "2025-01-15T12:00:00")
    
    def test_target_exists(self, tmp_path: Path):
        """Test handling when target file already exists."""
        source_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        target_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        
        source_path.write_text("source content")
        target_path.write_text("target content")
        
        with pytest.raises(OSError, match="already exists"):
            normalize_subband_path(source_path, "2025-01-15T12:00:00")


class TestNormalizeSubbandOnIngest:
    """Tests for normalize_subband_on_ingest."""
    
    def test_no_rename_needed(self, tmp_path: Path):
        """Test when source matches target group."""
        file_path = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        file_path.touch()
        
        result = normalize_subband_on_ingest(
            path=file_path,
            target_group_id="2025-01-15T12:00:00",
            source_group_id="2025-01-15T12:00:00",
        )
        
        assert result == file_path
    
    def test_rename_succeeds(self, tmp_path: Path):
        """Test successful rename during ingest."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        file_path.touch()
        
        result = normalize_subband_on_ingest(
            path=file_path,
            target_group_id="2025-01-15T12:00:00",
            source_group_id="2025-01-15T12:00:01",
        )
        
        expected = tmp_path / "2025-01-15T12:00:00_sb05.hdf5"
        assert result == expected
        assert expected.exists()
        assert not file_path.exists()
    
    def test_rename_failure_returns_original(self, tmp_path: Path):
        """Test that rename failure returns original path."""
        file_path = tmp_path / "2025-01-15T12:00:01_sb05.hdf5"
        # Don't create file - this will cause rename to fail
        
        result = normalize_subband_on_ingest(
            path=file_path,
            target_group_id="2025-01-15T12:00:00",
            source_group_id="2025-01-15T12:00:01",
        )
        
        # Should return original path on failure
        assert result == file_path


class TestNormalizeDirectory:
    """Tests for normalize_directory."""
    
    def test_empty_directory(self, tmp_path: Path):
        """Test empty directory."""
        stats = normalize_directory(tmp_path)
        
        assert stats["files_scanned"] == 0
        assert stats["files_renamed"] == 0
        assert stats["groups_found"] == 0
        assert stats["errors"] == []
    
    def test_single_group_no_rename(self, tmp_path: Path):
        """Test single group where all files already match."""
        for sb in range(16):
            (tmp_path / f"2025-01-15T12:00:00_sb{sb:02d}.hdf5").touch()
        
        stats = normalize_directory(tmp_path, dry_run=True)
        
        assert stats["files_scanned"] == 16
        assert stats["files_renamed"] == 0
        assert stats["groups_found"] == 1
    
    def test_single_group_with_renames(self, tmp_path: Path):
        """Test single group with mixed timestamps."""
        # First 8 subbands at T12:00:00
        for sb in range(8):
            (tmp_path / f"2025-01-15T12:00:00_sb{sb:02d}.hdf5").touch()
        
        # Next 8 subbands at T12:00:01 (1 second later)
        for sb in range(8, 16):
            (tmp_path / f"2025-01-15T12:00:01_sb{sb:02d}.hdf5").touch()
        
        stats = normalize_directory(tmp_path, dry_run=True)
        
        assert stats["files_scanned"] == 16
        assert stats["files_renamed"] == 8  # The 8 files at T12:00:01
        assert stats["groups_found"] == 1
    
    def test_two_separate_groups(self, tmp_path: Path):
        """Test two groups far apart in time."""
        # Group 1 at T12:00:00
        for sb in range(16):
            (tmp_path / f"2025-01-15T12:00:00_sb{sb:02d}.hdf5").touch()
        
        # Group 2 at T13:00:00 (1 hour later - outside tolerance)
        for sb in range(16):
            (tmp_path / f"2025-01-15T13:00:00_sb{sb:02d}.hdf5").touch()
        
        stats = normalize_directory(tmp_path, cluster_tolerance_s=60.0, dry_run=True)
        
        assert stats["files_scanned"] == 32
        assert stats["files_renamed"] == 0
        assert stats["groups_found"] == 2
    
    def test_apply_renames(self, tmp_path: Path):
        """Test actually applying renames."""
        # Create files with different timestamps
        (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").write_text("sb00")
        (tmp_path / "2025-01-15T12:00:01_sb01.hdf5").write_text("sb01")
        (tmp_path / "2025-01-15T12:00:02_sb02.hdf5").write_text("sb02")
        
        stats = normalize_directory(tmp_path, dry_run=False)
        
        assert stats["files_scanned"] == 3
        assert stats["files_renamed"] == 2
        assert stats["groups_found"] == 1
        
        # Verify files were renamed
        assert (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").exists()
        assert (tmp_path / "2025-01-15T12:00:00_sb01.hdf5").exists()
        assert (tmp_path / "2025-01-15T12:00:00_sb02.hdf5").exists()
        
        # Verify content preserved
        assert (tmp_path / "2025-01-15T12:00:00_sb01.hdf5").read_text() == "sb01"
        
        # Verify old files don't exist
        assert not (tmp_path / "2025-01-15T12:00:01_sb01.hdf5").exists()
        assert not (tmp_path / "2025-01-15T12:00:02_sb02.hdf5").exists()
    
    def test_custom_tolerance(self, tmp_path: Path):
        """Test with custom tolerance."""
        # Files 30 seconds apart
        (tmp_path / "2025-01-15T12:00:00_sb00.hdf5").touch()
        (tmp_path / "2025-01-15T12:00:30_sb01.hdf5").touch()
        
        # With default 60s tolerance, should be 1 group
        stats = normalize_directory(tmp_path, cluster_tolerance_s=60.0, dry_run=True)
        assert stats["groups_found"] == 1
        
        # With 10s tolerance, should be 2 groups
        stats = normalize_directory(tmp_path, cluster_tolerance_s=10.0, dry_run=True)
        assert stats["groups_found"] == 2
