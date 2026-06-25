"""ASR 分片断点缓存相关的 Pydantic 响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AsrSegmentCacheStatusItem(BaseModel):
    """单条 ASR 分片缓存聚合状态（按 record_id 聚合）。"""

    record_id: int = Field(..., description="面试记录 ID")
    segment_count: int = Field(..., description="该记录下的分片数量")
    first_update_time: datetime | None = Field(None, description="最早分片更新时间")
    last_update_time: datetime | None = Field(None, description="最晚分片更新时间")


class AsrResumeFileItem(BaseModel):
    """单个 ASR 断点续传兜底文件信息。"""

    record_id: int | None = Field(None, description="从文件名解析的记录 ID，解析失败为 None")
    filename: str = Field(..., description="文件名")
    relative_path: str = Field(..., description="项目相对路径")
    modified_time: datetime = Field(..., description="文件最后修改时间")
    size_bytes: int = Field(..., description="文件大小（字节）")


class AsrResumeCacheStatusResponse(BaseModel):
    """ASR 分片断点缓存状态查询响应。"""

    db_cache: list[AsrSegmentCacheStatusItem] = Field(
        default_factory=list, description="DB 中的缓存聚合状态"
    )
    fallback_files: list[AsrResumeFileItem] = Field(
        default_factory=list, description="文件兜底缓存列表"
    )
    db_record_count: int = Field(..., description="DB 缓存中的记录数")
    fallback_file_count: int = Field(..., description="文件兜底缓存文件数")
