"""
Data models for the streaming conversion pipeline.

This module defines the core data structures used throughout the pipeline:
- SubbandGroup: A complete observation packet of 16 subbands
- ConversionResult: Result of converting a group to MS
- ProcessingState: State machine for group processing

These models provide type safety and a single source of truth for group data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ProcessingState(str, Enum):
    """Processing states for a subband group."""
    
    COLLECTING = "collecting"  # Still receiving subbands
    PENDING = "pending"        # Complete, waiting for conversion
    CONVERTING = "converting"  # Conversion in progress
    COMPLETED = "completed"    # Successfully converted
    FAILED = "failed"          # Conversion failed
    
    @classmethod
    def from_string(cls, value: str) -> "ProcessingState":
        """Parse state from string, with fallback."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.COLLECTING


class ProcessingStage(str, Enum):
    """Detailed processing stage within conversion."""
    
    COLLECTING = "collecting"
    VALIDATING = "validating"
    LOADING = "loading"
    PHASING = "phasing"
    WRITING = "writing"
    CALIBRATING = "calibrating"
    IMAGING = "imaging"
    COMPLETE = "complete"
    ERROR = "error"


# Pattern to extract subband index from filename
SUBBAND_PATTERN = re.compile(r"_sb(\d{2})\.hdf5$")


def extract_subband_index(path: Path) -> Optional[int]:
    """Extract subband index from a filename.
    
    Args:
        path: Path to HDF5 file
        
    Returns:
        Subband index (0-15) or None if pattern doesn't match
        
    Example:
        >>> extract_subband_index(Path("2025-10-02T00:12:00_sb05.hdf5"))
        5
    """
    match = SUBBAND_PATTERN.search(path.name)
    if match:
        return int(match.group(1))
    return None


