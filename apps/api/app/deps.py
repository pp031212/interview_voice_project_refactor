from __future__ import annotations

from fastapi import Depends

from core.app_config import get_api_paths
from infra.db.repo import InterviewRepository
from services.asr_resume_cache_service import AsrResumeCacheService
from services.interview_service import InterviewService


def get_interview_service() -> InterviewService:
    """Provide InterviewService instance.

    Returns:
        InterviewService: Configured service.
    """
    paths = get_api_paths()
    return InterviewService(repo=InterviewRepository(), upload_dir=paths.upload_dir)


def interview_service_dep() -> InterviewService:
    """FastAPI dependency wrapper for InterviewService."""
    return get_interview_service()


InterviewServiceDep = Depends(interview_service_dep)


def get_asr_resume_cache_service() -> AsrResumeCacheService:
    """Provide AsrResumeCacheService instance.

    Returns:
        AsrResumeCacheService: Configured service.
    """
    return AsrResumeCacheService()


def asr_resume_cache_service_dep() -> AsrResumeCacheService:
    """FastAPI dependency wrapper for AsrResumeCacheService."""
    return get_asr_resume_cache_service()


AsrResumeCacheServiceDep = Depends(asr_resume_cache_service_dep)
