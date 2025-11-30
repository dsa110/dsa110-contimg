"""
Job service - business logic for pipeline job operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..repositories import JobRepository, JobRecord


class JobService:
    """Business logic for job operations."""
    
    LOG_PATHS = [
        "/data/dsa110-contimg/state/logs",
        "/data/dsa110-contimg/logs",
    ]
    
    def __init__(self, repository: "JobRepository"):
        self.repo = repository
    
    def get_job(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        return self.repo.get_by_run_id(run_id)
    
    def list_jobs(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["JobRecord"]:
        """List jobs with pagination."""
        return self.repo.list_all(limit=limit, offset=offset)
    
    def get_job_status(self, job: "JobRecord") -> str:
        """Determine job status from record."""
        if job.qa_grade:
            return "completed"
        return "pending"
    
    def build_provenance_links(self, job: "JobRecord") -> dict:
        """Build provenance URLs for a job."""
        return {
            "logs_url": f"/api/logs/{job.run_id}",
            "qa_url": f"/api/qa/job/{job.run_id}",
            "ms_url": (
                f"/api/ms/{quote(job.input_ms_path, safe='')}/metadata"
                if job.input_ms_path else None
            ),
            "image_url": (
                f"/api/images/{job.output_image_id}"
                if job.output_image_id else None
            ),
        }
    
    def find_log_file(self, run_id: str) -> Optional[Path]:
        """Find log file for a job, checking multiple paths."""
        for log_dir in self.LOG_PATHS:
            log_path = Path(log_dir) / f"{run_id}.log"
            if log_path.exists():
                return log_path
        return None
    
    def read_log_tail(self, run_id: str, tail: int = 100) -> dict:
        """Read the last N lines of a job's log file."""
        log_path = self.find_log_file(run_id)
        
        if not log_path:
            return {
                "run_id": run_id,
                "logs": [],
                "error": f"Log file not found for run_id: {run_id}",
            }
        
        try:
            with open(log_path) as f:
                lines = f.readlines()
                return {
                    "run_id": run_id,
                    "logs": lines[-tail:] if tail > 0 else lines,
                    "total_lines": len(lines),
                }
        except IOError as e:
            return {
                "run_id": run_id,
                "logs": [],
                "error": f"Failed to read log file: {str(e)}",
            }
