# 交接速览（Handoff）

本文件用于下次会话快速接手。

## 当前项目位置

- 重构项目根目录：`interview_voice_project_refactor/`

## 已完成

- 结构已对齐 `REFACTOR_PLAN.md`
- 共享层已收敛：`core/`, `infra/`, `services/`, `pipelines/`
- apps 已拆分：`apps/api`, `apps/worker`, `apps/ui`
- 数据、模型与检查点已迁移到 `interview_voice_project_refactor/data/`
- LangGraph checkpoint 路径已稳定到 `data/checkpoints/langgraph_checkpoints.db`
- ASR 分片级断点续传已落地（DB 主存 + 文件兜底）：
  - 主存表：`tb_asr_segment_cache`
  - 文件兜底：`data/checkpoints/asr_resume/record_<id>.json`
  - 成功后自动清理 DB/文件中间态
- Q&A 抽取级断点续传已落地（DB 主存）：
  - 主存表：`tb_interview_extract_cache`
  - 命中缓存时跳过 `__004__` 重新抽取
- 逐题分析级断点续传已落地（DB 主存）：
  - 主存表：`tb_interview_analysis_cache`（键：`record_id + qa_index`）
  - `__005__` 命中缓存题目跳过 LLM，仅补跑未完成题目
  - `__005__` 明细写入前先清空后重建，避免重复明细
  - Worker 成功后统一清理分析缓存
- 运维/测试脚本已迁移到 `scripts/`
- 依赖安装/启动/配置文档已补充
- 路径策略已统一为”项目相对路径”语义（含历史绝对路径兼容）
- GPT 定向兼容代码已按需回退（恢复基础 JSON 解析 + 保底）
- 配置规范已明确：禁止使用 GPT 系列模型
- LLM 默认客户端已改为懒加载；`MODEL_*` 缺失时可回退到 `REPORT_MODEL_*` / `EXTRACT_MODEL_*`，避免 Worker 导入阶段崩溃
- P0 优化已完成 4 项：
  - 健康检查路由（`/health` 和 `/readiness` 端点）
  - 统一配置加载（删除重复的 `load_dotenv()` 调用）
  - 全局异常处理中间件（FastAPI + Worker，支持异常分类和统一日志）
  - 异常分类完善（核心模块已使用具体异常类型，覆盖率约 40%）

## 关键文档

- `REFACTOR_PLAN.md`：重构规划与目标结构
- `PROGRESS.md`：已完成进度
- `NEXT_OPTIMIZATIONS.md`：唯一待办/优化来源（已按 `P0/P1/P2` 重排）
- `README_STARTUP.md`：启动步骤
- `启动流程与PyCharm配置.md`：PyCharm 运行配置
- `相关依赖的安装指南.md`：conda + requirements + FFmpeg
- `WORKFLOW_DETAIL.md`：详细流程（本地处理/LLM处理/断点机制）
- `EXCEPTION_HANDLING.md`：异常处理使用指南
- `EXCEPTION_CLASSIFICATION_PROGRESS.md`：异常分类实施进度追踪

## 启动路径（refactor）

- FastAPI：`apps/api` → `uvicorn app.main:app --host 0.0.0.0 --port 8001`
- Worker：`apps/worker` → `python -m app.main`
- UI：`apps/ui` → `streamlit run app/main.py`

## 注意事项

- `.env` 在 `interview_voice_project_refactor/.env`
- 模型路径建议使用相对路径：`data/models/...`（现有绝对路径可用但不推荐）
- 上传文件路径：`data/uploads`
- 切分语音输出路径：`data/voice`
- Markdown 输出路径：`markdown_reports/`（位于 refactor 根目录）
- 请使用非 GPT 模型，避免反问 schema 相关问题
- 若未配置 `MODEL_*`，请确保至少配置 `EXTRACT_MODEL_*` 或 `REPORT_MODEL_*` 且 `*_MODEL_NAME` 非空
- 当前数据库可能已被清空并重置自增（如需回放请先重新导入或重新上传测试数据）
