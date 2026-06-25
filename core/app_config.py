from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiPaths:
    """API-specific path configuration."""

    project_root: Path
    upload_dir: Path


def get_api_paths() -> ApiPaths:
    project_root = Path(__file__).resolve().parents[1]
    upload_dir = project_root / "data" / "uploads"
    return ApiPaths(project_root=project_root, upload_dir=upload_dir)
