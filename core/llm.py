from langchain_openai import ChatOpenAI

from core.config import get_config

conf = get_config()


def _build_llm(*, api_key: str | None, base_url: str | None, model: str | None) -> ChatOpenAI:
    if not model:
        raise ValueError(
            "LLM model is not configured. Please set MODEL_NAME, "
            "or task-specific EXTRACT_MODEL_NAME / REPORT_MODEL_NAME in .env"
        )
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def _resolve_llm_config(
    *,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
) -> tuple[str | None, str | None, str | None]:
    return (
        api_key or conf.model_api_key,
        base_url or conf.model_base_url,
        model or conf.model_name,
    )


_extract_llm: ChatOpenAI | None = None
_report_llm: ChatOpenAI | None = None
_default_llm: ChatOpenAI | None = None


def get_extract_llm() -> ChatOpenAI:
    """Model for transcript arrangement and QA extraction nodes."""
    global _extract_llm
    if _extract_llm is None:
        api_key, base_url, model = _resolve_llm_config(
            api_key=conf.extract_model_api_key,
            base_url=conf.extract_model_base_url,
            model=conf.extract_model_name,
        )
        _extract_llm = _build_llm(api_key=api_key, base_url=base_url, model=model)
    return _extract_llm


def get_report_llm() -> ChatOpenAI:
    """Model for per-question analysis and overall advice nodes."""
    global _report_llm
    if _report_llm is None:
        api_key, base_url, model = _resolve_llm_config(
            api_key=conf.report_model_api_key,
            base_url=conf.report_model_base_url,
            model=conf.report_model_name,
        )
        _report_llm = _build_llm(api_key=api_key, base_url=base_url, model=model)
    return _report_llm


def get_default_llm() -> ChatOpenAI:
    """Backward-compatible default model getter."""
    global _default_llm
    if _default_llm is None:
        # 默认优先 MODEL_*，若未配置则回退到 REPORT / EXTRACT 配置
        fallback_model = conf.model_name or conf.report_model_name or conf.extract_model_name
        fallback_api_key = conf.model_api_key or conf.report_model_api_key or conf.extract_model_api_key
        fallback_base_url = conf.model_base_url or conf.report_model_base_url or conf.extract_model_base_url
        _default_llm = _build_llm(
            api_key=fallback_api_key,
            base_url=fallback_base_url,
            model=fallback_model,
        )
    return _default_llm


class _LazyLLMProxy:
    """Lazy proxy to keep `my_llm` backward compatible without import-time initialization."""

    def __getattr__(self, item: str):
        return getattr(get_default_llm(), item)


my_llm = _LazyLLMProxy()
