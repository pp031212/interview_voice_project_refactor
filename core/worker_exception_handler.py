"""
Worker 异常处理工具

提供统一的异常处理、分类和日志记录
"""
from __future__ import annotations

import logging
import traceback
from typing import Callable

from core.errors import AppException, TemporaryError, PermanentError

logger = logging.getLogger(__name__)


def handle_worker_exception(
    record_id: int,
    exc: Exception,
    context: str = "处理任务",
    trace_id: str | None = None,
) -> tuple[str, bool]:
    """
    处理 Worker 异常

    Args:
        record_id: 记录 ID
        exc: 异常对象
        context: 上下文描述
        trace_id: 可选的任务追踪 ID

    Returns:
        (error_message, is_retryable): 错误消息和是否可重试
    """
    error_message = str(exc)
    is_retryable = False
    trace_prefix = f"[Trace {trace_id}] " if trace_id else ""

    if isinstance(exc, AppException):
        # 应用自定义异常
        error_code = exc.error_code
        is_retryable = isinstance(exc, TemporaryError)

        logger.error(
            f"{trace_prefix}[Record {record_id}] {context}失败: {error_code} - {exc.message}",
            extra={
                "trace_id": trace_id,
                "record_id": record_id,
                "error_code": error_code,
                "error_type": "temporary" if is_retryable else "permanent",
                "context": context,
            },
        )

        error_message = f"[{error_code}] {exc.message}"

    else:
        # 未预期的异常，默认为临时错误（可重试）
        is_retryable = True
        logger.error(
            f"{trace_prefix}[Record {record_id}] {context}时发生未预期错误: {error_message}",
            extra={
                "trace_id": trace_id,
                "record_id": record_id,
                "error_type": "unknown",
                "context": context,
                "traceback": traceback.format_exc(),
            },
        )

    return error_message[:500], is_retryable


def with_exception_handling(func: Callable) -> Callable:
    """
    异常处理装饰器

    用于包装可能抛出异常的函数，统一处理异常
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException as exc:
            logger.error(
                f"Application error in {func.__name__}: {exc.error_code} - {exc.message}",
                extra={
                    "function": func.__name__,
                    "error_code": exc.error_code,
                    "error_type": (
                        "temporary" if isinstance(exc, TemporaryError) else "permanent"
                    ),
                },
            )
            raise
        except Exception as exc:
            logger.error(
                f"Unexpected error in {func.__name__}: {str(exc)}",
                extra={
                    "function": func.__name__,
                    "traceback": traceback.format_exc(),
                },
            )
            raise

    return wrapper
