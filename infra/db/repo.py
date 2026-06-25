from __future__ import annotations

from datetime import datetime
from typing import Any

from infra.db.db_helper import my_db_helper


class InterviewRepository:
    """Repository wrapper around existing db_helper methods."""

    def list_records(self, *, exclude_markdown: bool = True) -> list[dict[str, Any]]:
        """Return all interview records.

        Args:
            exclude_markdown: When True, excludes markdown field.

        Returns:
            List of record dictionaries.
        """
        exclude_fields = ["markdown_text"] if exclude_markdown else []
        return my_db_helper.get_all_interview_records(exclude_fields=exclude_fields)

    def get_record_by_id(self, record_id: int | str) -> dict[str, Any] | None:
        """Fetch a single record by id.

        Args:
            record_id: Interview record id.

        Returns:
            Record dict or None.
        """
        records = my_db_helper.get_all_interview_records({"id": record_id})
        if not records:
            return None
        return records[0]

    def add_record(
        self,
        *,
        name: str,
        company_name: str,
        subject: str,
        interview_time: datetime,
        recording_url: str,
    ) -> int | None:
        """Insert a new interview record.

        Args:
            name: Candidate name.
            company_name: Company name.
            subject: Subject.
            interview_time: Interview datetime.
            recording_url: Relative file path.

        Returns:
            New record id or None.
        """
        return my_db_helper.add_interview_record(
            name=name,
            company_name=company_name,
            subject=subject,
            interview_time=interview_time,
            recording_url=recording_url,
        )
