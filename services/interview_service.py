from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from fastapi import UploadFile

from core.errors import FileUploadError, ValidationError, RecordNotFoundError
from core.utils.path_utils import get_file_extension
from core.utils.time_utils import get_current_time, get_datetime_from_str

from infra.db.repo import InterviewRepository


@dataclass(frozen=True)
class UploadInfo:
    """Information about a saved upload."""

    relative_path: str
    absolute_path: Path
    original_filename: str
    saved_filename: str


class InterviewService:
    """Application service for interview records."""

    def __init__(self, *, repo: InterviewRepository, upload_dir: Path) -> None:
        self._repo = repo
        self._upload_dir = upload_dir
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def list_records(self) -> list[dict[str, Any]]:
        """Return all interview records without markdown text.

        Returns:
            List of record dictionaries.
        """
        return self._repo.list_records(exclude_markdown=True)

    def get_record(self, record_id: int | str) -> dict[str, Any] | None:
        """Return a single interview record by id.

        Args:
            record_id: Interview record id.

        Returns:
            Record dict or None.

        Raises:
            RecordNotFoundError: If record does not exist.
        """
        record = self._repo.get_record_by_id(record_id)
        if record is None:
            raise RecordNotFoundError(int(record_id))
        return record

    def save_upload(self, *, file: UploadFile, name: str, company: str) -> UploadInfo:
        """Persist uploaded file to the upload directory.

        Args:
            file: UploadFile instance.
            name: Candidate name.
            company: Company name.

        Returns:
            UploadInfo: Saved file metadata.

        Raises:
            ValidationError: If file or parameters are invalid.
            FileUploadError: If file save fails.
        """
        if not file.filename:
            raise ValidationError("文件名不能为空")

        if not name or not company:
            raise ValidationError("姓名和公司名不能为空")

        try:
            original_filename = file.filename
            extension = get_file_extension(original_filename)
            saved_filename = f"{get_current_time()}_{name}_{company}{extension}"
            relative_path = str(Path("data") / "uploads" / saved_filename)
            absolute_path = self._upload_dir / saved_filename

            with absolute_path.open("wb") as output_file:
                shutil.copyfileobj(file.file, output_file)

            return UploadInfo(
                relative_path=relative_path,
                absolute_path=absolute_path,
                original_filename=original_filename,
                saved_filename=saved_filename,
            )
        except Exception as exc:
            raise FileUploadError(f"文件上传失败: {str(exc)}")

    def create_record(
        self,
        *,
        name: str,
        company: str,
        subject: str,
        interview_date_str: str,
        recording_url: str,
    ) -> int | None:
        """Create a new interview record.

        Args:
            name: Candidate name.
            company: Company name.
            subject: Subject.
            interview_date_str: Interview date string.
            recording_url: Relative file path.

        Returns:
            Record id or None.

        Raises:
            ValidationError: If required fields are missing.
        """
        if not name or not company:
            raise ValidationError("姓名和公司名不能为空")

        if not recording_url:
            raise ValidationError("录音文件路径不能为空")

        interview_time = get_datetime_from_str(interview_date_str)
        return self._repo.add_record(
            name=name,
            company_name=company,
            subject=subject,
            interview_time=interview_time,
            recording_url=recording_url,
        )
