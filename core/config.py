from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from core.utils.path_utils import get_file_path


load_dotenv()
load_dotenv(get_file_path(".env"))


def _get_int_env(key: str, default: int) -> int:
    """从环境变量读取整数值，解析失败时返回默认值。"""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class AppConfig:
    api_base_url: str
    app_name: str
    log_level: str
    model_api_key: str | None
    model_base_url: str | None
    model_name: str | None
    extract_model_api_key: str | None
    extract_model_base_url: str | None
    extract_model_name: str | None
    report_model_api_key: str | None
    report_model_base_url: str | None
    report_model_name: str | None
    voice_model_path: str | None
    voice_vad_model_path: str | None
    mysql_host: str | None
    mysql_port: int
    mysql_user: str | None
    mysql_password: str | None
    mysql_database_name: str | None
    worker_max_retries: int
    worker_retry_backoff_seconds: int
    asr_resume_cache_ttl_days: int


def get_config() -> AppConfig:
    return AppConfig(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8001"),
        app_name=os.getenv("APP_NAME", "Interview Voice API"),
        log_level=os.getenv("LOG_LEVEL", "info"),
        model_api_key=os.getenv("MODEL_API_KEY"),
        model_base_url=os.getenv("MODEL_BASE_URL"),
        model_name=os.getenv("MODEL_NAME"),
        extract_model_api_key=os.getenv("EXTRACT_MODEL_API_KEY"),
        extract_model_base_url=os.getenv("EXTRACT_MODEL_BASE_URL"),
        extract_model_name=os.getenv("EXTRACT_MODEL_NAME"),
        report_model_api_key=os.getenv("REPORT_MODEL_API_KEY"),
        report_model_base_url=os.getenv("REPORT_MODEL_BASE_URL"),
        report_model_name=os.getenv("REPORT_MODEL_NAME"),
        voice_model_path=os.getenv("VOICE_MODEL_PATH"),
        voice_vad_model_path=os.getenv("VOICE_VAD_MODEL_PATH"),
        mysql_host=os.getenv("MYSQL_HOST"),
        mysql_port=_get_int_env("MYSQL_PORT", 3306),
        mysql_user=os.getenv("MYSQL_USER"),
        mysql_password=os.getenv("MYSQL_PASSWORD"),
        mysql_database_name=os.getenv("MYSQL_DATABASE_NAME"),
        worker_max_retries=_get_int_env("WORKER_MAX_RETRIES", 3),
        worker_retry_backoff_seconds=_get_int_env("WORKER_RETRY_BACKOFF_SECONDS", 30),
        asr_resume_cache_ttl_days=_get_int_env("ASR_RESUME_CACHE_TTL_DAYS", 7),
    )
