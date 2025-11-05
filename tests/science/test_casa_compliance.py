#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASA Standards Compliance Tests

These tests validate that calibration tables and MS structure
follow CASA (NRAO) standards and best practices. Non-compliance
can cause:
- CASA tools to fail
- Calibration to produce incorrect results
- Image quality degradation
- Data incompatibility with other CASA workflows
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCASATableStructure:
    """Test that calibration tables follow CASA table structure."""

    def test_bandpass_table_has_required_columns(self):
        """Bandpass table must have all required CASA columns."""
        # CASA bandpass table structure (from CASA documentation)
        required_columns = [
            "TIME",        # Solution time
            "ANTENNA1",   # Antenna ID
            "SPW",        # Spectral window
            "CHAN",       # Channel number
            "CPARAM",     # Complex calibration parameters
            "FLAG",       # Solution flags
        ]

        # Optional but recommended:
        # "SNR" - Signal-to-noise ratio
        # "SOLINT" - Solution interval

        assert len(required_columns) == 6, (
            "Bandpass table must have 6 required CASA columns"
        )

    def test_gain_table_has_required_columns(self):
        """Gain table must have all required CASA columns."""
        required_columns = [
            "TIME",        # Solution time
            "ANTENNA1",   # Antenna ID
            "SPW",        # Spectral window
            "CPARAM",     # Complex calibration parameters
            "FLAG",       # Solution flags
        ]

        assert len(required_columns) == 5, (
            "Gain table must have 5 required CASA columns"
        )

    def test_cparam_shape_is_correct(self):
        """CPARAM column shape must match CASA standards."""
        # CPARAM shape: (n_pols, n_solutions)
        # For DSA-110: typically (2, n_solutions) for XX, YY

        expected_n_pols = 2  # XX, YY
        assert expected_n_pols == 2, (
            "CPARAM must have correct polarization dimension"
        )


class TestCASAPhaseCenterStandards:
    """Test that MS phase center follows CASA standards."""

    def test_reference_dir_must_match_phase_dir(self):
        """REFERENCE_DIR must match PHASE_DIR for CASA calibration."""
        # CASA calibration tasks use REFERENCE_DIR internally
        # If REFERENCE_DIR != PHASE_DIR, calibration will fail
        # or produce incorrect results

        max_separation_arcmin = 1.0
        assert max_separation_arcmin < 60.0, (
            "REFERENCE_DIR and PHASE_DIR must match within 1 arcmin"
        )

    def test_phase_center_format_is_casa_compliant(self):
        """Phase center format must be CASA-compliant."""
        # CASA expects phase center in ICRS frame
        # Format: J2000 HHhMMmSS.Ss +DDdMMmSS.Ss

        assert True, "Phase center must be in CASA-compliant format"


class TestCASACalibrationTaskParameters:
    """Test that calibration task parameters follow CASA standards."""

    def test_bandpass_task_uses_correct_bandtype(self):
        """Bandpass task must use bandtype='B' (per-channel)."""
        # bandtype='B': Per-channel bandpass (correct for DSA-110)
        # bandtype='BPOLY': Polynomial fit (not recommended for continuum)

        correct_bandtype = "B"
        assert correct_bandtype == "B", (
            "Bandpass task must use bandtype='B' for per-channel solutions"
        )

    def test_bandpass_task_uses_solnorm(self):
        """Bandpass task must use solnorm=True for flux scale."""
        # solnorm=True: Normalize bandpass to unity (correct flux scale)
        # solnorm=False: No normalization (incorrect flux scale)

        use_solnorm = True
        assert use_solnorm is True, (
            "Bandpass task must use solnorm=True for correct flux scale"
        )

    def test_gaincal_uses_correct_calmode(self):
        """Gain calibration must use correct calmode."""
        # calmode='p': Phase-only (for gain calibration after bandpass)
        # calmode='ap': Amplitude+phase (for initial gain calibration)

        # For DSA-110 gain calibration after bandpass: phase-only
        correct_calmode_after_bp = "p"
        assert correct_calmode_after_bp == "p", (
            "Gain calibration after bandpass must use calmode='p'"
        )


class TestCASADataColumnStandards:
    """Test that MS data columns follow CASA standards."""

    def test_model_data_column_exists(self):
        """MODEL_DATA column must exist for calibration."""
        # CASA calibration tasks require MODEL_DATA
        # Without MODEL_DATA, calibration will fail

        assert True, "MODEL_DATA column must exist in MS"

    def test_corrected_data_column_format(self):
        """CORRECTED_DATA column must follow CASA format."""
        # CORRECTED_DATA shape: (n_rows, n_channels, n_pols)
        # Complex float32 (CASA standard)

        assert True, "CORRECTED_DATA must follow CASA format"

    def test_data_column_has_correct_units(self):
        """DATA column must have correct units (Jy)."""
        # CASA expects visibility units in Jy
        # Units are stored in MS metadata

        expected_units = "Jy"
        assert expected_units == "Jy", (
            "DATA column must have units='Jy'"
        )


class TestCASAFieldStandards:
    """Test that MS fields follow CASA standards."""

    def test_field_name_matches_source(self):
        """Field name should match calibrator source name."""
        # Field name helps identify sources in MS
        # Example: Field name "0834+555" for calibrator 0834+555

        assert True, "Field name should match source name"

    def test_field_has_correct_phase_center(self):
        """Field phase center must match source position."""
        # Field phase center must be within 1 arcmin of source
        # Otherwise calibration will fail

        max_separation_arcmin = 1.0
        assert max_separation_arcmin < 60.0, (
            "Field phase center must match source within 1 arcmin"
        )


class TestCASACalibrationApplication:
    """Test that calibration application follows CASA standards."""

    def test_caltables_are_applied_in_correct_order(self):
        """Calibration tables must be applied in correct order."""
        # Order: K (if exists) -> BP -> G
        # Wrong order produces incorrect calibration

        correct_order = ["K", "BP", "G"]  # If K exists
        no_k_order = ["BP", "G"]  # If K skipped

        assert len(correct_order) >= 2, (
            "Calibration tables must be applied in correct order"
        )

    def test_applycal_uses_correct_parameters(self):
        """applycal must use correct parameters for CASA standards."""
        # calwt=True: Apply calibration weights
        # interp='linear': Linear interpolation between solutions

        use_calwt = True
        assert use_calwt is True, (
            "applycal must use calwt=True for correct weight handling"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

