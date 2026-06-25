from __future__ import annotations

from fastapi import Depends

from core.app_config import get_api_paths
from infra.db.repo import InterviewRepository
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
