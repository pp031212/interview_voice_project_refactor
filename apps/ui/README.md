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


