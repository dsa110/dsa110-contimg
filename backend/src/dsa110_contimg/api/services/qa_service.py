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
        return {
            "image_id": str(image.id),
            "qa_grade": image.qa_grade,
            "qa_summary": image.qa_summary,
            "metrics": {
                "rms_noise": image.noise_jy,
                "dynamic_range": image.dynamic_range,
                "beam_major_arcsec": image.beam_major_arcsec,
                "beam_minor_arcsec": image.beam_minor_arcsec,
                "beam_pa_deg": image.beam_pa_deg,
            },
        }
    
    def build_ms_qa(self, ms: "MSRecord") -> dict:
        """Build QA report for a measurement set."""
        return {
            "ms_path": ms.path,
            "qa_grade": ms.qa_grade,
            "qa_summary": ms.qa_summary,
            "stage": ms.stage,
            "status": ms.status,
            "cal_applied": bool(ms.cal_applied),
        }
    
    def build_job_qa(self, job: "JobRecord") -> dict:
        """Build QA report for a pipeline job."""
        return {
            "run_id": job.run_id,
            "qa_grade": job.qa_grade,
            "qa_summary": job.qa_summary,
            "ms_path": job.input_ms_path,
            "cal_table": job.cal_table_path,
        }
