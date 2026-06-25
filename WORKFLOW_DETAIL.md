# 项目详细工作流程（本地处理与 LLM 处理）

本文档描述 `interview_voice_project_refactor` 当前端到端处理流程，重点说明本地处理链路与 LLM 处理链路。

## 1. 总体执行入口

1. Worker 轮询数据库，拉取 `processing_status=0` 的记录。
2. 将记录状态置为 `1`（处理中）。
3. 调用 `pipelines/langgraph_agent.py` 执行状态图。
4. 成功后将记录状态置为 `2`，并清除该记录 checkpoint。
5. 失败则置为 `3`，保留 checkpoint 供重试续传。

## 2. 本地处理链路

本地处理主要覆盖音频切分、语音识别、状态更新、文件落盘、数据库写入等不依赖大模型生成的步骤。

### 2.1 音频切分（`__001__split_voice_node`）

- 输入：`input_audio_path`
- 处理：
- 使用 `pydub` 按 60 秒切分，重叠 5 秒（用于降低边界信息丢失）
- 输出目录：`data/voice/<base_name>/`
- 输出：`split_audio_path_list`

### 2.2 语音转文本（`__002__voice_to_text_node`）

- 输入：`split_audio_path_list`
- 处理：
- 逐个分片调用本地 ASR 模型（SenseVoice/FunASR）
- 参数包含 `merge_vad=True`、`merge_length_s=15` 等
- 对识别文本做 `rich_transcription_postprocess`
- 输出：`voice_text_list`
- 断点续传：
- 每个分片识别成功后会优先持久化到数据库表 `tb_asr_segment_cache`（DB 主存）
- 同时写入 `data/checkpoints/asr_resume/record_<id>.json` 作为兜底副本
- 重跑时优先复用数据库中的已完成分片文本；若 DB 缓存不可用则回退文件缓存
- 注意：`voice_to_text` 节点完成时不会立即清理缓存；仅在整条面试流程成功后由 Worker 统一清理，避免后续节点失败时中间文本丢失

### 2.3 文本落盘与数据库写入（`__007__generate_markdown_node`）

- 输出文件：`markdown_reports/*.md`（位于 refactor 根目录下）
- 同步写入主表字段：`markdown_text`
- 策略：先写文件，再写数据库，数据库失败时保留文件作为恢复依据

### 2.4 数据库状态管理（Worker）

- `0`：未处理
- `1`：处理中
- `2`：处理完成
- `3`：处理失败（保留错误信息与 checkpoint）

## 3. LLM 处理链路

LLM 客户端统一在 `core/llm.py` 懒加载初始化，配置来自 `.env`，按任务路由：

- 默认模型：`MODEL_API_KEY` / `MODEL_BASE_URL` / `MODEL_NAME`
- 抽取链路模型（`__003__` / `__004__`）：`EXTRACT_MODEL_API_KEY` / `EXTRACT_MODEL_BASE_URL` / `EXTRACT_MODEL_NAME`
- 报告链路模型（`__005__` / `__006__`）：`REPORT_MODEL_API_KEY` / `REPORT_MODEL_BASE_URL` / `REPORT_MODEL_NAME`

回退策略：
- 优先使用任务专属模型（extract/report）
- 若任务专属未配置，则回退到默认 `MODEL_*`
- 默认模型对象为懒加载代理：即使 `MODEL_NAME` 未配置，也不会在 import 阶段直接抛错

说明：当前评分与分析依赖 LLM 输出，没有本地规则引擎聚合分数。

### 3.1 全文整理（`__003__voice_text_arrange_node`）

- 输入：`voice_text_list`
- 处理：
- 将所有分片文本拼接为整段 `raw_text`
- 调用 LLM 做“去重复片段 + 常见错字修正”
- 保持原始口语风格，不做风格润色
- 输出：`voice_arrange_text`
- 数据落库：主表 `interview_text`

### 3.2 问答抽取（`__004__extract_interview_topic_node`）

- 输入：`voice_arrange_text`
- 处理：
- 将全文按字符切块（默认 2000，重叠 200）
- 每块调用 LLM 抽取问答 JSON
- 使用 `JsonOutputParser + Pydantic` 做结构化解析
- 多块结果融合并去重（按问题相似度）
- 输出：`interview_topic_list`

### 3.3 逐题分析与参考答案（`__005__offer_sample_answer_node`）

- 输入：`interview_topic_list`
- 处理：
- 对每个问答调用 LLM 生成：
- `analysis.exam_point`
- `analysis.answer_approach`
- `analysis.answer_evaluation`
- `analysis.score`
- `sample_answer`
- 解析异常处理：
- 优先做 JSON 修复（提取主体、转义修复等）
- 仍失败时落兜底结构，避免流水线中断
- 输出：增强后的 `interview_topic_list`
- 数据落库：写入面试明细表

### 3.4 整场面试总评（`__006__offer_interview_advice_node`）

- 输入：`voice_arrange_text`
- 处理：
- 调用 LLM 生成结构化总评 JSON：
- `overall_comment`
- `overall_score`
- `strengths`
- `weaknesses`
- `suggestions`
- 输出：`interview_advice`
- 数据落库：更新主表整体点评与总分等字段

## 4. Checkpoint 与断点续传

### 4.1 存储位置

- `data/checkpoints/langgraph_checkpoints.db`
- 每条记录的 thread key：`record_<record_id>`

### 4.2 续传行为

- 失败后保留 checkpoint
- 重置记录为 `status=0` 后再次执行，会尝试从已保存状态继续
- 成功后清除该记录 checkpoint

### 4.3 当前粒度限制

- LangGraph checkpoint 仍主要是“节点级”
- `voice_to_text` 已补充分片级断点（DB 主存 + 文件兜底），可避免分片转写整体重跑

## 5. 当前已识别的优化重点

1. 评分一致性：引入本地 Rubric 与规则聚合，降低不同模型评分漂移。
2. ASR 术语准确率：引入术语词典/热词与二次纠错流程。
3. 断点治理：为分片级断点增加 TTL 清理策略与可视化状态查询。
   - 已完成脚本层能力：`scripts/manage_asr_resume_cache.py`（status / cleanup 子命令）
   - DB 层：`DatabaseHelper.get_asr_segment_cache_status()` 和 `clear_expired_asr_segment_cache()`
   - 配置：`ASR_RESUME_CACHE_TTL_DAYS`（默认 7 天）
   - UI 可视化待后续推进

## 6. 2026-03-03 增量更新（断点粒度）

- 新增逐题分析缓存表：`tb_interview_analysis_cache`。
- 缓存键：`(record_id, qa_index)`，缓存内容为 `__005__offer_sample_answer_node` 的单题完整输出（含 `analysis` 与 `sample_answer`）。
- 执行策略：
  - 先读缓存，命中题目直接跳过 LLM；
  - 未命中题目调用 LLM，成功后立即落库；
  - 失败重试时，仅补跑未完成题目。
- 明细落库幂等：`__005__` 在写 `tb_interview_recording_analysis_detail` 前会先按 `record_id` 清空历史明细，再重建写入，避免重复明细。
- 成功清理：Worker 在整条流程成功后，会清理 `tb_interview_analysis_cache` 中该记录缓存。
- 解析兜底补充（__005__）：在 JSON 主体提取和常见 LaTeX 片段清洗后，额外对非法反斜杠转义做统一修复（如 `\eta`/`\e` 场景），再进入结构化解析，降低因字符串转义不合法导致的整题降级概率。
