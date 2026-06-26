from __future__ import annotations

from datetime import datetime
from typing import Any

from core.task_status import InterviewProcessingStage, infer_processing_stage_from_tip
from infra.db.db_helper import my_db_helper


async def update_mysql(
    msg: str,
    record_id: int | None = None,
    processing_stage: str | InterviewProcessingStage | None = None,
) -> None:
    update_fields: dict[str, Any] = {
        "processing_tips": msg,
        "last_progress_at": datetime.now(),
    }
    stage = processing_stage or infer_processing_stage_from_tip(msg)
    if isinstance(stage, InterviewProcessingStage):
        update_fields["processing_stage"] = stage.value
    elif stage:
        update_fields["processing_stage"] = str(stage)
    my_db_helper.update_interview_record(record_id, update_fields)
