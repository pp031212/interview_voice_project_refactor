from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    """Return refactor project root path."""
    return Path(__file__).resolve().parents[2]


def get_file_path(relative_path: str) -> str:
    """Return absolute path for a refactor-project-relative path."""
    path_obj = Path(relative_path)
    if path_obj.is_absolute():
        return str(path_obj)

    normalized = relative_path.replace("\\", "/")
    legacy_prefix = "interview_voice_project_refactor/"
    if normalized.startswith(legacy_prefix):
        normalized = normalized[len(legacy_prefix):]

    return str(get_repo_root() / normalized)


def get_file_extension(file_path: str) -> str:
    """Return file extension including leading dot."""
    return Path(file_path).suffix


def to_project_relative_path(path: str) -> str:
    """Convert an absolute/legacy path to refactor-project-relative path."""
    normalized = path.replace("\\", "/")
    legacy_prefix = "interview_voice_project_refactor/"
    if normalized.startswith(legacy_prefix):
        return normalized[len(legacy_prefix):]

    path_obj = Path(path)
    if path_obj.is_absolute():
        try:
            return str(path_obj.resolve().relative_to(get_repo_root().resolve())).replace("\\", "/")
        except Exception:
            return normalized
    return normalized
