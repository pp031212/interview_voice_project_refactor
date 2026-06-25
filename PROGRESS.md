# 重构进度记录

## 2026-02-28

- 完成 FastAPI 重构子项目骨架：`interview_voice_project_refactor/fastapi_service/`。
- 引入分层结构：`app/`, `core/`, `infra/`, `services/`。
- 路由改为依赖注入 + service 调用，保持原行为。
- 新增 Pydantic schema，接口参数/返回结构保持不变。
- 迁移数据库层到 `infra/db/`，不再依赖原 `__002__db_helper_parse/`。
- 迁移路径/时间工具到 `core/utils/`，不再依赖原 `common/`。
- 新增 UI 重构子项目：`interview_voice_project_refactor/ui_service/`，迁移 Streamlit 页面与入口。
- 新增 Worker 重构子项目：`interview_voice_project_refactor/worker_service/`，拆分 `main.py` 与 `tasks.py`。
- Worker 依赖迁移：`pipeline/` + `infra/db/` + `core/*` 均已本地化，不再依赖原 `__001__langgraph_more_node` / `__002__db_helper_parse` / `common`。
- UI 基础配置统一：新增 `core/config.py`，支持 `API_BASE_URL`（默认 `http://127.0.0.1:8001`），页面调用改为读配置。
- Worker 配置预埋：新增 `core/worker_config.py`，统一读取 `API_BASE_URL`。
- 新增 `interview_voice_project_refactor/.env.example`，统一 refactor 子项目的环境变量模板。
- 修复 Worker `langgraph_agent.py` 中重复的 `build_graph` 定义。
- 按 `REFACTOR_PLAN.md` 对齐目录：迁移到 `interview_voice_project_refactor/apps/api`、`interview_voice_project_refactor/apps/worker`、`interview_voice_project_refactor/apps/ui`。
- 将共享层收敛到 `interview_voice_project_refactor/` 根目录：`core/`, `infra/`, `services/`, `pipelines/`。
- 新增 `interview_voice_project_refactor/README_STARTUP.md`，统一 refactor 启动说明。
- 修复 FastAPI 依赖注入声明（避免误判为请求体字段）。
- 迁移 `common/markdown_utils.py` 到 `interview_voice_project_refactor/core/markdown_utils.py`。
- FastAPI 配置统一：新增 `APP_NAME` / `LOG_LEVEL`，应用于 FastAPI 标题。
- 迁移原项目检查点到 `interview_voice_project_refactor/data/checkpoints/`，并更新 LangGraph checkpointer 路径。
- 迁移 `uploaded_files`、`voice`、`voice_file` 到 `interview_voice_project_refactor/data/`，并更新路径引用。
- 将项目目录重命名为 `interview_voice_project_refactor`，并更新路径引用。
- 迁移数据库初始化脚本与 SQL：`scripts/setup_database.py`、`scripts/init_database.sql`、`scripts/fix_markdown_text_column.sql`。
- 迁移运维脚本：`scripts/manage_checkpoints.py`、`scripts/reset_failed_records.py`、`scripts/check_database_status.py`。
- 迁移测试脚本：`scripts/test_checkpoint.py`、`scripts/test_langgraph_checkpoint_simple.py`。
- 新增依赖安装指南：`相关依赖的安装指南.md`。
- 新增启动流程与 PyCharm 配置指南：`启动流程与PyCharm配置.md`。
- 新增优化空间清单：`NEXT_OPTIMIZATIONS.md`。
- 新增交接速览：`HANDOFF.md`。

## 2026-03-02

