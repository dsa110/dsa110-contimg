"""
QA service - business logic for quality assessment.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..repositories import ImageRecord, MSRecord, JobRecord


class QAService:
    """Business logic for quality assessment operations."""
    
    def build_image_qa(self, image: "ImageRecord") -> dict:
        """Build QA report for an image."""
        metrics = dict(image.qa_metrics) if image.qa_metrics else {}
        metrics.setdefault("rms_noise", image.noise_jy)
        metrics.setdefault("dynamic_range", image.dynamic_range)
        metrics.setdefault("beam_major_arcsec", image.beam_major_arcsec)
        metrics.setdefault("beam_minor_arcsec", image.beam_minor_arcsec)
        metrics.setdefault("beam_pa_deg", image.beam_pa_deg)

        return {
            "image_id": str(image.id),
            "qa_grade": image.qa_grade,
            "qa_summary": image.qa_summary,
            "quality_metrics": metrics,
            "flags": image.qa_flags or [],
            "timestamp": image.qa_timestamp,
        }
    
    def build_ms_qa(self, ms: "MSRecord") -> dict:
        """Build QA report for a measurement set."""
        metrics = dict(ms.qa_metrics) if ms.qa_metrics else {}
        metrics.setdefault("stage", ms.stage)
        metrics.setdefault("status", ms.status)

        return {
            "ms_path": ms.path,
            "qa_grade": ms.qa_grade,
            "qa_summary": ms.qa_summary,
            "stage": ms.stage,
            "status": ms.status,
            "cal_applied": bool(ms.cal_applied),
            "quality_metrics": metrics,
            "flags": ms.qa_flags or [],
            "timestamp": ms.qa_timestamp,
        }
    
    def build_job_qa(self, job: "JobRecord") -> dict:
        """Build QA report for a pipeline job."""
        return {
            "run_id": job.run_id,
            "qa_grade": job.qa_grade,
            "qa_summary": job.qa_summary,
            "ms_path": job.input_ms_path,
            "cal_table": job.cal_table_path,
            "flags": job.qa_flags or [],
            "queue_status": job.queue_status,
            "pipeline_config": job.config,
        }
