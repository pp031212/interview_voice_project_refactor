from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from fastapi import UploadFile

from core.errors import FileUploadError, ValidationError, RecordNotFoundError
from core.task_status import InterviewProcessingStatus
from core.utils.path_utils import get_file_extension
from core.utils.time_utils import get_current_time, get_datetime_from_str

from infra.db.repo import InterviewRepository

# 支持的音频文件扩展名（大小写不敏感）
ALLOWED_AUDIO_EXTENSIONS: set[str] = {".mp3", ".wav", ".flac", ".aac", ".m4a"}

# 最大上传文件大小：200MB
MAX_UPLOAD_SIZE_BYTES: int = 200 * 1024 * 1024

# 分块读取大小：1MB
CHUNK_SIZE_BYTES: int = 1 * 1024 * 1024

# 文件名中需要清理的非法字符
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


@dataclass(frozen=True)
class UploadInfo:
    """Information about a saved upload."""

    relative_path: str
    absolute_path: Path
    original_filename: str
    saved_filename: str


def _sanitize_filename_part(value: str) -> str:
    """清理文件名中的非法字符。

    Args:
        value: 原始字符串（如姓名、公司名）。

    Returns:
        清理后的字符串，可安全用于文件名。
    """
    if not value:
        return "unknown"

    # 替换非法字符为空格，然后将空格替换为下划线
    cleaned = INVALID_FILENAME_CHARS.sub(" ", value)
    cleaned = cleaned.strip().replace(" ", "_")

    # 如果清理后为空，返回默认值
    return cleaned if cleaned else "unknown"


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
        # 1. 基础校验
        if not file.filename:
            raise ValidationError("文件名不能为空")

        if not name or not company:
            raise ValidationError("姓名和公司名不能为空")

        # 2. 扩展名校验（大小写不敏感）
        original_filename = file.filename
        extension = get_file_extension(original_filename).lower()

        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
            raise ValidationError(
                f"不支持的文件格式: {extension}，支持的格式: {allowed_list}"
            )

        # 3. 安全文件名处理
        safe_name = _sanitize_filename_part(name)
        safe_company = _sanitize_filename_part(company)
        saved_filename = f"{get_current_time()}_{safe_name}_{safe_company}{extension}"
        relative_path = str(Path("data") / "uploads" / saved_filename)
        absolute_path = self._upload_dir / saved_filename

        # 4. 分块写入文件并累计大小
        total_size = 0
        try:
            with absolute_path.open("wb") as output_file:
                while True:
                    chunk = file.file.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    total_size += len(chunk)

                    # 检查是否超过最大大小
                    if total_size > MAX_UPLOAD_SIZE_BYTES:
                        # 超过限制，关闭文件并删除
                        output_file.close()
                        self._cleanup_file(absolute_path)
                        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                        raise ValidationError(
                            f"文件大小超过限制: {max_mb}MB"
                        )

                    output_file.write(chunk)

            return UploadInfo(
                relative_path=relative_path,
                absolute_path=absolute_path,
                original_filename=original_filename,
                saved_filename=saved_filename,
            )

        except ValidationError:
            # 验证错误直接抛出，不包装
            raise
        except Exception as exc:
            # 写入失败时清理残留文件
            self._cleanup_file(absolute_path)
            raise FileUploadError(f"文件上传失败: {str(exc)}")

    def _cleanup_file(self, file_path: Path) -> None:
        """清理残留文件。

        Args:
            file_path: 要删除的文件路径。
        """
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as cleanup_exc:
            # 清理失败不覆盖原始异常，仅打印
            print(f"警告: 清理残留文件失败: {cleanup_exc}")

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

    def retry_failed_record(self, record_id: int | str) -> dict[str, Any]:
        """Reset a failed record to pending so Worker can resume it.

        The method keeps all checkpoint/cache data intact. Worker will pick the
        record up on the next poll and continue from existing checkpoints.

        Args:
            record_id: Interview record id.

        Returns:
            Updated record dict.

        Raises:
            RecordNotFoundError: If record does not exist.
            ValidationError: If current status is not failed.
        """
        record = self.get_record(record_id)
        status = record.get("processing_status")
        try:
            status_value = int(status)
        except (TypeError, ValueError):
            raise ValidationError(f"记录状态异常，无法继续处理: {status}")

        if status_value == int(InterviewProcessingStatus.PROCESSING):
            raise ValidationError("记录正在处理中，无需继续处理")
        if status_value == int(InterviewProcessingStatus.COMPLETED):
            raise ValidationError("记录已处理完成，无需继续处理")
        if status_value != int(InterviewProcessingStatus.FAILED):
            raise ValidationError("只有处理失败的记录可以继续处理")

        self._repo.reset_record_to_pending(
            record_id,
            processing_tips="等待重新处理（用户手动继续，保留断点）",
        )
        return self.get_record(record_id)
