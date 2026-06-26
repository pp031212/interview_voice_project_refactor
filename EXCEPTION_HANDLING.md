# 异常处理使用指南

本文档说明如何在项目中使用统一的异常处理机制。

## 异常分类

系统中的异常分为两大类：

### 1. 临时错误（TemporaryError）- 可重试
- `DatabaseError` - 数据库连接或查询错误
- `LLMError` - LLM 调用错误
- `LLMTimeoutError` - LLM 调用超时
- `ASRError` - ASR 处理错误

### 2. 永久错误（PermanentError）- 需人工介入
- `RecordNotFoundError` - 记录不存在
- `FileUploadError` - 文件上传错误
- `FileNotFoundError` - 文件不存在
- `ValidationError` - 数据验证错误
- `BusinessError` - 业务逻辑错误

## 在代码中使用

### 1. 抛出自定义异常

```python
from core.errors import RecordNotFoundError, DatabaseError, ValidationError

# 记录不存在
if not record:
    raise RecordNotFoundError(record_id)

# 数据库错误
try:
    db.query(...)
except Exception as e:
    raise DatabaseError(f"查询失败: {str(e)}")

# 验证错误
if not file_name:
    raise ValidationError("文件名不能为空")
```

### 2. FastAPI 路由

FastAPI 的全局异常处理中间件会自动捕获并处理异常：

```python
from fastapi import APIRouter
from core.errors import RecordNotFoundError

@router.get("/record/{record_id}")
async def get_record(record_id: int):
    record = service.get_record(record_id)
    if not record:
        raise RecordNotFoundError(record_id)  # 自动返回 400 错误
    return record
```

### 3. Worker 任务

Worker 使用 `handle_worker_exception` 处理异常：

```python
from core.worker_exception_handler import handle_worker_exception

try:
    # 处理任务
    process_task(record_id)
except Exception as exc:
    error_info = handle_worker_exception(
        record_id, exc, "处理任务"
    )
    # error_info 包含 error_code/error_type/error_message/is_retryable
    # Worker 会把这些字段写入面试记录，供详情页展示和重试策略判断
```

Worker 失败时会写入主表结构化字段：
- `error_code`：错误代码，如 `DATABASE_ERROR`、`ASR_ERROR`、`LLM_ERROR`
- `error_type`：`temporary` 或 `permanent`
- `error_message`：面向用户的失败原因
- `retry_count` / `max_retries`：当前重试次数和上限
- `failed_at`：失败时间

## 异常响应格式

### FastAPI 响应

**临时错误（503）：**
```json
{
  "error": "数据库连接失败",
  "error_code": "DATABASE_ERROR",
  "error_type": "temporary"
}
```

**永久错误（400）：**
```json
{
  "error": "记录 123 不存在",
  "error_code": "RECORD_NOT_FOUND",
  "error_type": "permanent"
}
```

**未知错误（500）：**
```json
{
  "error": "服务器内部错误",
  "error_code": "INTERNAL_SERVER_ERROR",
  "error_type": "unknown"
}
```

## 日志记录

所有异常都会自动记录到日志中，包含：
- 错误代码
- 错误类型（temporary/permanent/unknown）
- 请求路径（FastAPI）
- 记录 ID（Worker）
- 堆栈跟踪（未预期错误）

## 添加新的异常类型

在 `core/errors.py` 中添加：

```python
class MyCustomError(PermanentError):
    """自定义错误描述"""

    def __init__(self, message: str):
        super().__init__(message, "MY_CUSTOM_ERROR")
```
