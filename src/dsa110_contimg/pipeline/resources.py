"""
Resource management for pipeline execution.

Provides automatic cleanup of temporary files, directories, and other resources.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List

from dsa110_contimg.pipeline.config import PipelineConfig


class ResourceManager:
    """Manages pipeline resources (temp files, scratch dirs, etc.).
    
    Resources are automatically tracked and cleaned up when the manager
    is used as a context manager or when cleanup_all() is called.
    
    Example:
        with ResourceManager(config) as rm:
            with rm.temp_dir() as tmp:
                # Use tmp directory
                pass
            # tmp automatically cleaned up
        # All resources cleaned up
    """
    
    def __init__(self, config: PipelineConfig):
        """Initialize resource manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self._temp_dirs: List[Path] = []
        self._temp_files: List[Path] = []
    
    @contextmanager
    def temp_dir(self, prefix: str = "dsa110_") -> Iterator[Path]:
        """Create temporary directory, cleanup on exit.
        
        Args:
            prefix: Prefix for temporary directory name
            
        Yields:
            Path to temporary directory
        """
        tmp = Path(tempfile.mkdtemp(prefix=prefix))
        self._temp_dirs.append(tmp)
        try:
            yield tmp
        finally:
            if tmp.exists():
                try:
                    shutil.rmtree(tmp, ignore_errors=True)
                except Exception:
                    pass
                if tmp in self._temp_dirs:
                    self._temp_dirs.remove(tmp)
    
    @contextmanager
    def temp_file(self, suffix: str = "", prefix: str = "dsa110_") -> Iterator[Path]:
        """Create temporary file, cleanup on exit.
        
        CRITICAL: Ensures file descriptor is always closed, even if exception occurs.
        
        Args:
            suffix: File suffix (e.g., '.ms')
            prefix: File prefix
            
        Yields:
            Path to temporary file
        """
        import os
        fd = None
        tmp_path = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            tmp_path = Path(tmp)
            self._temp_files.append(tmp_path)
            yield tmp_path
        finally:
            # CRITICAL: Always close file descriptor first, then remove file
            # This ensures we don't leak file descriptors even if unlink fails
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass  # Best effort - fd may already be closed
            
            # Remove file if it exists
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass  # Best effort - file may already be deleted
            
            # Remove from tracking list
            if tmp_path is not None and tmp_path in self._temp_files:
                self._temp_files.remove(tmp_path)
    
    @contextmanager
    def scratch_dir(self) -> Iterator[Path]:
        """Get or create scratch directory.
        
        Yields:
            Path to scratch directory
        """
        scratch = self.config.paths.scratch_dir or Path("/tmp")
        scratch.mkdir(parents=True, exist_ok=True)
        yield scratch
    
    def cleanup_all(self) -> None:
        """Cleanup all managed resources."""
        for tmp in self._temp_dirs:
            if tmp.exists():
                try:
                    shutil.rmtree(tmp, ignore_errors=True)
                except Exception:
                    pass
        self._temp_dirs.clear()
        
        for tmp_file in self._temp_files:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass
        self._temp_files.clear()
    
    def __enter__(self) -> ResourceManager:
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, cleanup all resources."""
        self.cleanup_all()

