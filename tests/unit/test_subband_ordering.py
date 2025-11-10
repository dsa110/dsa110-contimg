#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Focused unit tests for subband ordering logic.

These tests verify that subband files are correctly sorted by subband number
(0-15) rather than by filename, which is critical for proper spectral ordering
in the MS and correct bandpass calibration.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestSubbandCodeExtraction:
    """Test subband code extraction from filenames."""

    def test_extract_sb00(self):
        """Test extraction of sb00 from filename."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        code = _extract_subband_code("2025-10-29T13:54:17_sb00.hdf5")
        assert code == "sb00", f"Expected 'sb00', got '{code}'"

    def test_extract_sb15(self):
        """Test extraction of sb15 from filename."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        code = _extract_subband_code("2025-10-29T13:54:17_sb15.hdf5")
        assert code == "sb15", f"Expected 'sb15', got '{code}'"

    def test_extract_sb03(self):
        """Test extraction of sb03 from filename with different timestamp."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        code = _extract_subband_code("2025-10-29T13:54:18_sb03.hdf5")
        assert code == "sb03", f"Expected 'sb03', got '{code}'"

    def test_extract_no_subband(self):
        """Test extraction from filename without subband code."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        code = _extract_subband_code("2025-10-29T13:54:17.hdf5")
        assert code is None, f"Expected None for file without subband, got '{code}'"


class TestSubbandSorting:
    """Test subband file sorting logic."""

    def test_sort_by_subband_number(self):
        """Test that files sort by subband number, not filename."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        # Files with mixed timestamps - should sort by subband number
        files = [
            "2025-10-29T13:54:18_sb03.hdf5",  # Later timestamp, but sb03
            "2025-10-29T13:54:17_sb00.hdf5",  # Earlier timestamp, sb00
            "2025-10-29T13:54:17_sb15.hdf5",  # Earlier timestamp, sb15
            "2025-10-29T13:54:17_sb01.hdf5",  # Earlier timestamp, sb01
            "2025-10-29T13:54:18_sb02.hdf5",  # Later timestamp, sb02
        ]

        def sort_by_subband(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            return sb_num

        sorted_files = sorted(files, key=sort_by_subband)

        # Should be sorted by subband number: 0, 1, 2, 3, 15
        expected_order = [
            "2025-10-29T13:54:17_sb00.hdf5",
            "2025-10-29T13:54:17_sb01.hdf5",
            "2025-10-29T13:54:18_sb02.hdf5",
            "2025-10-29T13:54:18_sb03.hdf5",
            "2025-10-29T13:54:17_sb15.hdf5",
        ]

        assert sorted_files == expected_order, (
            f"Files not sorted correctly by subband number.\n"
            f"Expected: {expected_order}\n"
            f"Got: {sorted_files}"
        )

    def test_sort_all_16_subbands(self):
        """Test sorting of all 16 subbands in correct order."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        # Create files for all 16 subbands with mixed timestamps
        files = []
        for sb_num in [15, 0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7]:
            # Alternate between two timestamps to test sorting
            timestamp = (
                "2025-10-29T13:54:17" if sb_num % 2 == 0 else "2025-10-29T13:54:18"
            )
            files.append(f"{timestamp}_sb{sb_num:02d}.hdf5")

        def sort_by_subband(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            return sb_num

        sorted_files = sorted(files, key=sort_by_subband)

        # Extract subband numbers from sorted files
        sorted_subbands = [
            int(_extract_subband_code(os.path.basename(f)).replace("sb", ""))
            for f in sorted_files
        ]

        # Should be 0-15 in order
        expected = list(range(16))
        assert sorted_subbands == expected, (
            f"Subbands not sorted correctly.\n"
            f"Expected: {expected}\n"
            f"Got: {sorted_subbands}"
        )

    def test_sort_handles_missing_subband(self):
        """Test that sorting handles files without subband codes gracefully."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _extract_subband_code,
        )

        files = [
            "2025-10-29T13:54:17_sb01.hdf5",
            "2025-10-29T13:54:17.hdf5",  # No subband code
            "2025-10-29T13:54:17_sb00.hdf5",
            "other_file.hdf5",  # No subband code
            "2025-10-29T13:54:17_sb02.hdf5",
        ]

        def sort_by_subband(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            return sb_num

        sorted_files = sorted(files, key=sort_by_subband)

        # Files with subband codes should come first, sorted by number
        # Files without subband codes should come last (999)
        assert sorted_files[0].endswith("_sb00.hdf5"), "sb00 should be first"
        assert sorted_files[1].endswith("_sb01.hdf5"), "sb01 should be second"
        assert sorted_files[2].endswith("_sb02.hdf5"), "sb02 should be third"
        # Files without subband codes should be at the end
        assert (
            "2025-10-29T13:54:17.hdf5" in sorted_files[-2:]
            or "other_file.hdf5" in sorted_files[-2:]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
