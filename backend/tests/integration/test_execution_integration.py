"""
Integration tests for the unified execution module.

Tests that InProcessExecutor and SubprocessExecutor produce consistent
results when processing synthetic UVH5 data.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, List
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pytest

from dsa110_contimg.execution import (
    ErrorCode,
    ExecutionResult,
    ExecutionTask,
    InProcessExecutor,
    SubprocessExecutor,
    get_executor,
)
from dsa110_contimg.execution.task import ResourceLimits


# ============================================================================
# Fixtures for Synthetic Data
# ============================================================================


def create_minimal_uvh5(
    filepath: Path,
    timestamp: str,
    subband_idx: int,
    nants: int = 10,
    ntimes: int = 5,
    nfreqs: int = 48,  # Match DSA-110 (48 channels per subband)
    npols: int = 2,    # Match DSA-110 (XX, YY)
) -> None:
    """Create a minimal synthetic UVH5 file for testing.

    This creates a simplified HDF5 file with the minimum structure
    needed to test the execution pipeline without requiring full
    pyuvdata simulation. The structure matches real DSA-110 files.

    Args:
        filepath: Output file path
        timestamp: ISO timestamp for the observation
        subband_idx: Subband index (0-15)
        nants: Number of antennas
        ntimes: Number of time integrations
        nfreqs: Number of frequency channels per subband
        npols: Number of polarizations
    """
    # Calculate baseline count (upper triangle, no autocorr)
    nbls = nants * (nants - 1) // 2
    nblts = nbls * ntimes

    # Parse timestamp to get JD (pyuvdata uses JD, not MJD)
    dt = datetime.fromisoformat(timestamp)
    # JD for 2000-01-01T12:00:00 is 2451545.0
    jd_2000 = 2451545.0
    dt_2000 = datetime(2000, 1, 1, 12, 0, 0)
    jd_start = jd_2000 + (dt - dt_2000).total_seconds() / 86400.0

    # Create time array (JD)
    dt_sec = 12.88  # Integration time in seconds
    time_array = np.repeat(
        jd_start + np.arange(ntimes) * dt_sec / 86400.0,
        nbls,
    )

    # Create frequency array (descending within subband, matching DSA-110)
    freq_start = 1.53e9 - subband_idx * 125e6  # ~125 MHz per subband
    freq_array = freq_start - np.arange(nfreqs) * (125e6 / nfreqs)

    # Create antenna arrays
    ant1_list = []
    ant2_list = []
    for i in range(nants):
        for j in range(i + 1, nants):
            ant1_list.append(i)
            ant2_list.append(j)

    ant1_array = np.tile(ant1_list, ntimes)
    ant2_array = np.tile(ant2_list, ntimes)

    # Create synthetic visibility data (simple point source)
    # Shape: (nblts, nspws, nfreqs, npols)
    data_array = np.ones((nblts, 1, nfreqs, npols), dtype=np.complex64) * 1.0

    # Create flag and nsample arrays
    flag_array = np.zeros((nblts, 1, nfreqs, npols), dtype=bool)
    nsample_array = np.ones((nblts, 1, nfreqs, npols), dtype=np.float32)

    # Create UVW array - MUST be consistent across subbands for pyuvdata combine
    # UVW depends on time and baseline, NOT subband, so use fixed seed
    rng_uvw = np.random.default_rng(42)  # Same seed for all subbands
    uvw_array = rng_uvw.uniform(-1000, 1000, size=(nblts, 3)).astype(np.float64)

    # Antenna positions also need to be consistent
    rng_ant = np.random.default_rng(123)  # Fixed seed for antenna positions
    antenna_positions = rng_ant.uniform(-100, 100, size=(nants, 3)).astype(np.float64)

    # LST array (radians)
    # Approximate LST from JD (simplified)
    lst_array = ((time_array - 2451545.0) * 2 * np.pi * 1.00273790935) % (2 * np.pi)

    # Write HDF5 file with UVH5 structure matching real DSA-110 files
    with h5py.File(filepath, "w") as f:
        # Header group
        header = f.create_group("Header")

        # Scalar metadata as datasets (matching real files)
        header.create_dataset("latitude", data=np.float64(37.2339))  # OVRO latitude
        header.create_dataset("longitude", data=np.float64(-118.2817))  # OVRO longitude
        header.create_dataset("altitude", data=np.float64(1222.0))  # meters
        header.create_dataset("telescope_name", data=np.bytes_("DSA-110"))
        header.create_dataset("instrument", data=np.bytes_("dsa"))
        header.create_dataset("object_name", data=np.bytes_("zenith"))
        header.create_dataset("history", data=np.bytes_("Synthetic test data"))

        # Dimensions as scalar datasets
        header.create_dataset("Nants_data", data=np.int64(nants))
        header.create_dataset("Nants_telescope", data=np.int64(nants))
        header.create_dataset("Nbls", data=np.int64(nbls))
        header.create_dataset("Nblts", data=np.int64(nblts))
        header.create_dataset("Nfreqs", data=np.int64(nfreqs))
        header.create_dataset("Npols", data=np.int64(npols))
        header.create_dataset("Nspws", data=np.int64(1))
        header.create_dataset("Ntimes", data=np.int64(ntimes))

        # Antenna info - must be consistent across subbands
        header.create_dataset("antenna_numbers", data=np.arange(nants, dtype=np.int64))
        header.create_dataset(
            "antenna_names",
            data=np.array([f"{i:03d}" for i in range(nants)], dtype="S4"),
        )
        header.create_dataset(
            "antenna_positions",
            data=antenna_positions,  # Use pre-computed consistent positions
        )
        header.create_dataset(
            "antenna_diameters",
            data=np.full(nants, 4.65, dtype=np.float64),  # DSA-110 dish size
        )

        # Frequency info
        header.create_dataset("freq_array", data=freq_array.reshape(1, -1).astype(np.float64))
        header.create_dataset("channel_width", data=np.float64(125e6 / nfreqs))
        header.create_dataset("spw_array", data=np.array([0], dtype=np.int64))

        # Polarization (-5=XX, -6=XY, -7=YX, -8=YY) - DSA-110 uses XX, YY
        if npols == 2:
            header.create_dataset("polarization_array", data=np.array([-5, -8], dtype=np.int64))
        else:
            header.create_dataset("polarization_array", data=np.array([-5, -6, -7, -8], dtype=np.int64))

        # Phase center info (matching real files)
        header.create_dataset("phase_type", data=np.bytes_("drift"))
        header.create_dataset("phase_center_app_dec", data=np.float64(0.65))  # ~37 deg

        # extra_keywords group for phase center (matching real structure)
        extra = header.create_group("extra_keywords")
        extra.create_dataset("phase_center_dec", data=np.float64(0.65))
        extra.create_dataset("phase_center_epoch", data=np.bytes_("J2000"))
        extra.create_dataset("ha_phase_center", data=np.float64(0.0))
        extra.create_dataset("applied_delays_ns", data=np.bytes_("none"))
        extra.create_dataset("fs_table", data=np.bytes_("none"))

        # Time-varying arrays in Header (matching real files)
        header.create_dataset("time_array", data=time_array.astype(np.float64))
        header.create_dataset("uvw_array", data=uvw_array)
        header.create_dataset("ant_1_array", data=ant1_array.astype(np.int64))
        header.create_dataset("ant_2_array", data=ant2_array.astype(np.int64))
        header.create_dataset(
            "integration_time",
            data=np.full(nblts, dt_sec, dtype=np.float64),
        )

        # Data group (only visdata, flags, nsamples)
        data_grp = f.create_group("Data")
        data_grp.create_dataset("visdata", data=data_array)
        data_grp.create_dataset("flags", data=flag_array)
        data_grp.create_dataset("nsamples", data=nsample_array)


def create_subband_group(
    output_dir: Path,
    timestamp: str,
    num_subbands: int = 16,
    **kwargs,
) -> List[Path]:
    """Create a complete subband group for testing.

    Args:
        output_dir: Directory to create files in
        timestamp: ISO timestamp for the observation
        num_subbands: Number of subbands to create (default: 16)
        **kwargs: Additional arguments passed to create_minimal_uvh5

    Returns:
        List of created file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []

    for sb_idx in range(num_subbands):
        filename = f"{timestamp}_sb{sb_idx:02d}.hdf5"
        filepath = output_dir / filename
        create_minimal_uvh5(filepath, timestamp, sb_idx, **kwargs)
        files.append(filepath)

    return files


