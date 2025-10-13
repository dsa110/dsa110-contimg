"""Pydantic models used by the monitoring API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QueueGroup(BaseModel):
    group_id: str = Field(..., description="Normalized observation timestamp")
    state: str = Field(..., description="Queue state (collecting|pending|in_progress|completed|failed)")
    received_at: datetime
    last_update: datetime
    subbands_present: int = Field(..., description="Number of subbands ingested for this group")
    expected_subbands: int = Field(..., description="Expected subbands per group")
    has_calibrator: bool | None = Field(None, description="True if any calibrator was matched in beam")
    matches: list[CalibratorMatch] | None = Field(None, description="Top matched calibrators for this group")


class QueueStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    failed: int
    completed: int
    collecting: int


class CalibrationSet(BaseModel):
    set_name: str
    tables: List[str]
    active: int = Field(..., description="Number of active tables")
    total: int = Field(..., description="Total tables registered for the set")


class PipelineStatus(BaseModel):
    queue: QueueStats
    recent_groups: List[QueueGroup]
    calibration_sets: List[CalibrationSet]
    matched_recent: int = Field(0, description="Number of recent groups with calibrator matches")


class ProductEntry(BaseModel):
    id: int
    path: str
    ms_path: str
    created_at: datetime
    type: str
    beam_major_arcsec: Optional[float] = None
    noise_jy: Optional[float] = None
    pbcor: bool = Field(False, description="Primary-beam corrected")


class ProductList(BaseModel):
    items: List[ProductEntry]


class CalibratorMatch(BaseModel):
    name: str
    ra_deg: float
    dec_deg: float
    sep_deg: float
    weighted_flux: float | None = None


class CalibratorMatchGroup(BaseModel):
    group_id: str
    matched: bool = Field(..., description="True if any calibrator matched")
    matches: List[CalibratorMatch]
    received_at: datetime
    last_update: datetime


class CalibratorMatchList(BaseModel):
    items: List[CalibratorMatchGroup]


class QAArtifact(BaseModel):
    group_id: str
    name: str
    path: str
    created_at: datetime | None = None


class QAList(BaseModel):
    items: List[QAArtifact]


class GroupDetail(BaseModel):
    group_id: str
    state: str
    received_at: datetime
    last_update: datetime
    subbands_present: int
    expected_subbands: int
    has_calibrator: bool | None = None
    matches: list[CalibratorMatch] | None = None
    qa: list[QAArtifact] = []
    perf_total_time: float | None = None
    writer_type: str | None = None


class SystemMetrics(BaseModel):
    ts: datetime
    cpu_percent: float | None = None
    mem_percent: float | None = None
    mem_total: int | None = None
    mem_used: int | None = None
    disk_total: int | None = None
    disk_used: int | None = None
    load_1: float | None = None
    load_5: float | None = None
    load_15: float | None = None


class MsIndexEntry(BaseModel):
    path: str
    start_mjd: float | None = None
    end_mjd: float | None = None
    mid_mjd: float | None = None
    processed_at: datetime | None = None
    status: str | None = None
    stage: str | None = None
    stage_updated_at: datetime | None = None
    cal_applied: int | None = None
    imagename: str | None = None


class MsIndexList(BaseModel):
    items: List[MsIndexEntry]
