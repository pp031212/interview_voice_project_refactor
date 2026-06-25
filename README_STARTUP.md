# Refactor 启动指南

本指南对应 `interview_voice_project_refactor/` 结构，不影响原项目。

## 目录结构（关键）

```
interview_voice_project_refactor/
├── apps/
│   ├── api/
│   │   └── app/
│   ├── worker/
│   │   ├── app/
│   │   └── scripts/
│   └── ui/
│       └── app/
├── core/
├── infra/
├── services/
├── pipelines/
├── domain/
└── data/
```

## 0. 环境变量

参考 `interview_voice_project_refactor/.env.example`，在项目根目录 `.env` 中配置：

```
API_BASE_URL=http://127.0.0.1:8001

MODEL_API_KEY=...
MODEL_BASE_URL=...
MODEL_NAME=...

# 可选：按任务路由模型（为空则回退到 MODEL_*）
# 文本整理/问答抽取（__003__/__004__）
EXTRACT_MODEL_API_KEY=...
EXTRACT_MODEL_BASE_URL=...
EXTRACT_MODEL_NAME=...

# 逐题分析/总评（__005__/__006__）
REPORT_MODEL_API_KEY=...
REPORT_MODEL_BASE_URL=...
REPORT_MODEL_NAME=...

VOICE_MODEL_PATH=...
VOICE_VAD_MODEL_PATH=...

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE_NAME=...
```

本仓库不提交本地语音模型权重。模型下载与路径配置见 `MODEL_SETUP.md`。

说明：
- 推荐配置 `MODEL_*` 作为默认模型。
- 若未配置 `MODEL_*`，也可仅配置 `EXTRACT_MODEL_*` 与/或 `REPORT_MODEL_*`；Worker 会在运行时自动回退，不会在导入阶段因 `MODEL_NAME=None` 崩溃。

### LLM 配置限制（重要）

- 禁止使用 GPT 系列模型（无论官方地址还是第三方网关）。
- 原因：当前场景下 GPT 系列更容易出现“反问 schema/结构化输出偏离”问题，影响面试分析稳定性。
- 请改用非 GPT 模型（如 Kimi 等），并填写其官方 API 地址。

## 1. 启动 MySQL

```
.\start_mysql.ps1
```
或手动启动 MySQL 服务。

## 2. 启动 FastAPI（refactor）

```
cd interview_voice_project_refactor\\\apps\api
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 3. 启动 Worker（refactor）

```
cd interview_voice_project_refactor\apps\worker
python -m app.main
```

## 4. 启动 UI（refactor）

```
cd interview_voice_project_refactor\apps\ui
streamlit run app/main.py
```

## 5. 运行数据库连接自检（可选）

```
cd interview_voice_project_refactor\apps\worker
python scripts\test_db_connection.py
```

## 7. 启动报错排查

若出现以下错误：

`ValidationError: ChatOpenAI ... model Input should be a valid string (input_value=None)`

请检查：
- 至少配置一组可用模型：`MODEL_*` 或 `EXTRACT_MODEL_*` 或 `REPORT_MODEL_*`。
- 对应 `*_MODEL_NAME` 不能为空字符串。
- 禁止配置 GPT 系列模型名称（如 `gpt-*`）。

## 6. 验证流程

1. 打开 UI 页面，上传录音
2. Worker 自动处理
3. UI 查看详情

FastAPI 文档：`http://127.0.0.1:8001/docs`


