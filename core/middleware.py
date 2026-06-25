"""
FastAPI 中间件

包含全局异常处理、日志记录等中间件
"""
from __future__ import annotations

import logging
import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.errors import AppException, PermanentError, TemporaryError

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        try:
            response = await call_next(request)
            return response

        except AppException as exc:
            # 应用自定义异常
            logger.error(
                f"Application error: {exc.error_code} - {exc.message}",
                extra={
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
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                status_code = status.HTTP_400_BAD_REQUEST

            return JSONResponse(
                status_code=status_code,
                content={
                    "error": exc.message,
                    "error_code": exc.error_code,
                    "error_type": (
                        "temporary" if isinstance(exc, TemporaryError) else "permanent"
                    ),
                },
            )

        except Exception as exc:
            # 未预期的异常
            logger.error(
                f"Unexpected error: {str(exc)}",
                extra={
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
                },
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # 记录请求
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # 处理请求
        response = await call_next(request)

        # 记录响应
        logger.info(
            f"Response: {response.status_code}",
            extra={
                "status_code": response.status_code,
                "path": request.url.path,
            },
        )

        return response
