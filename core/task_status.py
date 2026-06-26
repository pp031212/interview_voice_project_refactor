"""面试记录处理状态/阶段常量与工具函数。"""
from __future__ import annotations

from enum import Enum, IntEnum


class InterviewProcessingStatus(IntEnum):
    """面试记录处理状态枚举。

    IntEnum 值是 int 子类，可直接用于数据库读写和字典比较。
    """

    PENDING = 0      # 未处理
    PROCESSING = 1   # 处理中
    COMPLETED = 2    # 已完成
    FAILED = 3       # 处理失败


class InterviewProcessingStage(str, Enum):
    """面试记录处理阶段枚举。

    阶段表示当前卡在流水线的哪一步；状态表示任务整体状态。
    失败记录应优先保留失败前所在阶段，方便用户判断是否需要重新上传。
    """

    UPLOADED = "uploaded"
    SPLIT_AUDIO = "split_audio"
    ASR = "asr"
    ARRANGE_TEXT = "arrange_text"
    EXTRACT_QA = "extract_qa"
    ANALYZE_ANSWERS = "analyze_answers"
    GENERATE_ADVICE = "generate_advice"
    GENERATE_REPORT = "generate_report"
    COMPLETED = "completed"
    FAILED = "failed"


# 状态标签映射
_STATUS_LABELS: dict[int, str] = {
    InterviewProcessingStatus.PENDING: "未处理",
    InterviewProcessingStatus.PROCESSING: "处理中",
    InterviewProcessingStatus.COMPLETED: "已完成",
    InterviewProcessingStatus.FAILED: "处理失败",
}

PROCESSING_STAGE_FLOW: tuple[InterviewProcessingStage, ...] = (
    InterviewProcessingStage.UPLOADED,
    InterviewProcessingStage.SPLIT_AUDIO,
    InterviewProcessingStage.ASR,
    InterviewProcessingStage.ARRANGE_TEXT,
    InterviewProcessingStage.EXTRACT_QA,
    InterviewProcessingStage.ANALYZE_ANSWERS,
    InterviewProcessingStage.GENERATE_ADVICE,
    InterviewProcessingStage.GENERATE_REPORT,
    InterviewProcessingStage.COMPLETED,
)

_STAGE_LABELS: dict[InterviewProcessingStage, str] = {
    InterviewProcessingStage.UPLOADED: "已上传",
    InterviewProcessingStage.SPLIT_AUDIO: "音频切分",
    InterviewProcessingStage.ASR: "语音识别",
    InterviewProcessingStage.ARRANGE_TEXT: "文本整理",
    InterviewProcessingStage.EXTRACT_QA: "问答抽取",
    InterviewProcessingStage.ANALYZE_ANSWERS: "逐题分析",
    InterviewProcessingStage.GENERATE_ADVICE: "总评生成",
    InterviewProcessingStage.GENERATE_REPORT: "报告生成",
    InterviewProcessingStage.COMPLETED: "完成",
    InterviewProcessingStage.FAILED: "处理失败",
}

_STAGE_DESCRIPTIONS: dict[InterviewProcessingStage, str] = {
    InterviewProcessingStage.UPLOADED: "录音已保存，等待 Worker 认领",
    InterviewProcessingStage.SPLIT_AUDIO: "将长录音切成可识别的音频片段",
    InterviewProcessingStage.ASR: "把音频片段转换成文本",
    InterviewProcessingStage.ARRANGE_TEXT: "合并和清理转写文本",
    InterviewProcessingStage.EXTRACT_QA: "从文本中提取面试问答",
    InterviewProcessingStage.ANALYZE_ANSWERS: "生成每道题的分析与参考答案",
    InterviewProcessingStage.GENERATE_ADVICE: "生成整场面试总结与建议",
    InterviewProcessingStage.GENERATE_REPORT: "生成并保存 Markdown 报告",
    InterviewProcessingStage.COMPLETED: "报告已生成，可以查看和下载",
    InterviewProcessingStage.FAILED: "处理失败，请查看失败原因",
}

_TIP_STAGE_KEYWORDS: tuple[tuple[InterviewProcessingStage, tuple[str, ...]], ...] = (
    (
        InterviewProcessingStage.GENERATE_REPORT,
        ("开始生成markdown", "完成生成markdown", "Markdown生成完成", "Markdown", "报告"),
    ),
    (
        InterviewProcessingStage.GENERATE_ADVICE,
        ("开始提供面试建议", "完成提供面试建议", "总评", "面试建议"),
    ),
    (
        InterviewProcessingStage.ANALYZE_ANSWERS,
        (
            "开始提供参考答案",
            "完成提供参考答案",
            "命中逐题分析缓存",
            "个问题的回答",
            "参考答案",
            "逐题",
            "LLM",
        ),
    ),
    (
        InterviewProcessingStage.EXTRACT_QA,
        (
            "开始抽取面试题",
            "抽取节点",
            "文本已切分",
            "文本块",
            "开始融合抽取结果",
            "完成抽取面试题",
            "抽取",
        ),
    ),
    (
        InterviewProcessingStage.ARRANGE_TEXT,
        ("开始整理语音文本", "完成整理语音文本", "整理语音文本"),
    ),
    (
        InterviewProcessingStage.ASR,
        (
            "开始语音转文本",
            "完成语音转文本",
            "命中断点缓存",
            "正在处理第",
            "语音识别",
            "ASR",
        ),
    ),
    (
        InterviewProcessingStage.SPLIT_AUDIO,
        ("开始切分语音", "完成切分语音", "语音共切割", "切分"),
    ),
)


def get_processing_status_label(status: int | InterviewProcessingStatus) -> str:
    """返回处理状态的中文标签。

    Args:
        status: 状态值（int、IntEnum、或其他任意类型）。

    Returns:
        对应的中文标签；未知或非法状态返回 ``未知状态(<value>)``。
    """
    try:
        key = int(status)
    except (TypeError, ValueError):
        return f"未知状态({status})"
    return _STATUS_LABELS.get(key, f"未知状态({status})")


def normalize_processing_stage(
    stage: str | InterviewProcessingStage | None,
) -> InterviewProcessingStage | None:
    """把外部阶段值规范化为枚举，非法值返回 None。"""
    if stage is None:
        return None
    if isinstance(stage, InterviewProcessingStage):
        return stage
    try:
        return InterviewProcessingStage(str(stage))
    except ValueError:
        return None


def get_processing_stage_label(
    stage: str | InterviewProcessingStage | None,
) -> str:
    """返回处理阶段的中文标签。"""
    normalized = normalize_processing_stage(stage)
    if normalized is None:
        return f"未知阶段({stage})"
    return _STAGE_LABELS.get(normalized, f"未知阶段({stage})")


def get_processing_stage_description(
    stage: str | InterviewProcessingStage | None,
) -> str:
    """返回处理阶段的用户说明。"""
    normalized = normalize_processing_stage(stage)
    if normalized is None:
        return ""
    return _STAGE_DESCRIPTIONS.get(normalized, "")


def infer_processing_stage_from_tip(
    processing_tips: str | None,
) -> InterviewProcessingStage | None:
    """从历史 processing_tips 文本推断阶段。

    这是兼容旧记录的兜底逻辑；新记录应直接写入 ``processing_stage``。
    """
    text = str(processing_tips or "")
    if not text:
        return None

    for stage, keywords in _TIP_STAGE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return stage
    if "等待" in text or "正在处理中" in text:
        return InterviewProcessingStage.UPLOADED
    return None
