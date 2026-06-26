# Streamlit UI 重构服务（隔离版）

此目录用于放置 **重构后的 Streamlit UI**，不影响原项目。

## 结构

```
interview_voice_project_refactor/
├── apps/
│   └── ui/
│       └── app/
│   ├── __init__.py
│   ├── main.py
│   └── pages/
│       ├── __init__.py
│       ├── page_add.py
│       ├── page_detail.py
│       ├── page_main.py
│       └── page_test.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── utils/
│       ├── __init__.py
│       └── path_utils.py
```

## 启动方式

```bash
streamlit run app/main.py
```

## 配置

- `API_BASE_URL`：后端 API 基础地址（默认 `http://127.0.0.1:8001`）

## 主要体验

- 上传成功后直接进入记录详情页，可查看处理状态。
- 上传页会先校验必填项、文件格式、文件大小和后端服务状态。
- 上传失败时会展示错误代码、错误类型、trace_id 和可操作建议。
- 上传页保留最近提交任务入口，便于返回刚提交的记录详情。
- 未完成记录可在详情页查看阶段进度条，并默认自动刷新状态。
- 失败记录会展示失败原因、错误类型、重试次数和处理建议。
- 失败记录可点击“继续处理”，不需要重新上传录音。


