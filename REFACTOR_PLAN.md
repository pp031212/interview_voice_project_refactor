# 重构步骤与结构图

本文档描述将当前“面试录音分析系统”重构为更工程化结构的步骤与目标结构图。该方案遵循“渐进式迁移”，即在不影响现有功能的前提下新增新结构，并逐步搬迁。

## 一、重构目标

1. 入口清晰：API / Worker / UI 三个应用分离。
2. 业务逻辑集中：核心流程收敛到 `services/` + `pipelines/`。
3. 依赖与基础设施隔离：数据库、LLM、ASR、文件存储集中到 `infra/`。
4. 更易测试：领域逻辑与外部依赖解耦。
5. 可扩展：便于引入任务队列、并行处理、更多模型。

## 二、重构后的项目结构图

```
interview_voice_project/
├── apps/
│   ├── api/                      # FastAPI 服务
│   │   ├── main.py
│   │   ├── routes/
│   │   └── deps.py
│   ├── worker/                   # 任务执行（LangGraph/队列）
│   │   ├── main.py
│   │   └── tasks.py
│   └── ui/                       # Streamlit 前端
│       └── main.py
├── core/                         # 核心配置与基础设施
│   ├── config.py                 # 环境配置
│   ├── logging.py
│   └── errors.py
├── domain/                       # 领域模型与业务规则
│   ├── models.py                 # 领域对象（InterviewRecord）
│   ├── pipeline_state.py         # 流程状态定义
│   └── steps.py                  # 步骤常量与规则
├── services/                     # 业务服务层
│   ├── interview_service.py      # 入口业务逻辑
│   └── pipeline_service.py       # 调度/恢复逻辑
├── pipelines/                    # LangGraph 流程
│   ├── graph.py
│   └── nodes/
│       ├── split_audio.py
│       ├── asr.py
│       ├── arrange_text.py
│       ├── extract_qa.py
│       ├── offer_sample.py
│       ├── offer_advice.py
│       └── generate_md.py
├── infra/                        # 基础设施实现
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py             # SQLAlchemy
│   │   └── repo.py               # Repository
│   ├── llm/
│   │   └── client.py
│   ├── asr/
│   │   └── client.py
│   └── storage/
│       └── file_store.py
├── scripts/                      # 运维脚本（初始化、迁移）
│   ├── setup_database.py
│   └── maintenance.py
├── data/                         # 本地数据（uploads/checkpoints/reports）
│   ├── uploads/
│   ├── voice/
│   ├── checkpoints/
│   └── reports/
├── tests/
│   ├── unit/
│   └── integration/
├── .env
└── requirements.txt
```

## 三、渐进式重构步骤（建议顺序）

### 步骤 1：建立新结构骨架（不迁移业务）
1. 新建 `apps/ core/ domain/ services/ pipelines/ infra/ scripts/ data/ tests/` 目录。
2. 将原有目录保持不动，确保现有功能可运行。

### 步骤 2：抽离配置与通用工具
1. 将 `.env` 的读取统一封装进 `core/config.py`。
2. 将现有 `common/` 中的配置、时间、路径工具迁移或包装到 `core/`。

### 步骤 3：数据库访问层标准化
1. 在 `infra/db/` 下建立 SQLAlchemy session 与 repository。
2. 将 `__002__db_helper_parse/` 的能力逐步迁移到 `infra/db/repo.py`。
3. 保留旧接口一段时间，通过适配层过渡。

### 步骤 4：LangGraph 流程迁移
1. 将 `__001__langgraph_more_node/` 下的节点移动到 `pipelines/nodes/`。
2. 重写 `pipelines/graph.py` 统一图构建。
3. 将原 `langgraph_agent.py` 简化为对 `pipelines/graph.py` 的调用。

### 步骤 5：服务层抽象
1. 建立 `services/pipeline_service.py`，封装“从数据库拉取任务 → 执行 → 更新状态”。
2. 建立 `services/interview_service.py`，封装“创建记录、校验、触发处理”。

### 步骤 6：API 和 Worker 解耦
1. `apps/api/` 只提供 API，不直接跑任务。
2. `apps/worker/` 独立运行任务循环（或后续切换队列）。

### 步骤 7：UI 迁移
1. `apps/ui/main.py` 作为 Streamlit 入口。
2. 页面逻辑拆分到 `apps/ui/pages/`（可选）。

### 步骤 8：数据目录统一
1. 将 `uploaded_files/`、`voice/`、`checkpoints/`、`markdown_reports/` 统一迁移到 `data/`。
2. `core/config.py` 中集中管理路径。

### 步骤 9：测试补齐
1. 在 `tests/` 中补充流程单元测试。
2. 增加数据库、LLM、ASR 的 mock 测试。

## 四、迁移原则

- 保证每一步可运行、可回退。
- 不一次性搬迁所有文件，优先抽离基础设施层。
- 迁移完成后再删除旧目录（如 `__001__*`、`__002__*` 等）。

## 五、最小可行里程碑（MVP）

1. `core/config.py` + `infra/db/` 就位。
2. `pipelines/graph.py` 可正常执行流程。
3. `apps/worker/main.py` 替代 `run_langgraph.py`。
4. API 和 UI 仍可正常使用。

---