@dataclass
class SubbandGroup:
    """A complete observation packet of 16 subbands.
    
    This is the primary data structure passed through the pipeline.
    It encapsulates all information about a group of HDF5 subband files
    that will be converted to a single Measurement Set.
    
    Attributes:
        group_id: Timestamp-based identifier (e.g., "2025-10-02T00:12:00")
        files: List of paths to subband files, ordered by index
        expected_subbands: Number of subbands expected (default 16)
        state: Current processing state
        stage: Detailed processing stage
        received_at: When the first subband was received
        last_update: When the group was last modified
        chunk_minutes: Duration of observation in minutes
        has_calibrator: Whether a calibrator is in field
        calibrators: List of calibrator names if detected
        ms_path: Path to output MS (if converted)
        error: Error message (if failed)
        error_message: Detailed error message
        retry_count: Number of retry attempts
        checkpoint_path: Path to checkpoint file for recovery
        metrics: Performance metrics from processing
        
    Example:
        >>> group = SubbandGroup(
        ...     group_id="2025-10-02T00:12:00",
        ...     files=[Path(f"/data/2025-10-02T00:12:00_sb{i:02d}.hdf5") for i in range(16)],
        ... )
        >>> group.is_complete
        True
        >>> group.missing_subbands
        []
    """
    
    group_id: str
    files: List[Path] = field(default_factory=list)
    expected_subbands: int = 16
    
    # State tracking
    state: ProcessingState = ProcessingState.COLLECTING
    stage: ProcessingStage = ProcessingStage.COLLECTING
    
    # Timestamps
    received_at: Optional[datetime] = None
    last_update: Optional[datetime] = None
    chunk_minutes: float = 5.0
    
    # Calibrator detection
    has_calibrator: Optional[bool] = None
    calibrators: Optional[List[str]] = None
    
    # Processing results
    ms_path: Optional[Path] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    checkpoint_path: Optional[Path] = None
    
    # Performance metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Normalize types after initialization."""
        # Ensure files are Path objects
        self.files = [Path(f) if not isinstance(f, Path) else f for f in self.files]
        
        # Ensure state is enum
        if isinstance(self.state, str):
            self.state = ProcessingState.from_string(self.state)
            
        # Ensure ms_path is Path if set
        if self.ms_path and not isinstance(self.ms_path, Path):
            self.ms_path = Path(self.ms_path)
            
        # Ensure checkpoint_path is Path if set
        if self.checkpoint_path and not isinstance(self.checkpoint_path, Path):
            self.checkpoint_path = Path(self.checkpoint_path)

    @property
    def is_complete(self) -> bool:
        """Check if all expected subbands are present."""
        return len(self.files) >= self.expected_subbands
    
    @property
    def actual_subbands(self) -> int:
        """Number of subbands actually received."""
        return len(self.files)
    
    @property
    def present_subbands(self) -> Set[int]:
        """Set of subband indices that are present."""
        indices = set()
        for f in self.files:
            idx = extract_subband_index(f)
            if idx is not None:
                indices.add(idx)
        return indices
    
    @property
    def missing_subbands(self) -> List[int]:
        """List of subband indices that are missing."""
        present = self.present_subbands
        return sorted([i for i in range(self.expected_subbands) if i not in present])
    
    @property
    def file_paths_str(self) -> List[str]:
        """File paths as strings (for API compatibility)."""
        return [str(f) for f in self.files]
    
    @property
    def ordered_files(self) -> List[Path]:
        """Files ordered by subband index."""
        def sort_key(p: Path) -> int:
            idx = extract_subband_index(p)
            return idx if idx is not None else 999
        return sorted(self.files, key=sort_key)
    
    @property
    def timestamp(self) -> Optional[datetime]:
        """Parse group_id as datetime."""
        try:
            return datetime.strptime(self.group_id, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    
    @property
    def observation_date(self) -> Optional[str]:
        """Extract date portion of group_id (YYYY-MM-DD)."""
        ts = self.timestamp
        return ts.strftime("%Y-%m-%d") if ts else None
    
    def add_file(self, path: Path) -> bool:
        """Add a subband file to the group.
        
        Args:
            path: Path to HDF5 subband file
            
        Returns:
            True if file was added (not duplicate), False otherwise
        """
        path = Path(path)
        if path not in self.files:
            self.files.append(path)
            self.last_update = datetime.utcnow()
            return True
        return False
    
    def validate_files(self) -> tuple[List[Path], List[Path]]:
        """Validate that all files exist and are readable.
        
        Returns:
            Tuple of (valid_files, invalid_files)
        """
        valid = []
        invalid = []
        for f in self.files:
            if f.exists() and f.is_file():
                valid.append(f)
            else:
                invalid.append(f)
        return valid, invalid
    
    def set_error(self, error: str, message: Optional[str] = None) -> None:
        """Set error state with message."""
        self.state = ProcessingState.FAILED
        self.stage = ProcessingStage.ERROR
        self.error = error
        self.error_message = message or error
        self.last_update = datetime.utcnow()
    
    def set_completed(self, ms_path: Path) -> None:
        """Mark as successfully completed."""
        self.state = ProcessingState.COMPLETED
        self.stage = ProcessingStage.COMPLETE
        self.ms_path = Path(ms_path)
        self.last_update = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "group_id": self.group_id,
            "files": self.file_paths_str,
            "expected_subbands": self.expected_subbands,
            "actual_subbands": self.actual_subbands,
            "is_complete": self.is_complete,
            "missing_subbands": self.missing_subbands,
            "state": self.state.value,
            "stage": self.stage.value,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "chunk_minutes": self.chunk_minutes,
            "has_calibrator": self.has_calibrator,
            "calibrators": self.calibrators,
            "ms_path": str(self.ms_path) if self.ms_path else None,
            "error": self.error,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metrics": self.metrics,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubbandGroup":
        """Create from dictionary."""
        # Parse timestamps
        received_at = None
        if data.get("received_at"):
            try:
                received_at = datetime.fromisoformat(data["received_at"])
            except (ValueError, TypeError):
                pass
                
        last_update = None
        if data.get("last_update"):
            try:
                last_update = datetime.fromisoformat(data["last_update"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            group_id=data["group_id"],
            files=[Path(f) for f in data.get("files", [])],
            expected_subbands=data.get("expected_subbands", 16),
            state=ProcessingState.from_string(data.get("state", "collecting")),
            received_at=received_at,
            last_update=last_update,
            chunk_minutes=data.get("chunk_minutes", 5.0),
            has_calibrator=data.get("has_calibrator"),
            calibrators=data.get("calibrators"),
            ms_path=Path(data["ms_path"]) if data.get("ms_path") else None,
            error=data.get("error"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            metrics=data.get("metrics", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "SubbandGroup":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def __repr__(self) -> str:
        return (
            f"SubbandGroup(id={self.group_id!r}, "
            f"files={self.actual_subbands}/{self.expected_subbands}, "
            f"state={self.state.value})"
        )


@dataclass
class ConversionMetrics:
    """Performance metrics from conversion."""
    
    load_time_s: float = 0.0
    phase_time_s: float = 0.0
    write_time_s: float = 0.0
    total_time_s: float = 0.0
    writer_type: Optional[str] = None
    ms_size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class ConversionResult:
    """Result of converting a SubbandGroup to Measurement Set.
    
    This is returned by ConversionStage.execute() and contains
    all information about the conversion outcome.
    """
    
    success: bool
    group: SubbandGroup
    ms_path: Optional[Path] = None
    elapsed_seconds: float = 0.0
    error_message: Optional[str] = None
    metrics: ConversionMetrics = field(default_factory=ConversionMetrics)
    
    # Extracted metadata from MS
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    mid_mjd: Optional[float] = None
    is_calibrator: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "group_id": self.group.group_id,
            "ms_path": str(self.ms_path) if self.ms_path else None,
            "elapsed_seconds": self.elapsed_seconds,
            "error_message": self.error_message,
            "metrics": self.metrics.to_dict(),
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "mid_mjd": self.mid_mjd,
            "is_calibrator": self.is_calibrator,
        }


# Type alias for backwards compatibility
GroupInfo = SubbandGroup
