# Interview Voice Project Refactor

面试录音分析项目的重构版本。项目将上传录音、语音识别、问答抽取、逐题分析、总评生成和报告查看拆成独立模块，便于本地部署、断点续跑和后续维护。

## 功能概览

- 上传面试录音并创建面试记录
- 使用本地 FunASR 模型完成语音识别
- 通过 LLM 整理面试文本、抽取问答、生成逐题分析和总评
- 生成 Markdown 格式面试报告
- 支持 Worker 断点续跑：
  - ASR 分片级缓存
  - Q&A 抽取缓存
  - 逐题分析缓存
  - LangGraph checkpoint
- 支持 Rubric v1 旁路评分：
  - 保留现有模型评分
  - 额外生成本地规则聚合分、维度分、证据和缺失点
  - 基于逐题 Rubric 聚合整体旁路评分
- 支持任务状态管理：
  - 未处理、处理中、已完成、处理失败
  - 标准化处理阶段：已上传、音频切分、语音识别、文本整理、问答抽取、逐题分析、总评生成、报告生成、完成
  - 结构化失败信息：错误代码、错误类型、失败原因、重试次数、失败时间
  - 处理耗时统计：开始处理、当前阶段开始、最近进度更新、完成时间
  - Worker 任务追踪 ID：页面和脚本可用于定位对应日志
  - Worker 最大重试次数
  - 失败任务重试退避
  - 永久错误不自动重试
- 首页支持记录搜索、状态筛选、疑似卡住筛选和多维度排序
- 详情页支持 ASR 断点缓存诊断，辅助判断是否需要重新上传

## 项目结构

```text
interview_voice_project_refactor/
├── apps/
│   ├── api/        # FastAPI 服务
│   ├── worker/     # 后台处理 Worker
│   └── ui/         # Streamlit 前端
├── core/           # 配置、LLM、异常、路径、状态等共享能力
├── infra/          # 数据库模型与持久化
├── services/       # 业务服务
├── pipelines/      # LangGraph 处理流水线
├── scripts/        # 数据库、检查点、状态检查等脚本
├── data/           # 本地运行数据，不提交
└── markdown_reports/ # 生成报告，不提交
```

## 环境要求

- Python 3.11+
- MySQL
- FFmpeg
- 本地语音模型：
  - `iic/SenseVoiceSmall`
  - `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`
- 可用的非 GPT LLM API

依赖安装细节见 [相关依赖的安装指南.md](./相关依赖的安装指南.md)。

## 快速开始

1. 安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

2. 准备环境变量：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，至少配置：

```env
API_BASE_URL=http://127.0.0.1:8001

MODEL_API_KEY=
MODEL_BASE_URL=
MODEL_NAME=

VOICE_MODEL_PATH=data/models/SenseVoiceSmall
VOICE_VAD_MODEL_PATH=data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE_NAME=
```

3. 下载本地语音模型：

模型文件不提交到 GitHub。下载方式和目录检查见 [MODEL_SETUP.md](./MODEL_SETUP.md)。

4. 启动 FastAPI：

```powershell
cd apps\api
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

5. 启动 Worker：

```powershell
cd apps\worker
python -m app.main
```

6. 启动 UI：

```powershell
cd apps\ui
streamlit run app/main.py
```

FastAPI 文档地址：

```text
http://127.0.0.1:8001/docs
```

更完整的启动说明见 [README_STARTUP.md](./README_STARTUP.md) 和 [启动流程与PyCharm配置.md](./启动流程与PyCharm配置.md)。

## 重要配置

### LLM

项目支持默认模型和按任务路由模型：

- `MODEL_*`：默认模型配置
- `EXTRACT_MODEL_*`：文本整理、问答抽取
- `REPORT_MODEL_*`：逐题分析、总评生成

当前项目约定：不要使用 GPT 系列模型。请使用非 GPT 模型，并填写对应服务商的 API 地址。

### Worker 重试

```env
WORKER_MAX_RETRIES=3
WORKER_RETRY_BACKOFF_SECONDS=30
```

- `WORKER_MAX_RETRIES`：失败任务最大自动重试次数
- `WORKER_RETRY_BACKOFF_SECONDS`：失败后再次认领前的冷却秒数
- 永久错误会标记为失败，但不会自动重试
- 人工重置脚本可把失败任务重置为未处理

## 本地数据与模型

以下内容不会提交到 GitHub：

- `.env`
- `data/`
- `markdown_reports/`
- 本地模型权重
- 上传录音
- 切分音频
- checkpoint
- 生成报告

这是预期行为。云端仓库只保存代码、配置模板和必要文档。

## 常用脚本

检查数据库状态：

```powershell
python scripts\check_database_status.py
```

重置失败或处理中的记录：

```powershell
python scripts\reset_failed_records.py
```

管理 LangGraph checkpoint：

```powershell
python scripts\manage_checkpoints.py
```

评估 Rubric 校准样本：

```powershell
python scripts\evaluate_rubric_calibration.py
```

默认读取 `data/rubric_calibration_samples.example.json`。真实人工标注样本建议另存为本地 JSON 文件，不提交隐私数据，再通过路径传入：

```powershell
python scripts\evaluate_rubric_calibration.py data\my_rubric_samples.local.json
```

## 文档入口

- [README_STARTUP.md](./README_STARTUP.md)：启动步骤
- [MODEL_SETUP.md](./MODEL_SETUP.md)：本地语音模型下载与配置
- [WORKFLOW_DETAIL.md](./WORKFLOW_DETAIL.md)：处理链路与断点机制
- [NEXT_OPTIMIZATIONS.md](./NEXT_OPTIMIZATIONS.md)：后续优化清单
- [HANDOFF.md](./HANDOFF.md)：交接速览
- [EXCEPTION_HANDLING.md](./EXCEPTION_HANDLING.md)：异常处理说明

## 当前状态

项目已完成基础重构和主要稳定性改造：

- FastAPI / Worker / UI 拆分
- 共享层收敛到 `core/`、`infra/`、`services/`、`pipelines/`
- 健康检查路由
- 统一异常处理
- DB 层异常标准化
- 任务状态枚举与状态流转方法
- 标准化处理阶段字段与详情页进度展示
- 结构化失败字段与详情页失败原因展示
- 处理耗时字段与疑似卡住任务提示
- Worker 任务追踪 ID 持久化与页面/脚本展示
- 详情页 ASR 断点缓存诊断
- Rubric v1 逐题旁路评分
- Rubric v1 整体旁路评分
- Rubric 校准样本格式与偏差评估脚本
- 首页记录检索、异常任务筛选和列表状态摘要
- Worker 失败重试上限与退避
- 多级断点续跑缓存

后续优化以 [NEXT_OPTIMIZATIONS.md](./NEXT_OPTIMIZATIONS.md) 为准。
