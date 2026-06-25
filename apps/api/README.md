# FastAPI 重构服务（隔离版）

此目录用于放置 **重构后的 FastAPI 服务**，不影响原项目。

## 结构

```
interview_voice_project_refactor/
├── apps/
│   └── api/
│       └── app/
│   ├── __init__.py
│   ├── deps.py
│   ├── main.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── interviews.py
│   └── routes/
│       ├── __init__.py
│       └── interviews.py
├── core/
│   ├── __init__.py
│   ├── app_config.py
│   ├── config.py
│   ├── db_config.py
│   ├── llm.py
│   ├── output_graph_utils.py
│   ├── voice_model.py
│   └── utils/
│       ├── __init__.py
│       ├── path_utils.py
│       └── time_utils.py
├── infra/
│   ├── __init__.py
│   └── db/
│       ├── __init__.py
│       ├── db_helper.py
│       └── model/
│           ├── __init__.py
│           ├── base.py
│           ├── tb_interview_recording_analysis.py
│           ├── tb_interview_recording_analysis_detail.py
│           └── tb_user.py
│       └── repo.py
└── services/
    ├── __init__.py
    └── interview_service.py
```

## 说明

- 路由与原始 `__003__fastapi/langgraph_fastapi.py` 等价
- 只做结构整理，不改变行为
- 共享层（`core/`、`infra/`、`services/`）位于 `interview_voice_project_refactor/` 根目录

## 启动方式

```bash
python -m app.main
```

或使用 uvicorn：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```


