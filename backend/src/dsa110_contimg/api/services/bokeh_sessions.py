"""
Bokeh session manager for interactive visualization tools.

Manages lifecycle of Bokeh server processes for InteractiveClean sessions.
These sessions enable interactive CLEAN imaging with mask drawing and
real-time deconvolution feedback.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class BokehSession:
    """Represents a running Bokeh server session for InteractiveClean."""

    id: str
    port: int
    process: subprocess.Popen
    ms_path: str
    imagename: str
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    params: Dict = field(default_factory=dict)

    @property
    def url(self) -> str:
        """Get the URL for accessing this Bokeh session."""
        # Use the host from environment or default to localhost
        host = os.getenv("BOKEH_HOST", "localhost")
        return f"http://{host}:{self.port}/iclean"

    @property
    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def age_hours(self) -> float:
        """Get session age in hours."""
        return self.age_seconds / 3600.0

    def is_alive(self) -> bool:
        """Check if the Bokeh server process is still running."""
        return self.process.poll() is None

    def to_dict(self) -> dict:
        """Convert session to dictionary for API responses."""
        return {
            "id": self.id,
            "port": self.port,
            "url": self.url,
            "ms_path": self.ms_path,
            "imagename": self.imagename,
            "created_at": self.created_at.isoformat(),
            "age_hours": round(self.age_hours, 2),
            "is_alive": self.is_alive(),
            "user_id": self.user_id,
            "params": self.params,
        }


class PortPool:
    """Manages a pool of available ports for Bokeh servers."""

    def __init__(self, port_range: range):
        """Initialize port pool.

        Args:
            port_range: Range of ports to use (e.g., range(5010, 5100))
        """
        self.available = set(port_range)
        self.in_use: Dict[str, int] = {}  # session_id -> port
        self._lock = asyncio.Lock()

    async def acquire(self, session_id: str) -> int:
        """Acquire a port for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            Port number

        Raises:
            RuntimeError: If no ports available
        """
        async with self._lock:
            if not self.available:
                raise RuntimeError(
                    f"No ports available. {len(self.in_use)} sessions active. "
                    "Consider cleaning up stale sessions."
                )
            port = self.available.pop()
            self.in_use[session_id] = port
            return port

    async def release(self, session_id: str) -> None:
        """Release a port back to the pool.

        Args:
            session_id: Session identifier that held the port
        """
        async with self._lock:
            if session_id in self.in_use:
                port = self.in_use.pop(session_id)
                self.available.add(port)

    @property
    def available_count(self) -> int:
        """Number of available ports."""
        return len(self.available)

    @property
    def in_use_count(self) -> int:
        """Number of ports in use."""
        return len(self.in_use)


# Default imaging parameters for DSA-110
DSA110_ICLEAN_DEFAULTS = {
    "imsize": [5040, 5040],
    "cell": "2.5arcsec",
    "specmode": "mfs",
    "deconvolver": "mtmfs",
    "weighting": "briggs",
    "robust": 0.5,
    "niter": 10000,
    "threshold": "0.5mJy",
    "nterms": 2,
    "datacolumn": "corrected",
}


class BokehSessionManager:
    """
    Manages Bokeh server sessions for interactive tools.

    This manager handles:
    - Launching Bokeh server processes for InteractiveClean
    - Port allocation and tracking
    - Session lifecycle management
    - Automatic cleanup of stale sessions

    Usage:
        manager = BokehSessionManager()
        session = await manager.create_session(ms_path, imagename)
        # ... user interacts with session ...
        await manager.cleanup_session(session.id)
    """

    def __init__(
        self,
        port_range: range = range(5010, 5100),
        default_params: Optional[Dict] = None,
    ):
        """Initialize session manager.

        Args:
            port_range: Range of ports to use for Bokeh servers
            default_params: Default imaging parameters (uses DSA-110 defaults if None)
        """
        self.sessions: Dict[str, BokehSession] = {}
        self.port_pool = PortPool(port_range)
        self.default_params = default_params or DSA110_ICLEAN_DEFAULTS.copy()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        ms_path: str,
        imagename: str,
        params: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> BokehSession:
        """
        Create and launch a new InteractiveClean Bokeh session.

        Args:
            ms_path: Path to the Measurement Set
            imagename: Output image name prefix
            params: Imaging parameters (merged with defaults)
            user_id: Optional user identifier for session tracking

        Returns:
            BokehSession with connection details

        Raises:
            FileNotFoundError: If MS does not exist
            RuntimeError: If Bokeh server fails to start
        """
        # Validate MS exists
        if not Path(ms_path).exists():
            raise FileNotFoundError(f"Measurement Set not found: {ms_path}")

        # Generate session ID and acquire port
        session_id = str(uuid.uuid4())
        port = await self.port_pool.acquire(session_id)

        # Merge params with defaults
        merged_params = self.default_params.copy()
        if params:
            merged_params.update(params)

        # Build the Python script that will run InteractiveClean
        # Note: casagui may not be installed - handle gracefully
        script = self._build_iclean_script(
            ms_path=ms_path,
            imagename=imagename,
            params=merged_params,
            port=port,
        )

        # Get conda environment's Python
        python_exe = sys.executable

        logger.info(f"Starting iClean session {session_id} on port {port}")
        logger.debug(f"MS: {ms_path}, imagename: {imagename}")

        try:
            # Set up environment for Bokeh
            env = os.environ.copy()
            env["BOKEH_ALLOW_WS_ORIGIN"] = "*"

            # Launch subprocess
            proc = subprocess.Popen(
                [python_exe, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(Path(ms_path).parent),  # Working dir is MS directory
            )

            # Create session object
            session = BokehSession(
                id=session_id,
                port=port,
                process=proc,
                ms_path=ms_path,
                imagename=imagename,
                user_id=user_id,
                params=merged_params,
            )

            # Wait briefly for server to start
            await asyncio.sleep(2.0)

            # Check if process is still running
            if proc.poll() is not None:
                await self.port_pool.release(session_id)
                stderr = proc.stderr.read().decode() if proc.stderr else "Unknown error"
                logger.error(f"Bokeh server failed to start: {stderr}")
                raise RuntimeError(f"Bokeh server failed to start: {stderr}")

            # Store session
            async with self._lock:
                self.sessions[session_id] = session

            logger.info(f"Session {session_id} started successfully at {session.url}")
            return session

        except Exception as e:
            # Clean up on failure
            await self.port_pool.release(session_id)
            raise

    def _build_iclean_script(
        self,
        ms_path: str,
        imagename: str,
        params: Dict,
        port: int,
    ) -> str:
        """Build Python script to launch InteractiveClean.

        Args:
            ms_path: Path to Measurement Set
            imagename: Output image name prefix
            params: Imaging parameters
            port: Port for Bokeh server

        Returns:
            Python script as string
        """
        # Format imsize as list
        imsize = params.get("imsize", [5040, 5040])
        if isinstance(imsize, int):
            imsize = [imsize, imsize]

        script = f'''
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iclean_session")

try:
    from casagui.apps import InteractiveClean
except ImportError as e:
    logger.error("casagui not installed. Install with: pip install git+https://github.com/casangi/casagui.git")
    sys.exit(1)

logger.info("Launching InteractiveClean session")
logger.info(f"MS: {ms_path}")
logger.info(f"Output: {imagename}")

try:
    ic = InteractiveClean(
        vis="{ms_path}",
        imagename="{imagename}",
        imsize={imsize},
        cell="{params.get('cell', '2.5arcsec')}",
        specmode="{params.get('specmode', 'mfs')}",
        deconvolver="{params.get('deconvolver', 'mtmfs')}",
        weighting="{params.get('weighting', 'briggs')}",
        robust={params.get('robust', 0.5)},
        niter={params.get('niter', 10000)},
        threshold="{params.get('threshold', '0.5mJy')}",
    )
    
    logger.info(f"Starting Bokeh server on port {port}")
    ic.serve(port={port})
    
except Exception as e:
    logger.exception(f"InteractiveClean failed: {{e}}")
    sys.exit(1)
'''
        return script

    async def get_session(self, session_id: str) -> Optional[BokehSession]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            BokehSession if found, None otherwise
        """
        return self.sessions.get(session_id)

    async def cleanup_session(self, session_id: str) -> bool:
        """Terminate session and free resources.

        Args:
            session_id: Session identifier

        Returns:
            True if session was cleaned up, False if not found
        """
        async with self._lock:
            session = self.sessions.pop(session_id, None)

        if session is None:
            return False

        logger.info(f"Cleaning up session {session_id}")

        # Terminate process
        if session.process.poll() is None:
            session.process.terminate()
            try:
                session.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"Session {session_id} did not terminate, killing")
                session.process.kill()
                session.process.wait()

        # Release port
        await self.port_pool.release(session_id)

        logger.info(f"Session {session_id} cleaned up")
        return True

    async def cleanup_stale_sessions(self, max_age_hours: float = 4.0) -> int:
        """Clean up sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        # Find stale sessions
        stale_ids = [
            sid
            for sid, session in self.sessions.items()
            if session.created_at < cutoff or not session.is_alive()
        ]

        # Clean them up
        for sid in stale_ids:
            await self.cleanup_session(sid)

        if stale_ids:
            logger.info(f"Cleaned up {len(stale_ids)} stale sessions")

        return len(stale_ids)

    async def cleanup_dead_sessions(self) -> int:
        """Clean up sessions whose processes have died.

        Returns:
            Number of sessions cleaned up
        """
        dead_ids = [
            sid for sid, session in self.sessions.items() if not session.is_alive()
        ]

        for sid in dead_ids:
            await self.cleanup_session(sid)

        if dead_ids:
            logger.info(f"Cleaned up {len(dead_ids)} dead sessions")

        return len(dead_ids)

    def list_sessions(self) -> list[dict]:
        """List all active sessions.

        Returns:
            List of session dictionaries
        """
        return [session.to_dict() for session in self.sessions.values()]

    async def shutdown(self) -> None:
        """Shutdown manager and cleanup all sessions."""
        logger.info("Shutting down BokehSessionManager")

        # Stop cleanup task if running
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cleanup all sessions
        session_ids = list(self.sessions.keys())
        for sid in session_ids:
            await self.cleanup_session(sid)

        logger.info("BokehSessionManager shutdown complete")

    async def start_cleanup_loop(self, interval_seconds: int = 3600) -> None:
        """Start background task for periodic cleanup.

        Args:
            interval_seconds: Interval between cleanup runs (default: 1 hour)
        """

        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.cleanup_stale_sessions()
                    await self.cleanup_dead_sessions()
                except Exception as e:
                    logger.exception(f"Error in cleanup loop: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(
            f"Started session cleanup loop (interval: {interval_seconds}s)"
        )


# Singleton instance
_manager: Optional[BokehSessionManager] = None


def get_session_manager() -> BokehSessionManager:
    """Get the singleton BokehSessionManager instance.

    Returns:
        BokehSessionManager singleton
    """
    global _manager
    if _manager is None:
        _manager = BokehSessionManager()
    return _manager


async def init_session_manager() -> BokehSessionManager:
    """Initialize session manager and start cleanup loop.

    Call this at application startup.

    Returns:
        Initialized BokehSessionManager
    """
    manager = get_session_manager()
    await manager.start_cleanup_loop()
    return manager


async def shutdown_session_manager() -> None:
    """Shutdown session manager.

    Call this at application shutdown.
    """
    global _manager
    if _manager is not None:
        await _manager.shutdown()
        _manager = None
