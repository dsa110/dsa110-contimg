"""
Unit tests for the job queue module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import directly from the module to avoid app initialization issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from dsa110_contimg.api.job_queue import (
    JobQueue,
    JobStatus,
    JobInfo,
    enqueue_job,
    get_job_status,
    get_job_info,
    rerun_pipeline_job,
)


class TestJobStatus:
    """Tests for JobStatus enum."""
    
    def test_status_values(self):
        """Verify all expected status values exist."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.STARTED.value == "started"
        assert JobStatus.FINISHED.value == "finished"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.NOT_FOUND.value == "not_found"


class TestJobInfo:
    """Tests for JobInfo dataclass."""
    
    def test_job_info_creation(self):
        """Test creating a JobInfo instance."""
        now = datetime.utcnow()
        info = JobInfo(
            job_id="test123",
            status=JobStatus.QUEUED,
            created_at=now,
            meta={"key": "value"},
        )
        
        assert info.job_id == "test123"
        assert info.status == JobStatus.QUEUED
        assert info.created_at == now
        assert info.meta == {"key": "value"}
    
    def test_job_info_to_dict(self):
        """Test serializing JobInfo to dict."""
        now = datetime.utcnow()
        info = JobInfo(
            job_id="test123",
            status=JobStatus.FINISHED,
            created_at=now,
            result={"output": "success"},
        )
        
        d = info.to_dict()
        assert d["job_id"] == "test123"
        assert d["status"] == "finished"
        assert d["result"] == {"output": "success"}
        assert d["created_at"] == now.isoformat()


class TestJobQueueInMemory:
    """Tests for JobQueue in-memory fallback mode."""
    
    @pytest.fixture
    def queue(self):
        """Create a queue that uses in-memory fallback."""
        # Force in-memory mode by using invalid Redis URL
        with patch.dict(os.environ, {"REDIS_URL": "redis://invalid:9999/0"}):
            q = JobQueue(redis_url="redis://invalid:9999/0")
            # Ensure it's not connected
            q._redis = None
            q._queue = None
            return q
    
    def test_queue_not_connected(self, queue):
        """Verify queue is in fallback mode."""
        assert not queue.is_connected
    
    def test_enqueue_in_memory(self, queue):
        """Test enqueueing a job in memory."""
        def dummy_func():
            pass
        
        job_id = queue.enqueue(dummy_func, meta={"test": True})
        
        assert job_id is not None
        assert job_id.startswith("job_")
    
    def test_enqueue_with_custom_id(self, queue):
        """Test enqueueing with custom job ID."""
        def dummy_func():
            pass
        
        job_id = queue.enqueue(dummy_func, job_id="custom_123")
        assert job_id == "custom_123"
    
    def test_get_job_in_memory(self, queue):
        """Test retrieving job from in-memory queue."""
        def dummy_func():
            pass
        
        job_id = queue.enqueue(dummy_func, meta={"key": "value"})
        job_info = queue.get_job(job_id)
        
        assert job_info is not None
        assert job_info.job_id == job_id
        assert job_info.status == JobStatus.QUEUED
        assert job_info.meta == {"key": "value"}
    
    def test_get_status_in_memory(self, queue):
        """Test getting job status."""
        def dummy_func():
            pass
        
        job_id = queue.enqueue(dummy_func)
        status = queue.get_status(job_id)
        
        assert status == JobStatus.QUEUED
    
    def test_get_status_not_found(self, queue):
        """Test getting status for non-existent job."""
        status = queue.get_status("nonexistent")
        assert status == JobStatus.NOT_FOUND
    
    def test_cancel_in_memory(self, queue):
        """Test canceling a job."""
        def dummy_func():
            pass
        
        job_id = queue.enqueue(dummy_func)
        success = queue.cancel(job_id)
        
        assert success
        assert queue.get_status(job_id) == JobStatus.CANCELED
    
    def test_cancel_nonexistent(self, queue):
        """Test canceling non-existent job."""
        success = queue.cancel("nonexistent")
        assert not success
    
    def test_list_jobs_in_memory(self, queue):
        """Test listing jobs."""
        def dummy_func():
            pass
        
        queue.enqueue(dummy_func, job_id="job1")
        queue.enqueue(dummy_func, job_id="job2")
        
        jobs = queue.list_jobs()
        assert len(jobs) == 2
        assert any(j.job_id == "job1" for j in jobs)
        assert any(j.job_id == "job2" for j in jobs)
    
    def test_list_jobs_with_filter(self, queue):
        """Test listing jobs with status filter."""
        def dummy_func():
            pass
        
        queue.enqueue(dummy_func, job_id="job1")
        queue.enqueue(dummy_func, job_id="job2")
        queue.cancel("job2")
        
        queued = queue.list_jobs(status=JobStatus.QUEUED)
        canceled = queue.list_jobs(status=JobStatus.CANCELED)
        
        assert len(queued) == 1
        assert len(canceled) == 1
    
    def test_queue_stats_in_memory(self, queue):
        """Test getting queue stats."""
        def dummy_func():
            pass
        
        queue.enqueue(dummy_func)
        queue.enqueue(dummy_func)
        
        stats = queue.get_queue_stats()
        assert stats["connected"] is False
        assert stats["in_memory_count"] == 2


class TestJobQueueRedis:
    """Tests for JobQueue with Redis (mocked)."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis connection."""
        with patch("src.dsa110_contimg.api.job_queue.Redis") as mock:
            mock_instance = MagicMock()
            mock.from_url.return_value = mock_instance
            mock_instance.ping.return_value = True
            yield mock_instance
    
    @pytest.fixture
    def mock_rq_queue(self):
        """Create mock RQ Queue."""
        with patch("src.dsa110_contimg.api.job_queue.Queue") as mock:
            yield mock


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_enqueue_job_function(self):
        """Test enqueue_job convenience function."""
        with patch("dsa110_contimg.api.job_queue.job_queue") as mock_queue:
            mock_queue.enqueue.return_value = "job_123"
            
            def dummy():
                pass
            
            result = enqueue_job(dummy, job_id="test")
            mock_queue.enqueue.assert_called_once()
            assert result == "job_123"
    
    def test_get_job_status_function(self):
        """Test get_job_status convenience function."""
        with patch("dsa110_contimg.api.job_queue.job_queue") as mock_queue:
            mock_queue.get_status.return_value = JobStatus.FINISHED
            
            result = get_job_status("job_123")
            assert result == JobStatus.FINISHED
    
    def test_get_job_info_function(self):
        """Test get_job_info convenience function."""
        with patch("dsa110_contimg.api.job_queue.job_queue") as mock_queue:
            mock_info = JobInfo(job_id="test", status=JobStatus.QUEUED)
            mock_queue.get_job.return_value = mock_info
            
            result = get_job_info("test")
            assert result == mock_info


class TestRerunPipelineJob:
    """Tests for the rerun_pipeline_job worker function."""
    
    def test_rerun_generates_new_run_id(self):
        """Test that rerun creates a new run ID."""
        result = rerun_pipeline_job("original_run_20231201_120000")
        
        assert result["original_run_id"] == "original_run_20231201_120000"
        assert result["new_run_id"].startswith("original_run_")
        assert result["new_run_id"] != result["original_run_id"]
        assert result["status"] == "completed"
    
    def test_rerun_with_underscores_in_name(self):
        """Test rerun with complex run ID."""
        result = rerun_pipeline_job("my_pipeline_run_20231201_120000")
        
        assert result["new_run_id"].startswith("my_pipeline_run_")
