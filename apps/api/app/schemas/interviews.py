from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AddInterviewPayload(BaseModel):
    """Payload for adding an interview record."""

    name: str = Field(..., min_length=1, max_length=100)
    company: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=255)
    interview_date_str: str = Field(..., min_length=4, max_length=20)


class RecordsResponse(BaseModel):
    """Response wrapper for list responses."""

    data: list[dict[str, Any]]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecordResponse(BaseModel):
    """Response wrapper for single record payload."""

    data: dict[str, Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AddRecordResponse(BaseModel):
    """Response wrapper for create results."""

    success: bool
    message: str | None = None
    record_id: int | None = None
    error: str | None = None


class RetryRecordResponse(BaseModel):
    """Response wrapper for retry/resume requests."""

    success: bool
    message: str
    record_id: int
    processing_status: int
    processing_tips: str | None = None
    processing_stage: str | None = None
    error_code: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    retry_count: int | None = None
    max_retries: int | None = None
    failed_at: Any | None = None
    processing_started_at: Any | None = None
    stage_started_at: Any | None = None
    last_progress_at: Any | None = None
    completed_at: Any | None = None
