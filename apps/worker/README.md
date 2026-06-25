# Worker 重构服务（隔离版）

此目录用于放置 **重构后的处理 Worker**，不影响原项目。

## 结构

```
interview_voice_project_refactor/
├── apps/
│   └── worker/
│       └── app/
│   ├── __init__.py
│   ├── main.py
│   └── tasks.py
├── core/
├── infra/
├── pipelines/
└── scripts/
    └── test_db_connection.py
```

## 启动方式

```bash
python -m app.main
```

## 配置

- `API_BASE_URL`：后端 API 基础地址（默认 `http://127.0.0.1:8001`）


