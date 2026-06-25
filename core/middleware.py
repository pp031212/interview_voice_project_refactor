"""
FastAPI 中间件

包含全局异常处理、日志记录等中间件
"""
from __future__ import annotations

import logging
import traceback
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.errors import AppException, PermanentError, TemporaryError

logger = logging.getLogger(__name__)


def _get_or_create_trace_id(request: Request) -> str:
    """从请求头获取 trace_id，不存在则生成一个。"""
    trace_id = (request.headers.get("X-Trace-ID") or "").strip()
    if trace_id:
        return trace_id
    return uuid.uuid4().hex


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        try:
            response = await call_next(request)
            return response

        except AppException as exc:
            # 获取 trace_id：优先 request.state，其次请求头，兜底生成
            trace_id = getattr(
                getattr(request, "state", None), "trace_id", None
            ) or _get_or_create_trace_id(request)

            # 应用自定义异常
            logger.error(
                f"Application error: {exc.error_code} - {exc.message}",
                extra={
                    "trace_id": trace_id,
                    "error_code": exc.error_code,
                    "error_type": (
                        "temporary" if isinstance(exc, TemporaryError) else "permanent"
                    ),
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # 根据异常类型返回不同的 HTTP 状态码
            if isinstance(exc, TemporaryError):
                resp_status = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                resp_status = status.HTTP_400_BAD_REQUEST

            return JSONResponse(
                status_code=resp_status,
                content={
                    "error": exc.message,
                    "error_code": exc.error_code,
                    "error_type": (
                        "temporary" if isinstance(exc, TemporaryError) else "permanent"
                    ),
                    "trace_id": trace_id,
                },
                headers={"X-Trace-ID": trace_id},
            )

        except Exception as exc:
            # 获取 trace_id：优先 request.state，其次请求头，兜底生成
            trace_id = getattr(
                getattr(request, "state", None), "trace_id", None
            ) or _get_or_create_trace_id(request)

            # 未预期的异常
            logger.error(
                f"Unexpected error: {str(exc)}",
                extra={
                    "trace_id": trace_id,
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc(),
                },
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "服务器内部错误",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "error_type": "unknown",
                    "trace_id": trace_id,
                },
                headers={"X-Trace-ID": trace_id},
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # 确定 trace_id 并挂载到 request.state
        trace_id = _get_or_create_trace_id(request)
        request.state.trace_id = trace_id

        # 记录请求
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # 处理请求
        response = await call_next(request)

        # 响应头带上 trace_id
        response.headers["X-Trace-ID"] = trace_id

        # 记录响应
        logger.info(
            f"Response: {response.status_code}",
            extra={
                "trace_id": trace_id,
                "status_code": response.status_code,
                "path": request.url.path,
            },
        )

        return response
