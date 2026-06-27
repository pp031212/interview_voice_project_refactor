"""ASR 分片断点缓存查询服务。

只读服务，用于查询 DB 缓存状态和文件兜底缓存状态。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from core.utils.path_utils import get_file_path, to_project_relative_path
from infra.db.db_helper import my_db_helper


# 文件名中提取 record_id 的正则
_RECORD_ID_PATTERN = re.compile(r"^record_(\d+)\.json$")


def _parse_record_id_from_filename(filename: str) -> int | None:
    """从文件名中解析 record_id。

    Args:
        filename: 文件名，如 "record_123.json"。

    Returns:
        解析出的 record_id，解析失败返回 None。
    """
    match = _RECORD_ID_PATTERN.match(filename)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def _read_fallback_file_summary(path: Path) -> dict:
    """读取 ASR 兜底缓存文件的摘要信息。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "split_count": None,
            "cached_segment_count": None,
            "updated_at": None,
        }

    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    results = payload.get("results", {}) if isinstance(payload, dict) else {}
    split_count = meta.get("split_count") if isinstance(meta, dict) else None
    updated_at = meta.get("updated_at") if isinstance(meta, dict) else None
    cached_segment_count = len(results) if isinstance(results, dict) else None

    return {
        "split_count": split_count if isinstance(split_count, int) else None,
        "cached_segment_count": cached_segment_count,
        "updated_at": updated_at if isinstance(updated_at, str) else None,
    }


class AsrResumeCacheService:
    """ASR 分片断点缓存查询服务。"""

    def __init__(self) -> None:
        self._asr_resume_dir = Path(get_file_path("data/checkpoints/asr_resume"))

    def get_db_cache_status(
        self, record_id: int | None = None
    ) -> list[dict]:
        """查询 DB 中的 ASR 分片缓存聚合状态。

        Args:
            record_id: 指定记录 ID；为 None 时查询全部。

        Returns:
            包含 record_id, segment_count, first_update_time, last_update_time 的字典列表。
        """
        return my_db_helper.get_asr_segment_cache_status(record_id)

    def get_fallback_files(
        self, record_id: int | None = None
    ) -> list[dict]:
        """扫描文件兜底缓存目录。

        只扫描 data/checkpoints/asr_resume/ 下的 record_*.json 普通文件，
        排除 symlink。

        Args:
            record_id: 指定记录 ID 时只返回对应的文件。

        Returns:
            包含 record_id, filename, relative_path, modified_time, size_bytes 的字典列表。
        """
        results: list[dict] = []

        if not self._asr_resume_dir.is_dir():
            return results

        for entry in self._asr_resume_dir.iterdir():
            # 只处理普通文件
            if not entry.is_file():
                continue
            # 排除 symlink
            if entry.is_symlink():
                continue
            # 只匹配 record_*.json
            if not _RECORD_ID_PATTERN.match(entry.name):
                continue

            parsed_id = _parse_record_id_from_filename(entry.name)

            # record_id 过滤
            if record_id is not None and parsed_id != record_id:
                continue

            stat = entry.stat()
            relative_path = to_project_relative_path(str(entry))
            file_summary = _read_fallback_file_summary(entry)

            results.append(
                {
                    "record_id": parsed_id,
                    "filename": entry.name,
                    "relative_path": relative_path,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime),
                    "size_bytes": stat.st_size,
                    **file_summary,
                }
            )

        # 按 record_id 排序，None 排最后
        results.sort(key=lambda x: (x["record_id"] is None, x["record_id"] or 0))
        return results

    def get_status(self, record_id: int | None = None) -> dict:
        """获取完整的 ASR 分片断点缓存状态。

        Args:
            record_id: 指定记录 ID；为 None 时查询全部。

        Returns:
            包含 db_cache, fallback_files, db_record_count, fallback_file_count 的字典。
        """
        db_cache = self.get_db_cache_status(record_id)
        fallback_files = self.get_fallback_files(record_id)

        return {
            "db_cache": db_cache,
            "fallback_files": fallback_files,
            "db_record_count": len(db_cache),
            "fallback_file_count": len(fallback_files),
        }
