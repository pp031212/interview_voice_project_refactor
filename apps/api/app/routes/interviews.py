from __future__ import annotations

import json
from fastapi import APIRouter, Depends, File, Form, UploadFile

from pydantic import ValidationError as PydanticValidationError

from app.deps import interview_service_dep
from app.schemas.interviews import (
    AddInterviewPayload,
    AddRecordResponse,
    RecordResponse,
    RecordsResponse,
    RetryRecordResponse,
)
from core.errors import ValidationError
from services.interview_service import InterviewService

router = APIRouter()

@router.get("/interview_records")
async def get_interview_records(
    service: InterviewService = Depends(interview_service_dep),
) -> RecordsResponse:
    """Return all interview records.

    Returns:
        Response payload.
    """
    records = service.list_records()
    return RecordsResponse(data=records)


@router.get("/interview_records/{record_id}")
async def get_interview_record_by_id(
    record_id: int,
    service: InterviewService = Depends(interview_service_dep),
) -> RecordResponse:
    """Return interview record details by record id.

    Args:
        record_id: Interview record ID (path parameter).

    Returns:
        Response payload with record data.
    """
    record = service.get_record(record_id)
    return RecordResponse(data=record)


@router.post("/interview_records/{record_id}/retry")
async def retry_interview_record(
    record_id: int,
    service: InterviewService = Depends(interview_service_dep),
) -> RetryRecordResponse:
    """Reset a failed interview record to pending for resume processing.

    Args:
        record_id: Interview record ID (path parameter).
        service: Interview service dependency.

    Returns:
        Response payload with updated processing status.
    """
    record = service.retry_failed_record(record_id)
    return RetryRecordResponse(
        success=True,
        message="已提交继续处理，将从断点续跑",
        record_id=record_id,
        processing_status=int(record.get("processing_status", 0)),
        processing_tips=record.get("processing_tips"),
        processing_stage=record.get("processing_stage"),
        error_code=record.get("error_code"),
        error_type=record.get("error_type"),
        error_message=record.get("error_message"),
        retry_count=record.get("retry_count"),
        max_retries=record.get("max_retries"),
        failed_at=record.get("failed_at"),
        processing_started_at=record.get("processing_started_at"),
        stage_started_at=record.get("stage_started_at"),
        last_progress_at=record.get("last_progress_at"),
        completed_at=record.get("completed_at"),
    )


@router.post("/add_interview_record")
async def add_interview_record(
    json_data_str: str = Form(...),
    file: UploadFile = File(...),
    service: InterviewService = Depends(interview_service_dep),
) -> AddRecordResponse:
    """Add a new interview record and upload audio file.

    Args:
        json_data_str: JSON string containing form data.
        file: Uploaded audio file.

    Returns:
        Response payload.
    """
    try:
        payload = AddInterviewPayload.model_validate_json(json_data_str)
    except PydanticValidationError:
        payload_dict = json.loads(json_data_str)
        payload = AddInterviewPayload.model_validate(payload_dict)

    name = payload.name
    company = payload.company
    subject = payload.subject
    interview_date_str = payload.interview_date_str

    upload_info = service.save_upload(file=file, name=name, company=company)
    record_id = service.create_record(
        name=name,
        company=company,
        subject=subject,
        interview_date_str=interview_date_str,
        recording_url=upload_info.relative_path,
    )

    if record_id:
        return AddRecordResponse(
            success=True, message="面试记录已添加", record_id=record_id
        )

    raise ValidationError("添加面试记录失败")
