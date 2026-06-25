from __future__ import annotations

from infra.db.db_helper import my_db_helper


async def update_mysql(msg: str, record_id: int | None = None) -> None:
    my_db_helper.update_interview_record(record_id, {"processing_tips": msg})