def create_hdf5_index_db(db_path: Path, files: List[Path], timestamp: str) -> None:
    """Create an HDF5 index database for the given files.

    Args:
        db_path: Path to create the SQLite database
        files: List of HDF5 file paths
        timestamp: Group timestamp
    """
    conn = sqlite3.connect(db_path)
    # Use the actual schema expected by hdf5_index.py
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hdf5_file_index (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            timestamp_iso TEXT,
            group_id TEXT,
            subband_idx INTEGER,
            mid_mjd REAL,
            nblts INTEGER,
            nfreqs INTEGER,
            file_size_bytes INTEGER,
            indexed_at TEXT
        )
        """
    )

    # Parse timestamp to MJD
    dt = datetime.fromisoformat(timestamp)
    mid_mjd = (dt - datetime(1858, 11, 17)).total_seconds() / 86400.0

    for filepath in files:
        # Extract subband index from filename
        sb_str = filepath.stem.split("_sb")[1]
        sb_idx = int(sb_str)

        conn.execute(
            """
            INSERT INTO hdf5_file_index 
            (path, timestamp_iso, group_id, subband_idx, mid_mjd, nblts, nfreqs, file_size_bytes, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(filepath),
                timestamp,
                timestamp,
                sb_idx,
                mid_mjd,
                225,  # 10 antennas -> 45 baselines * 5 times
                64,
                filepath.stat().st_size if filepath.exists() else 0,
                datetime.now().isoformat(),
            ),
        )

    conn.commit()
    conn.close()


