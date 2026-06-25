from __future__ import annotations

from core.config import AppConfig, get_config


WorkerConfig = AppConfig


def get_worker_config() -> AppConfig:
    return get_config()