- 修复 `__005__offer_sample_answer_node.py` 的 JSON 解析稳定性问题：增加 JSON 文本清理、未转义双引号修复、失败兜底结构，避免单题解析异常导致整条流水线失败。
- 合并数据库脚本：将 `scripts/fix_markdown_text_column.sql` 的 LONGTEXT 升级逻辑并入 `scripts/init_database.sql`（建表定义 + 兼容旧库 ALTER），并删除独立修复脚本文件。
- 增加 checkpoint 数据库自愈能力：在 `pipelines/langgraph_agent.py` 中加入启动完整性检查（`PRAGMA integrity_check`）与运行期/清理期 `database disk image is malformed` 自动重建与重试机制。
- 修复 Markdown 文件落盘路径：`__007__generate_markdown_node.py` 改为保存到 `interview_voice_project_refactor/markdown_reports`，不再落到仓库根目录的旧 `markdown_reports`。
- 完成 Markdown 历史文件迁移：将仓库根目录 `markdown_reports/` 整体迁移到 `interview_voice_project_refactor/markdown_reports/`，并删除旧目录。
- 统一 refactor 项目内文件路径为相对路径语义：`path_utils` 以 `interview_voice_project_refactor` 为根解析路径，并兼容旧前缀；同步更新 config、db_config、app_config、pipeline 节点、checkpoint 脚本与上传路径存储逻辑。
- 更新 `NEXT_OPTIMIZATIONS.md`：新增评分一致性、本地评分规则、术语识别准确率、ASR 分片级断点续传等优化方向。
- 新增流程文档 `WORKFLOW_DETAIL.md`：系统化梳理当前本地处理与 LLM 处理链路、输入输出、落库行为与 checkpoint 机制。
- 继续补充优化方向：在 `NEXT_OPTIMIZATIONS.md` 增加科大讯飞 ASR 接入评估、可插拔 ASR Provider 抽象、双引擎低置信度复核策略。
- 修复 `offer_sample_answer_node` 结果字段缺失导致的崩溃：增加 LLM 返回结果归一化（`analysis/sample_answer` 补齐、评分安全转换、同义字段兜底），避免 `KeyError: 'sample_answer'` 中断流程。
- 修复 `offer_interview_advice_node` 在非 JSON 输出时的中断问题：增加总评 JSON 提取修复、字段归一化与保底结果，避免 `OUTPUT_PARSING_FAILURE` 触发整条流程重跑。
- 实现 ASR 分片级断点续传：`__002__voice_to_text_node` 增加 `data/checkpoints/asr_resume/record_<id>.json` 中间态持久化，失败重跑时跳过已完成分片，仅继续未完成分片，全部成功后自动清理中间文件。
- 同步更新待办与未来优化文档：在 `TODO.md` 增加“已完成（ASR 分片级断点续传）”条目；在 `NEXT_OPTIMIZATIONS.md` 为断点粒度项标记完成状态并补充下一步（DB 持久化与 TTL 清理）。
- 增强 GPT-5.2 兼容性与结果质量：`offer_interview_advice_node` 增加“解析失败→提取 JSON 主体→LLM 重排修复→保底结果”多级兜底；`offer_sample_answer_node` 增加平铺字段兼容与 `sample_answer` 字典转文本，修复 Markdown 中空总评与字典串展示问题。
- 实现“混合但 DB 为主”的 ASR 中间文本持久化：新增 `tb_asr_segment_cache` 表与 DBHelper 读写接口，`voice_to_text` 改为优先读写数据库缓存（文件仅兜底），并在任务成功后清理 DB/文件中间态。
- 同步数据库初始化脚本与文档：更新 `scripts/init_database.sql`、`scripts/setup_database.py` 以及 `WORKFLOW_DETAIL.md` / `NEXT_OPTIMIZATIONS.md` / `TODO.md` 的断点机制说明。
- 修复总评提示词污染问题：`offer_interview_advice_node` 新增“提示词污染检测 + 基于原始面试文本重生成”机制，避免将模型反问 schema/输出规范等元对话内容写入最终 Markdown。
- 优化 ASR 分片缓存路径存储：`tb_asr_segment_cache.segment_path` 改为项目相对路径（不再写绝对路径），并在读取缓存时兼容历史绝对路径归一化，提升跨环境可移植性与隐私安全性。
- 按需回退 GPT 定向兼容逻辑：移除 `offer_interview_advice_node` 与 `offer_sample_answer_node` 中针对 GPT 系列的特化修复链路，恢复为基础 JSON 解析与保底策略。
- 配置指南新增限制：在 `README_STARTUP.md`、`启动流程与PyCharm配置.md`、`.env.example` 明确“禁止使用第三方 API 调用 GPT 系列模型，GPT 必须使用官方 `https://api.openai.com/v1`”。
- 文档整合：将 `TODO.md` 的待办/搁置内容并入 `NEXT_OPTIMIZATIONS.md` 统一维护；`TODO.md` 改为归档指引，避免双份清单不一致。
- 优化清单重排：`NEXT_OPTIMIZATIONS.md` 按 `P0/P1/P2` 优先级重构，纳入原 TODO 搁置项并统一状态。
- 删除 `TODO.md`，后续仅维护 `NEXT_OPTIMIZATIONS.md` 作为唯一待办与优化来源。
- 更新 `HANDOFF.md`：同步最新可交接状态（ASR 分片断点 DB 主存、路径策略、GPT 配置限制、文档入口变更与当前注意事项）。
- 修复 ASR 中间文本清理时机：`voice_to_text` 不再在节点完成时清理缓存，改为 Worker 在整条流程成功后统一清理，确保后续节点失败时可复用中间文本断点。
- 实现按任务路由模型：新增 `EXTRACT_MODEL_*`（用于 `__003__/__004__`）与 `REPORT_MODEL_*`（用于 `__005__/__006__`）配置；对应节点已切换到 `core.llm` 的路由函数，未配置时自动回退 `MODEL_*` 默认模型。
- 修复 Worker 启动期 LLM 初始化崩溃：`core/llm.py` 改为懒加载与回退策略（默认模型可回退到 REPORT/EXTRACT 模型），避免 `MODEL_NAME` 缺失时在 import 阶段抛出 `ValidationError`。
- 文档同步更新：`README_STARTUP.md`、`启动流程与PyCharm配置.md`、`HANDOFF.md`、`WORKFLOW_DETAIL.md` 补充 `MODEL_*` 可选说明、任务路由回退策略与 `ChatOpenAI model=None` 启动报错排查指引。




