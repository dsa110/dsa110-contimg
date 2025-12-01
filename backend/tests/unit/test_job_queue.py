"""
Unit tests for the job queue module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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
        """Test that rerun creates a new run ID with proper job lookup."""
        from dsa110_contimg.api.repositories import JobRecord
        from datetime import datetime
        
        mock_job = JobRecord(
            run_id="original_run_20231201_120000",
            input_ms_path="/data/test.ms",
            cal_table_path="/data/test.cal",
            phase_center_ra=180.0,
            phase_center_dec=45.0,
        )
        
        with patch("dsa110_contimg.api.job_queue.JobRepository") as MockRepo:
            mock_instance = MagicMock()
            mock_instance.get_by_run_id = AsyncMock(return_value=mock_job)
            MockRepo.return_value = mock_instance
            
            with patch("dsa110_contimg.api.job_queue.get_db_connection") as mock_conn:
                mock_conn.return_value = MagicMock()
                
                with patch("dsa110_contimg.api.job_queue.db_create_job", return_value=1):
                    with patch("dsa110_contimg.api.job_queue.db_update_job_status"):
                        # Mock the stages_impl import that happens inside the function
                        with patch.dict('sys.modules', {'dsa110_contimg.pipeline.stages_impl': MagicMock()}):
                            result = rerun_pipeline_job("original_run_20231201_120000")
        
        assert result["original_run_id"] == "original_run_20231201_120000"
        # new_run_id format is: base_id_rerun_timestamp where base_id is everything before the last underscore
        assert "_rerun_" in result["new_run_id"]
        assert result["new_run_id"].startswith("original_run_20231201_rerun_")
        assert result["status"] == "completed"
        assert result["config"]["ms_path"] == "/data/test.ms"
    
    def test_rerun_with_config_overrides(self):
        """Test rerun applies config overrides."""
        from dsa110_contimg.api.repositories import JobRecord
        
        mock_job = JobRecord(
            run_id="test_run",
            input_ms_path="/data/original.ms",
            phase_center_ra=180.0,
            phase_center_dec=45.0,
        )
        
        with patch("dsa110_contimg.api.job_queue.JobRepository") as MockRepo:
            mock_instance = MagicMock()
            mock_instance.get_by_run_id = AsyncMock(return_value=mock_job)
            MockRepo.return_value = mock_instance
            
            with patch("dsa110_contimg.api.job_queue.get_db_connection") as mock_conn:
                mock_conn.return_value = MagicMock()
                
                with patch("dsa110_contimg.api.job_queue.db_create_job", return_value=1):
                    with patch("dsa110_contimg.api.job_queue.db_update_job_status"):
                        result = rerun_pipeline_job("test_run", config={"ms_path": "/data/new.ms"})
        
        # Config override should be applied
        assert result["config"]["ms_path"] == "/data/new.ms"
        # Original values preserved where not overridden
        assert result["config"]["phase_center_ra"] == 180.0
    
    def test_rerun_job_not_found(self):
        """Test rerun raises ValueError when original job not found."""
        with patch("dsa110_contimg.api.job_queue.JobRepository") as MockRepo:
            mock_instance = MagicMock()
            mock_instance.get_by_run_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_instance
            
            with pytest.raises(ValueError) as exc_info:
                rerun_pipeline_job("nonexistent_run")
            
            assert "not found" in str(exc_info.value)
    
    def test_rerun_with_pipeline_command(self):
        """Test rerun uses PIPELINE_CMD_TEMPLATE when configured."""
        from dsa110_contimg.api.repositories import JobRecord
        import subprocess
        
        mock_job = JobRecord(
            run_id="test_run",
            input_ms_path="/data/test.ms",
        )
        
        with patch("dsa110_contimg.api.job_queue.JobRepository") as MockRepo:
            mock_instance = MagicMock()
            mock_instance.get_by_run_id = AsyncMock(return_value=mock_job)
            MockRepo.return_value = mock_instance
            
            with patch("dsa110_contimg.api.job_queue.get_db_connection") as mock_conn:
                mock_conn.return_value = MagicMock()
                
                with patch("dsa110_contimg.api.job_queue.db_create_job", return_value=1):
                    with patch("dsa110_contimg.api.job_queue.db_update_job_status"):
                        with patch("dsa110_contimg.api.job_queue.PIPELINE_CMD_TEMPLATE", "echo {ms_path}"):
                            with patch("subprocess.run") as mock_run:
                                mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
                                
                                result = rerun_pipeline_job("test_run")
        
        assert result["status"] == "completed"
        mock_run.assert_called_once()
    
    def test_rerun_handles_pipeline_failure(self):
        """Test rerun handles pipeline command failure."""
        from dsa110_contimg.api.repositories import JobRecord
        import subprocess
        
        mock_job = JobRecord(
            run_id="test_run",
            input_ms_path="/data/test.ms",
        )
        
        with patch("dsa110_contimg.api.job_queue.JobRepository") as MockRepo:
            mock_instance = MagicMock()
            mock_instance.get_by_run_id = AsyncMock(return_value=mock_job)
            MockRepo.return_value = mock_instance
            
            with patch("dsa110_contimg.api.job_queue.get_db_connection") as mock_conn:
                mock_conn.return_value = MagicMock()
                
                with patch("dsa110_contimg.api.job_queue.db_create_job", return_value=1):
                    with patch("dsa110_contimg.api.job_queue.db_update_job_status"):
                        with patch("dsa110_contimg.api.job_queue.PIPELINE_CMD_TEMPLATE", "false"):
                            with patch("subprocess.run") as mock_run:
                                mock_run.side_effect = subprocess.CalledProcessError(1, "false", "", "error")
                                
                                result = rerun_pipeline_job("test_run")
        
        assert result["status"] == "failed"
        assert "failed" in result["error"]
