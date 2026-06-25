"""ASR 分片断点缓存查询路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import asr_resume_cache_service_dep
from app.schemas.asr_resume import AsrResumeCacheStatusResponse
from services.asr_resume_cache_service import AsrResumeCacheService

router = APIRouter()


@router.get(
    "/asr_resume_cache/status",
    response_model=AsrResumeCacheStatusResponse,
    tags=["ASR Resume Cache"],
)
async def get_asr_resume_cache_status(
    record_id: int | None = None,
    service: AsrResumeCacheService = Depends(asr_resume_cache_service_dep),
) -> AsrResumeCacheStatusResponse:
    """查询 ASR 分片断点缓存状态。

    Args:
        record_id: 可选，指定记录 ID 过滤。
        service: ASR 缓存查询服务（依赖注入）。

    Returns:
        包含 DB 缓存状态和文件兜底缓存状态的响应。
    """
    status = service.get_status(record_id=record_id)
    return AsrResumeCacheStatusResponse(**status)
