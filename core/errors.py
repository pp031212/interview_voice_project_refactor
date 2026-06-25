"""
异常定义与分类

定义系统中的异常类型，区分临时错误和永久错误
"""
from __future__ import annotations


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        super().__init__(self.message)


class TemporaryError(AppException):
    """临时错误（可重试）"""

    pass


class PermanentError(AppException):
    """永久错误（需人工介入）"""

    pass


# 数据库相关错误
class DatabaseError(TemporaryError):
    """数据库连接或查询错误"""

    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR")


class RecordNotFoundError(PermanentError):
    """记录不存在"""

    def __init__(self, record_id: int):
        super().__init__(f"记录 {record_id} 不存在", "RECORD_NOT_FOUND")
        self.record_id = record_id


# 文件相关错误
class FileUploadError(PermanentError):
    """文件上传错误"""

    def __init__(self, message: str):
        super().__init__(message, "FILE_UPLOAD_ERROR")


class FileNotFoundError(PermanentError):
    """文件不存在"""

    def __init__(self, file_path: str):
        super().__init__(f"文件 {file_path} 不存在", "FILE_NOT_FOUND")
        self.file_path = file_path


# 验证相关错误
class ValidationError(PermanentError):
    """数据验证错误"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


# LLM 相关错误
class LLMError(TemporaryError):
    """LLM 调用错误"""

    def __init__(self, message: str):
        super().__init__(message, "LLM_ERROR")


class LLMTimeoutError(TemporaryError):
    """LLM 调用超时"""

    def __init__(self, message: str):
        super().__init__(message, "LLM_TIMEOUT")


# ASR 相关错误
class ASRError(TemporaryError):
    """ASR 处理错误"""

    def __init__(self, message: str):
        super().__init__(message, "ASR_ERROR")


# 业务逻辑错误
class BusinessError(PermanentError):
    """业务逻辑错误"""

    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_ERROR")