- 统一治理模型思考文本污染：新增 core/llm_output_utils.py，实现代码块剥离、<thinking>/<reasoning>/<analysis> 标签清理与 JSON 主体提取；__004__/__005__/__006__ 在解析前统一接入，__004__ 新增清洗后重试，降低 Gemini 等模型思考文本导致的 JSON 解析失败率。
- 增加按模型能力分流：在 `core/llm.py` 新增 `extract_supports_json_response_format` / `report_supports_json_response_format` 判断；`__004__` / `__005__` / `__006__` 支持时启用 `response_format={"type":"json_object"}` 强约束，不支持时自动回退原有 JSON 解析修复链路，避免影响非 GPT 模型。
- 调整模型能力分流规则：移除 esponse_format 与 ase_url 的绑定限制，不再要求官方 OpenAI 地址；当前仅按模型名能力判断是否启用 esponse_format={"type":"json_object"}。
## 2026-03-03

- 新增逐题分析缓存表：`tb_interview_analysis_cache`，按 `(record_id, qa_index)` 维度持久化 `__005__` 节点输出，支持题目级断点续跑。
- `infra/db/db_helper.py` 新增逐题分析缓存接口：`get_analysis_cache` / `upsert_analysis_cache` / `clear_analysis_cache`。
- 改造 `__005__offer_sample_answer_node.py`：命中缓存题目直接跳过 LLM，未命中题目逐题分析并即时落库；节点结束前重建明细表写入，避免重复明细。
- Worker 成功清理链路新增逐题分析缓存清理：处理完成后统一执行 `clear_analysis_resume_cache(record_id)`。
- `scripts/init_database.sql` 同步新增 `tb_interview_analysis_cache` 建表语句。
- 修复 `__005__offer_sample_answer_node.py` 在数学公式字符串场景下的 JSON 解析失败：补充 `\eta -> eta` 清洗映射，并新增非法反斜杠转义兜底（将 `\e`、`\q` 等非 JSON 合法转义自动转为字面量反斜杠），避免 `OUTPUT_PARSING_FAILURE` 误触发保底结果。

## 2026-03-10

- 新增健康检查路由：在 `apps/api/app/main.py` 添加 `/health` 和 `/readiness` 端点，支持服务健康状态监控。
- 统一配置加载：删除 `core/db_config.py` 中重复的 `load_dotenv()` 调用，配置加载统一由 `core/config.py` 负责。
- 实现全局异常处理中间件：
  - 新增 `core/errors.py`：定义异常类型体系，区分临时错误（可重试）和永久错误（需人工介入）
  - 新增 `core/middleware.py`：实现 FastAPI 全局异常处理中间件和请求日志中间件
  - 新增 `core/worker_exception_handler.py`：实现 Worker 统一异常处理工具
  - 更新 `apps/api/app/main.py`：集成异常处理和日志中间件
  - 更新 `apps/worker/app/tasks.py`：使用统一异常处理，自动分类错误类型
  - 新增 `EXCEPTION_HANDLING.md`：异常处理使用指南
- 完善异常分类使用：
  - 更新 `infra/db/db_helper.py`：数据库操作抛出 `DatabaseError`
  - 更新 `services/interview_service.py`：业务逻辑抛出 `RecordNotFoundError`, `ValidationError`, `FileUploadError`
  - 更新 `apps/api/app/routes/interviews.py`：简化路由错误处理，依赖中间件自动处理异常
  - 更新 `pipelines/nodes/__002__voice_to_text_node.py`：ASR 节点抛出 `ASRError`
  - 新增 `EXCEPTION_CLASSIFICATION_PROGRESS.md`：异常分类实施进度追踪
