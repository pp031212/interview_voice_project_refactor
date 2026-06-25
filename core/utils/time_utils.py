from __future__ import annotations

from datetime import datetime


def get_current_time() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_current_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def get_datetime_str_from_datetime(date_time: datetime) -> str:
    return date_time.strftime("%Y%m%d")


def get_datetime_from_str(date_str: str) -> datetime:
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")
