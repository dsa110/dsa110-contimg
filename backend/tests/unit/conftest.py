"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
The key is using sys.modules to pre-install mocks BEFORE imports happen.

NOTE: Be careful not to mock modules that are being tested. Only mock
external heavy dependencies that aren't the subject of the tests.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

# =============================================================================
# PRE-IMPORT MOCKING: Install mocks into sys.modules BEFORE any imports happen
# =============================================================================
# This is critical - patch() won't work because the module is imported
# before the patch is applied. Instead, we pre-populate sys.modules.
#
# IMPORTANT: Only mock modules that are IMPORTED BY code under test, not
# modules that ARE the code under test. For example:
# - Mock calibrator_ms_service because orchestrator.py imports it
# - DON'T mock streaming_mosaic because test_streaming_mosaic_manager_unit.py tests it


def _install_mock_if_missing(module_path: str) -> MagicMock:
    """Install a MagicMock into sys.modules if not already present."""
    if module_path not in sys.modules:
        mock = MagicMock()
        sys.modules[module_path] = mock
        return mock
    return sys.modules[module_path]


# Mock heavy calibrator imports (CASA dependencies) - used by orchestrator.py
_install_mock_if_missing("dsa110_contimg.conversion.calibrator_ms_service")

# Mock astroquery.gaia to prevent network calls during test collection/import
# The Gaia module tries to configure connections at import time
_gaia_mock = _install_mock_if_missing("astroquery.gaia")
_gaia_mock.Gaia = MagicMock()
_gaia_mock.Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"

# NOTE: We do NOT mock dsa110_contimg.photometry.manager here because:
# 1. test_manager.py directly tests PhotometryConfig, PhotometryManager, PhotometryResult
# 2. The module imports fine without CASA dependencies
# 3. Orchestrator tests that need to mock it can do so locally with patch()

# =============================================================================
# Shared fixtures for unit tests
# =============================================================================


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """Provide an isolated working directory for tests that write files."""
    workdir = tmp_path / "work"
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


@pytest.fixture
def mock_table_factory() -> Callable[[str, bool], MagicMock]:
    """
    Lightweight casacore.tables.table stand-in.

    Returns context managers that expose the minimal surface area needed by the
    imaging and NVSS seeding tests (colnames, getcol, nrows).
    """

    def _factory(path: str, readonly: bool = True) -> MagicMock:  # noqa: ARG001
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=ctx)
        ctx.__exit__ = Mock(return_value=None)
        ctx.close = MagicMock()

        path_upper = str(path).upper()

        if "SPECTRAL_WINDOW" in path_upper:
            chan_freq = np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
            chan_width = np.full_like(chan_freq, 1e6)

            def _getcol(name: str, *args, **kwargs):  # noqa: ANN001
                if name == "CHAN_FREQ":
                    return chan_freq
                if name == "CHAN_WIDTH":
                    return chan_width
                return np.array([])

            ctx.getcol = Mock(side_effect=_getcol)
            ctx.colnames.return_value = ["CHAN_FREQ", "CHAN_WIDTH"]
            ctx.nrows.return_value = 1
        elif "FIELD" in path_upper:
            ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
            ctx.colnames.return_value = ["PHASE_DIR", "NAME"]
            ctx.nrows.return_value = 1
        elif "DATA_DESCRIPTION" in path_upper:
            ctx.getcol.return_value = np.array([0])
            ctx.colnames.return_value = ["SPECTRAL_WINDOW_ID"]
            ctx.nrows.return_value = 1
        else:
            cols = [
                "DATA",
                "CORRECTED_DATA",
                "MODEL_DATA",
                "FLAG",
                "ANTENNA1",
                "ANTENNA2",
                "TIME",
                "UVW",
            ]
            ctx.colnames.return_value = cols
            ctx.nrows.return_value = 1000

            def _getcol(name: str, start: int = 0, n: int = 0):  # noqa: ANN001
                length = 100
                if name in {"DATA", "CORRECTED_DATA"}:
                    return np.ones((length, 1, 4), dtype=np.complex64)
                if name == "FLAG":
                    return np.zeros((length, 1, 4), dtype=bool)
                if name in {"ANTENNA1", "ANTENNA2"}:
                    return np.zeros(length, dtype=int)
                if name == "TIME":
                    return np.linspace(0.0, 1.0, length)
                if name == "UVW":
                    return np.column_stack(
                        [
                            np.linspace(0.0, 1000.0, length),
                            np.zeros(length),
                            np.zeros(length),
                        ]
                    )
                return np.array([])

            ctx.getcol = Mock(side_effect=_getcol)
        return ctx

    return _factory


@pytest.fixture
def mock_wsclean_subprocess() -> Callable:
    """Stub subprocess.run used by run_wsclean tests."""

    def _runner(cmd, *args, **kwargs):  # noqa: ANN001
        return SimpleNamespace(args=cmd, returncode=0, stdout="", stderr="")

    return _runner
