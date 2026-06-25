"""面试记录处理状态常量与工具函数。"""
from __future__ import annotations

from enum import IntEnum


class InterviewProcessingStatus(IntEnum):
    """面试记录处理状态枚举。

    IntEnum 值是 int 子类，可直接用于数据库读写和字典比较。
    """

    PENDING = 0      # 未处理
    PROCESSING = 1   # 处理中
    COMPLETED = 2    # 已完成
    FAILED = 3       # 处理失败


# 状态标签映射
_STATUS_LABELS: dict[int, str] = {
    InterviewProcessingStatus.PENDING: "未处理",
    InterviewProcessingStatus.PROCESSING: "处理中",
    InterviewProcessingStatus.COMPLETED: "已完成",
    InterviewProcessingStatus.FAILED: "处理失败",
}


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
