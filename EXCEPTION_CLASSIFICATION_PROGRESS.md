# 异常分类实施进度

本文档记录项目中异常分类的实施情况。

## 已完成的模块

### 1. 核心层（core/）
- ✅ `core/errors.py` - 异常类型定义
- ✅ `core/middleware.py` - FastAPI 异常处理中间件
- ✅ `core/worker_exception_handler.py` - Worker 异常处理工具

### 2. 基础设施层（infra/）
- ✅ `infra/db/db_helper.py` - 数据库操作异常
  - `_ensure_tables_created()` - 抛出 `DatabaseError`
  - `get_user_by_id()` - 抛出 `DatabaseError`

### 3. 服务层（services/）
- ✅ `services/interview_service.py` - 业务服务异常
  - `get_record()` - 抛出 `RecordNotFoundError`
  - `save_upload()` - 抛出 `ValidationError`, `FileUploadError`
  - `create_record()` - 抛出 `ValidationError`

### 4. API 层（apps/api/）
- ✅ `apps/api/app/main.py` - 集成异常处理中间件
- ✅ `apps/api/app/routes/interviews.py` - 简化路由，依赖中间件处理异常

### 5. Worker 层（apps/worker/）
- ✅ `apps/worker/app/tasks.py` - 使用统一异常处理

### 6. Pipeline 节点（pipelines/nodes/）
- ✅ `__002__voice_to_text_node.py` - ASR 节点异常处理
  - `void2text()` - 抛出 `ASRError`

## 待完善的模块

### 1. 数据库层（infra/db/）
- ⏳ `db_helper.py` - 其他数据库操作方法（约 20+ 方法）
- ⏳ `repo.py` - Repository 层异常处理

### 2. Pipeline 节点（pipelines/nodes/）
- ⏳ `__003__arrange_text_node.py` - 文本整理节点
- ⏳ `__004__extract_interview_topic_node.py` - 问答抽取节点
- ⏳ `__005__offer_sample_answer_node.py` - 逐题分析节点
- ⏳ `__006__offer_interview_advice_node.py` - 总评节点
- ⏳ `__007__generate_markdown_node.py` - Markdown 生成节点

### 3. LLM 层（core/）
- ⏳ `core/llm.py` - LLM 调用异常处理
  - 添加 `LLMError`, `LLMTimeoutError`

### 4. 文件存储层（infra/storage/）
- ⏳ 如果存在文件存储模块，添加 `FileNotFoundError`

## 使用统计

- **已实施模块**: 6 个
- **待完善模块**: 约 10+ 个
- **覆盖率**: ~40%（核心路径已覆盖）

## 优先级建议

### P0 - 立即完善
1. `db_helper.py` 的核心查询方法（`get_interview_record_by_id`, `update_interview_record` 等）
2. LLM 调用层（`core/llm.py`）
3. 问答抽取和分析节点（`__004__`, `__005__`, `__006__`）

### P1 - 逐步完善
1. 其他 pipeline 节点
2. Repository 层
3. 文件存储层

### P2 - 可选完善
1. 工具函数层
2. 配置加载层

## 注意事项

1. **向后兼容**: 现有代码仍可正常运行，异常会被中间件捕获
2. **渐进式迁移**: 不需要一次性修改所有代码
3. **优先核心路径**: 先完善用户请求的主要路径
4. **保持一致性**: 使用统一的异常类型和错误消息格式