@pytest.fixture
def synthetic_subband_group(tmp_path: Path) -> Generator[dict, None, None]:
    """Fixture providing a synthetic 16-subband group for testing.

    Yields:
        Dictionary with:
        - input_dir: Path to directory containing UVH5 files
        - output_dir: Path for output MS files
        - scratch_dir: Path for temporary files
        - timestamp: ISO timestamp of the observation
        - files: List of created UVH5 file paths
        - db_path: Path to HDF5 index database
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    scratch_dir = tmp_path / "scratch"

    input_dir.mkdir()
    output_dir.mkdir()
    scratch_dir.mkdir()

    timestamp = "2025-06-01T12:00:00"
    files = create_subband_group(input_dir, timestamp, num_subbands=16)

    # Create index database
    db_path = input_dir / "hdf5_file_index.sqlite3"
    create_hdf5_index_db(db_path, files, timestamp)

    yield {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "scratch_dir": scratch_dir,
        "timestamp": timestamp,
        "files": files,
        "db_path": db_path,
        "start_time": "2025-06-01T11:00:00",
        "end_time": "2025-06-01T13:00:00",
    }


# ============================================================================
# Unit Tests for Synthetic Data Generation
# ============================================================================


class TestSyntheticDataGeneration:
    """Tests for the synthetic data generation utilities."""

    def test_create_minimal_uvh5(self, tmp_path: Path) -> None:
        """Test creating a minimal UVH5 file."""
        filepath = tmp_path / "test_sb00.hdf5"
        create_minimal_uvh5(filepath, "2025-06-01T12:00:00", 0)

        assert filepath.exists()
        assert filepath.stat().st_size > 0

        # Verify structure
        with h5py.File(filepath, "r") as f:
            assert "Header" in f
            assert "Data" in f
            assert "visdata" in f["Data"]
            assert f["Header"].attrs["Nants_data"] == 10

    def test_create_subband_group(self, tmp_path: Path) -> None:
        """Test creating a complete subband group."""
        files = create_subband_group(tmp_path, "2025-06-01T12:00:00", num_subbands=4)

        assert len(files) == 4
        for i, f in enumerate(files):
            assert f.exists()
            assert f"_sb{i:02d}.hdf5" in f.name

    def test_create_hdf5_index_db(self, tmp_path: Path) -> None:
        """Test creating HDF5 index database."""
        files = create_subband_group(tmp_path / "data", "2025-06-01T12:00:00", num_subbands=4)
        db_path = tmp_path / "index.sqlite3"
        create_hdf5_index_db(db_path, files, "2025-06-01T12:00:00")

        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT COUNT(*) FROM hdf5_file_index").fetchone()
        assert rows[0] == 4
        conn.close()


# ============================================================================
# Execution Task Tests
# ============================================================================


class TestExecutionTaskCreation:
    """Tests for creating ExecutionTask from synthetic data."""

    def test_create_task_from_fixture(self, synthetic_subband_group: dict) -> None:
        """Test creating an ExecutionTask from the fixture data."""
        data = synthetic_subband_group

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

        # Should validate without error
        task.validate()

        assert task.group_id == "2025-06-01T12:00:00"
        assert task.input_dir.exists()

    def test_task_to_cli_args(self, synthetic_subband_group: dict) -> None:
        """Test converting task to CLI arguments."""
        data = synthetic_subband_group

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            writer="parallel-subband",
        )

        args = task.to_cli_args()

        assert str(data["input_dir"].resolve()) in args
        assert str(data["output_dir"].resolve()) in args
        assert "--writer" in args
        assert "parallel-subband" in args


# ============================================================================
# InProcessExecutor Integration Tests
# ============================================================================


class TestInProcessExecutorIntegration:
    """Integration tests for InProcessExecutor with synthetic data."""

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_successful_conversion(
        self, mock_convert: MagicMock, synthetic_subband_group: dict
    ) -> None:
        """Test successful in-process conversion with mocked orchestrator."""
        data = synthetic_subband_group

        # Mock successful conversion
        mock_convert.return_value = {
            "converted": [data["timestamp"]],
            "skipped": [],
            "failed": [],
        }

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is True
        assert result.execution_mode == "inprocess"
        assert result.error_code is None or result.error_code == ErrorCode.SUCCESS
        mock_convert.assert_called_once()

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_conversion_with_failures(
        self, mock_convert: MagicMock, synthetic_subband_group: dict
    ) -> None:
        """Test in-process conversion when all groups fail."""
        data = synthetic_subband_group

        mock_convert.return_value = {
            "converted": [],
            "skipped": [],
            "failed": [{"group_id": data["timestamp"], "error": "test error"}],
        }

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.CONVERSION_ERROR

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_resource_limits_applied(
        self, mock_convert: MagicMock, synthetic_subband_group: dict
    ) -> None:
        """Test that resource limits are applied during execution."""
        data = synthetic_subband_group

        mock_convert.return_value = {
            "converted": [data["timestamp"]],
            "skipped": [],
            "failed": [],
        }

        limits = ResourceLimits(memory_mb=4096, omp_threads=2, max_workers=2)

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            resource_limits=limits,
        )

        # Capture environment during execution
        captured_env = {}

        def capture_env(*args, **kwargs):
            captured_env["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS")
            return {"converted": [data["timestamp"]], "skipped": [], "failed": []}

        mock_convert.side_effect = capture_env

        executor = InProcessExecutor()
        result = executor.run(task)

        assert result.success is True
        # OMP_NUM_THREADS should have been set to 2
        assert captured_env.get("OMP_NUM_THREADS") == "2"


# ============================================================================
# SubprocessExecutor Integration Tests
# ============================================================================


class TestSubprocessExecutorIntegration:
    """Integration tests for SubprocessExecutor with synthetic data."""

    def test_validation_error_before_spawn(self, tmp_path: Path) -> None:
        """Test that validation errors are caught before spawning subprocess."""
        task = ExecutionTask(
            group_id="test",
            input_dir=tmp_path / "nonexistent",  # Doesn't exist
            output_dir=tmp_path / "output",
            scratch_dir=tmp_path / "scratch",
            start_time="2025-06-01T12:00:00",
            end_time="2025-06-01T13:00:00",
        )

        executor = SubprocessExecutor()
        result = executor.run(task)

        assert result.success is False
        assert result.error_code == ErrorCode.VALIDATION_ERROR

    def test_command_building(self, synthetic_subband_group: dict) -> None:
        """Test that subprocess commands are built correctly."""
        data = synthetic_subband_group

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            writer="parallel-subband",
        )

        executor = SubprocessExecutor()
        cmd = executor._build_command(task)

        # Should include python, module, and 'groups' subcommand
        assert "python" in cmd[0] or "python3" in cmd[0]
        assert "-m" in cmd
        assert "dsa110_contimg.conversion.cli" in cmd
        assert "groups" in cmd

        # Should include input/output dirs
        assert str(data["input_dir"].resolve()) in cmd
        assert str(data["output_dir"].resolve()) in cmd

    def test_environment_building(self, synthetic_subband_group: dict) -> None:
        """Test that subprocess environment is built correctly."""
        data = synthetic_subband_group

        limits = ResourceLimits(omp_threads=4, mkl_threads=4)

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            resource_limits=limits,
            env_overrides={"TEST_VAR": "test_value"},
        )

        executor = SubprocessExecutor()
        env = executor._build_environment(task)

        assert env["OMP_NUM_THREADS"] == "4"
        assert env["MKL_NUM_THREADS"] == "4"
        assert env["TEST_VAR"] == "test_value"

    def test_return_code_mapping(self) -> None:
        """Test mapping of subprocess return codes to ErrorCode."""
        executor = SubprocessExecutor()

        assert executor._map_return_code(0) == ErrorCode.SUCCESS
        assert executor._map_return_code(137) == ErrorCode.OOM_ERROR  # SIGKILL
        assert executor._map_return_code(124) == ErrorCode.TIMEOUT_ERROR
        assert executor._map_return_code(2) == ErrorCode.IO_ERROR
        assert executor._map_return_code(99) == ErrorCode.GENERAL_ERROR


# ============================================================================
# Executor Factory Tests
# ============================================================================


class TestGetExecutor:
    """Tests for the get_executor factory function."""

    def test_get_inprocess_executor(self) -> None:
        """Test getting in-process executor."""
        executor = get_executor("inprocess")
        assert isinstance(executor, InProcessExecutor)

    def test_get_subprocess_executor(self) -> None:
        """Test getting subprocess executor."""
        executor = get_executor("subprocess", timeout_seconds=1800)
        assert isinstance(executor, SubprocessExecutor)
        assert executor.timeout_seconds == 1800

    def test_auto_defaults_to_inprocess(self) -> None:
        """Test that 'auto' mode defaults to in-process executor."""
        executor = get_executor("auto")
        assert isinstance(executor, InProcessExecutor)

    def test_invalid_mode_raises(self) -> None:
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Unknown execution mode"):
            get_executor("invalid")


# ============================================================================
# Execution Consistency Tests
# ============================================================================


class TestExecutionConsistency:
    """Tests verifying consistency between execution modes."""

    @patch("dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms")
    def test_same_task_same_result_structure(
        self, mock_convert: MagicMock, synthetic_subband_group: dict
    ) -> None:
        """Test that in-process execution produces consistent result structure."""
        data = synthetic_subband_group

        mock_convert.return_value = {
            "converted": [data["timestamp"]],
            "skipped": [],
            "failed": [],
        }

        task = ExecutionTask(
            group_id=data["timestamp"],
            input_dir=data["input_dir"],
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

        executor = InProcessExecutor()
        result = executor.run(task)

        # Verify result structure
        assert hasattr(result, "success")
        assert hasattr(result, "return_code")
        assert hasattr(result, "execution_mode")
        assert hasattr(result, "metrics")

        # Verify result can be serialized
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "return_code" in result_dict

    def test_validation_consistent_across_executors(
        self, synthetic_subband_group: dict
    ) -> None:
        """Test that both executors validate tasks consistently."""
        data = synthetic_subband_group

        # Create invalid task (nonexistent input dir)
        invalid_task = ExecutionTask(
            group_id="test",
            input_dir=data["input_dir"].parent / "nonexistent",
            output_dir=data["output_dir"],
            scratch_dir=data["scratch_dir"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )

        inprocess = InProcessExecutor()
        subprocess_exec = SubprocessExecutor()

        inprocess_result = inprocess.run(invalid_task)
        subprocess_result = subprocess_exec.run(invalid_task)

        # Both should fail with VALIDATION_ERROR
        assert inprocess_result.success is False
        assert subprocess_result.success is False
        assert inprocess_result.error_code == ErrorCode.VALIDATION_ERROR
        assert subprocess_result.error_code == ErrorCode.VALIDATION_ERROR
