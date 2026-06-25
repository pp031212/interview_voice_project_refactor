# 启动流程与 PyCharm 运行配置

本文档适用于 `interview_voice_project_refactor`。

## 一、启动流程（建议顺序）

1. 启动 MySQL
2. 启动 FastAPI
3. 启动 Worker
4. 启动 UI

参考 `README_STARTUP.md` 的命令也可直接运行。

---

## 二、PyCharm 运行配置

### 1) FastAPI (Uvicorn)

**运行配置**：新增 `FastAPI` 或 `Python` 配置

- **Interpreter**: 选择你的环境（如 `interview_voice_project_refactor_py3_11`）
- **Module name**: `uvicorn`
- **Parameters**: `app.main:app --host 0.0.0.0 --port 8001`
- **Working directory**: `interview_voice_project_refactor\apps\api`

> 说明：不要把 `uvicorn` 当作脚本路径传给 Python。

---

### 2) Worker

- **Interpreter**: 选择你的环境
- **Module name**: `app.main`
- **Working directory**: `interview_voice_project_refactor\apps\worker`

---

### 3) UI (Streamlit)

- **Interpreter**: 选择你的环境
- **Module name**: `streamlit`
- **Parameters**: `run app/main.py`
- **Working directory**: `interview_voice_project_refactor\apps\ui`

---

## 三、常见问题

### 0. GPT 模型配置要求（重要）

- 禁止使用 GPT 系列模型（包括官方地址和第三方网关）。
- 原因：当前链路中 GPT 系列容易出现“反问 schema”或结构化输出偏离，影响稳定性。
- 请使用非 GPT 模型，并填写模型官方 API 地址。
- `MODEL_*` 作为默认模型是推荐项，但不是强制项；若只配置了 `EXTRACT_MODEL_*` 或 `REPORT_MODEL_*`，系统会自动按任务路由并回退。

### 1. `python.exe` 被当成脚本执行

错误例子：
```
python.exe python.exe -m app.main
```
正确方式：
```
python.exe -m app.main
```

### 2. 找不到 `uvicorn`

请确认安装了依赖：
```
pip install -r requirements.txt
```

### 3. Worker 启动时报 `ChatOpenAI model=None`

典型错误：
`ValidationError: ChatOpenAI ... model Input should be a valid string`

排查顺序：
1. 检查 `.env` 至少有一组完整模型配置：`MODEL_*` / `EXTRACT_MODEL_*` / `REPORT_MODEL_*`。
2. 对应的 `*_MODEL_NAME` 不能为 `None` 或空字符串。
3. 确认未配置 GPT 系列模型名称（如 `gpt-*`）。

---
