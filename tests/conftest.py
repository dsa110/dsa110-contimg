"""
Pytest configuration and shared fixtures for DSA-110 pipeline tests.

This module provides reusable fixtures for:
- Mock MS files and table structures
- Minimal test MS creation
- Calibration table mocks
- Common test data patterns
- Pipeline framework fixtures
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MockTableContext:
    """Mock context manager for casacore.tables.table."""

    def __init__(self, mock_data):
        """Initialize with mock data dictionary."""
        self.mock_data = mock_data
        self.mock_table = MagicMock()
        # Set up common table attributes
        self.mock_table.nrows.return_value = mock_data.get("nrows", 1000)
        self.mock_table.colnames.return_value = mock_data.get("colnames", [])

    def __enter__(self):
        return self.mock_table

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture(scope="session")
def minimal_test_ms(tmp_path_factory):
    """
    Create a minimal test MS file for integration tests.

    This fixture creates a real minimal MS using the test_utils helper.
    The MS is created once per test session and reused across tests.

    Usage:
        def test_something(minimal_test_ms):
            ms_path = minimal_test_ms
            # Use ms_path in your test
    """
    ms_path = tmp_path_factory.mktemp("test_ms") / "minimal.ms"

    try:
        from dsa110_contimg.conversion.test_utils import create_minimal_test_ms

        # Only create if it doesn't exist (for faster test runs)
        if not ms_path.exists():
            success = create_minimal_test_ms(str(ms_path), cleanup=False)
            if not success:
                pytest.skip("Failed to create minimal test MS")

        return str(ms_path)
    except ImportError:
        pytest.skip("test_utils not available")
    except Exception as e:
        pytest.skip("Could not create minimal MS: {}".format(e))


@pytest.fixture
def mock_ms_structure():
    """
    Provide a mock MS table structure for unit tests.

    Returns a dictionary with mock data that can be used to patch
    casacore.tables.table calls.

    Usage:
        def test_something(mock_ms_structure):
            with patch('casacore.tables.table') as mock_table:
                # Configure mock_table to return mock_ms_structure data
                ...
    """
    return {
        "MAIN": {
            "nrows": 10000,
            "colnames": [
                "DATA",
                "CORRECTED_DATA",
                "MODEL_DATA",
                "FLAG",
                "ANTENNA1",
                "ANTENNA2",
                "TIME",
                "UVW",
            ],
            "DATA": np.random.random((10000, 1, 4))
            + 1j * np.random.random((10000, 1, 4)),
            "CORRECTED_DATA": np.random.random((10000, 1, 4))
            + 1j * np.random.random((10000, 1, 4)),
            "FLAG": np.zeros((10000, 1, 4), dtype=bool),
            "ANTENNA1": np.random.randint(0, 10, 10000),
            "ANTENNA2": np.random.randint(0, 10, 10000),
            "TIME": np.linspace(60000, 61000, 10000),
            "UVW": np.random.random((10000, 3)) * 1000,
        },
        "SPECTRAL_WINDOW": {
            "nrows": 1,
            "colnames": ["CHAN_FREQ", "CHAN_WIDTH", "REF_FREQUENCY"],
            "CHAN_FREQ": np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]]),  # 1.4 GHz center
            "CHAN_WIDTH": np.array([[1e6, 1e6, 1e6, 1e6]]),
            "REF_FREQUENCY": np.array([1.415e9]),
        },
        "FIELD": {
            "nrows": 1,
            "colnames": ["PHASE_DIR", "NAME"],
            "PHASE_DIR": np.array(
                [[[np.radians(120.0), np.radians(45.0)]]]
            ),  # RA=120 deg, Dec=45 deg
            "NAME": np.array(["TEST_FIELD"]),
        },
        "ANTENNA": {
            "nrows": 10,
            "colnames": ["NAME", "POSITION"],
            "NAME": np.array([f"ANT{i:03d}" for i in range(10)]),
            "POSITION": np.random.random((10, 3)) * 100,
        },
        "DATA_DESCRIPTION": {
            "nrows": 1,
            "colnames": ["SPECTRAL_WINDOW_ID", "POLARIZATION_ID"],
            "SPECTRAL_WINDOW_ID": np.array([0]),
            "POLARIZATION_ID": np.array([0]),
        },
    }


@pytest.fixture
def mock_table_factory(mock_ms_structure):
    """
    Factory fixture that creates a mock table function.

    Usage:
        def test_something(mock_table_factory):
            with patch('casacore.tables.table', side_effect=mock_table_factory):
                # Your test code that uses table()
                ...
    """

    def _create_mock_table(path, readonly=True, **kwargs):
        """Create a mock table based on the path."""
        # Parse table name from path (e.g., "ms::SPECTRAL_WINDOW" -> "SPECTRAL_WINDOW")
        if "::" in path:
            table_name = path.split("::")[-1]
        else:
            table_name = "MAIN"

        # Get mock data for this table
        mock_data = mock_ms_structure.get(table_name, {})

        # Create context manager
        ctx = MockTableContext(mock_data)

        # Configure getcol to return appropriate data
        def mock_getcol(colname, startrow=0, nrow=-1):
            if colname in mock_data:
                data = mock_data[colname]
                if nrow > 0 and hasattr(data, "__len__"):
                    return (
                        data[startrow : startrow + nrow]
                        if startrow + nrow <= len(data)
                        else data[startrow:]
                    )
                return data
            # Default return values for common columns
            if colname == "CHAN_FREQ":
                return np.array([[1.4e9, 1.41e9, 1.42e9, 1.43e9]])
            if colname == "PHASE_DIR":
                return np.array([[[np.radians(120.0), np.radians(45.0)]]])
            if colname == "FLAG":
                return np.zeros((1000, 1, 4), dtype=bool)
            if colname == "DATA":
                return np.random.random((1000, 1, 4)) + 1j * np.random.random(
                    (1000, 1, 4)
                )
            if colname == "ANTENNA1":
                return np.random.randint(0, 10, 1000)
            if colname == "ANTENNA2":
                return np.random.randint(0, 10, 1000)
            if colname == "TIME":
                return np.linspace(60000, 61000, 1000)
            if colname == "UVW":
                return np.random.random((1000, 3)) * 1000
            return np.array([])

        ctx.mock_table.getcol = Mock(side_effect=mock_getcol)
        # Always return required columns for MAIN table (for validate_ms)
        if table_name == "MAIN" or "::" not in path:
            ctx.mock_table.colnames = Mock(
                return_value=[
                    "DATA",
                    "CORRECTED_DATA",
                    "MODEL_DATA",
                    "FLAG",
                    "ANTENNA1",
                    "ANTENNA2",
                    "TIME",
                    "UVW",
                ]
            )
        else:
            ctx.mock_table.colnames = Mock(return_value=mock_data.get("colnames", []))
        ctx.mock_table.nrows = Mock(return_value=mock_data.get("nrows", 1000))

        return ctx

    return _create_mock_table


@pytest.fixture
def mock_wsclean_subprocess():
    """
    Mock WSClean subprocess execution.

    Usage:
        def test_wsclean(mock_wsclean_subprocess):
            with patch('subprocess.run', side_effect=mock_wsclean_subprocess):
                # Your test code
                ...
    """

    def _mock_subprocess_run(cmd, *args, **kwargs):
        """Mock subprocess.run for WSClean."""
        # Verify WSClean command structure
        assert isinstance(cmd, list)
        assert "wsclean" in cmd[0] or any("wsclean" in str(arg) for arg in cmd)

        # Create mock result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b"WSClean completed successfully"
        mock_result.stderr = b""

        # Create mock output files
        if "-name" in cmd:
            name_idx = cmd.index("-name") + 1
            if name_idx < len(cmd):
                imagename = cmd[name_idx]
                # Create mock output files
                for ext in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
                    output_path = Path(imagename + ext)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.touch()

        return mock_result

    return _mock_subprocess_run


@pytest.fixture
def mock_casa_tasks():
    """
    Mock CASA tasks (tclean, exportfits, etc.).

    Usage:
        def test_imaging(mock_casa_tasks):
            with patch('casatasks.tclean', side_effect=mock_casa_tasks['tclean']):
                # Your test code
                ...
    """

    def mock_tclean(*args, **kwargs):
        """Mock tclean task."""
        # Verify required parameters
        assert "vis" in kwargs
        assert "imagename" in kwargs

        # Create mock output files
        imagename = kwargs["imagename"]
        for ext in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            output_path = Path(imagename + ext)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch()

    def mock_exportfits(*args, **kwargs):
        """Mock exportfits task."""
        assert "imagename" in kwargs
        assert "fitsimage" in kwargs
        # Create mock FITS file
        fits_path = Path(kwargs["fitsimage"])
        fits_path.parent.mkdir(parents=True, exist_ok=True)
        fits_path.touch()

    return {
        "tclean": mock_tclean,
        "exportfits": mock_exportfits,
    }


@pytest.fixture
def temp_work_dir(tmp_path):
    """
    Provide a temporary working directory for tests.

    Usage:
        def test_something(temp_work_dir):
            output_file = temp_work_dir / "output.ms"
            # Use output_file in your test
    """
    return tmp_path


@pytest.fixture
def sample_calibration_tables(temp_work_dir):
    """
    Create mock calibration table file paths.

    Returns a dictionary with paths to mock calibration tables.
    """
    cal_dir = temp_work_dir / "caltables"
    cal_dir.mkdir()

    return {
        "k_table": str(cal_dir / "test_kcal"),
        "bp_table": str(cal_dir / "test_bpcal"),
        "g_table": str(cal_dir / "test_gacal"),
        "gp_table": str(cal_dir / "test_gpcal"),
    }


# Pipeline framework fixtures
@pytest.fixture
def test_config():
    """Standard test configuration for pipeline tests."""
    from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig

    return PipelineConfig(
        paths=PathsConfig(
            input_dir=Path("/test/input"),
            output_dir=Path("/test/output"),
        )
    )


@pytest.fixture
def test_context(test_config):
    """Standard test context for pipeline tests."""
    from dsa110_contimg.pipeline.context import PipelineContext

    return PipelineContext(
        config=test_config,
        job_id=1,
        inputs={
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T01:00:00",
        },
    )


@pytest.fixture
def in_memory_repo():
    """In-memory state repository for fast pipeline tests."""
    from dsa110_contimg.pipeline.state import InMemoryStateRepository

    return InMemoryStateRepository()


@pytest.fixture
def sqlite_repo(tmp_path):
    """SQLite state repository with temporary database."""
    from dsa110_contimg.pipeline.state import SQLiteStateRepository

    db_path = tmp_path / "test.db"
    repo = SQLiteStateRepository(db_path)
    yield repo
    repo.close()


@pytest.fixture
def context_with_repo(test_context, in_memory_repo):
    """Context with in-memory state repository."""
    from dsa110_contimg.pipeline.context import PipelineContext

    return PipelineContext(
        config=test_context.config,
        job_id=test_context.job_id,
        inputs=test_context.inputs,
        outputs=test_context.outputs,
        metadata=test_context.metadata,
        state_repository=in_memory_repo,
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "casa: marks tests requiring CASA environment")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests (fast, mocked)")
