from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
import streamlit as st

from core.config import get_config
from core.task_status import InterviewProcessingStatus, get_processing_status_label


def _parse_datetime(value: Any) -> datetime | None:
    """Parse API datetime value for UI display."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _format_datetime(value: Any) -> str:
    """Format datetime-like value for display."""
    parsed = _parse_datetime(value)
    if parsed is None:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _parse_failure_tips(processing_tips: str | None) -> dict[str, str]:
    """Parse structured failure text from processing_tips."""
    result = {
        "reason": "",
        "error_type": "",
        "retry_count": "",
        "hint": "",
    }
    if not processing_tips:
        return result

    for line in str(processing_tips).splitlines():
        item = line.strip()
        if item.startswith("处理失败:"):
            result["reason"] = item.removeprefix("处理失败:").strip()
        elif item.startswith("错误类型:"):
            result["error_type"] = item.removeprefix("错误类型:").strip()
        elif item.startswith("重试次数:"):
            result["retry_count"] = item.removeprefix("重试次数:").strip()
        elif item.startswith("提示:"):
            result["hint"] = item.removeprefix("提示:").strip()

    if not result["reason"]:
        result["reason"] = str(processing_tips).strip()
    return result


def _build_failure_action_text(failure_info: dict[str, str]) -> str:
    """Build a user-facing action suggestion for failed records."""
    reason = failure_info.get("reason", "")
    error_type = failure_info.get("error_type", "")
    combined = f"{reason} {error_type}"

    if any(keyword in combined for keyword in ["文件不存在", "录音文件", "不支持的文件格式"]):
        return "录音文件可能不可用或格式不符合要求。如果文件路径已经丢失，通常需要重新上传。"
    if any(keyword in combined for keyword in ["超时", "timeout", "LLM", "ASR", "数据库", "连接"]):
        return "这类问题通常可以在服务恢复后直接继续处理，不需要重新上传录音。"
    if "临时错误" in error_type:
        return "这是可重试错误。确认模型、数据库或网络服务恢复后，可以直接继续处理。"
    if "永久错误" in error_type:
        return "这是需要人工确认的问题。先检查文件、配置或输入内容，再尝试继续处理。"
    return "可以先查看失败原因。确认问题已修复后，点击继续处理会保留断点并重新排队。"


def get_data_by_id(record_id: int | str) -> dict[str, Any] | None:
    """Fetch interview record details."""
    api_base_url = get_config().api_base_url
    resp = requests.get(
        f"{api_base_url}/interview_records/{record_id}",
        timeout=60,
    )
    if resp.ok:
        result_dict = resp.json()
        data_dict = result_dict.get("data", {})
        return data_dict if isinstance(data_dict, dict) else {}

    st.error(f"获取详情失败：{resp.status_code} {resp.text}")
    return None


def retry_record(record_id: int | str) -> bool:
    """Request backend to reset a failed record to pending."""
    api_base_url = get_config().api_base_url
    resp = requests.post(
        f"{api_base_url}/interview_records/{record_id}/retry",
        timeout=30,
    )
    if resp.ok:
        payload = resp.json()
        st.success(payload.get("message", "已提交继续处理"))
        return True

    st.error(f"继续处理失败：{resp.status_code} {resp.text}")
    return False


def _render_record_summary(data_dict: dict[str, Any]) -> int:
    """Render record status summary and return status value."""
    status = data_dict.get("processing_status", -1)
    try:
        status_value = int(status)
    except (TypeError, ValueError):
        status_value = -1

    st.subheader("处理状态")
    cols = st.columns(4)
    cols[0].metric("记录ID", data_dict.get("id", "-"))
    cols[1].metric("状态", get_processing_status_label(status_value))
    cols[2].metric("公司", data_dict.get("company_name", "-"))
    cols[3].metric("更新时间", _format_datetime(data_dict.get("update_time")))

    st.write(f"姓名：{data_dict.get('name', '-')}")
    st.write(f"学科：{data_dict.get('subject', '-')}")
    st.write(f"当前进度：{data_dict.get('processing_tips') or '等待处理'}")
    return status_value


def _render_failed_state(record_id: int | str, data_dict: dict[str, Any]) -> None:
    """Render failed state and retry action."""
    processing_tips = data_dict.get("processing_tips")
    failure_info = _parse_failure_tips(processing_tips)

    st.error("处理失败")
    st.write(f"失败原因：{failure_info['reason'] or '-'}")
    if failure_info["error_type"]:
        st.write(f"错误类型：{failure_info['error_type']}")
    if failure_info["retry_count"]:
        st.write(f"重试次数：{failure_info['retry_count']}")
    if failure_info["hint"]:
        st.write(f"系统提示：{failure_info['hint']}")

    st.info(_build_failure_action_text(failure_info))

    retry_col, refresh_col = st.columns([1, 1])
    with retry_col:
        if st.button("继续处理", type="primary"):
            if retry_record(record_id):
                st.rerun()
    with refresh_col:
        if st.button("刷新状态"):
            st.rerun()


def _render_incomplete_state(status_value: int) -> None:
    """Render pending/processing state."""
    if status_value == int(InterviewProcessingStatus.PENDING):
        st.info("记录已排队，Worker 会自动开始处理。")
    elif status_value == int(InterviewProcessingStatus.PROCESSING):
        st.info("记录正在处理中，可以稍后刷新查看进度。")
    else:
        st.warning("该记录尚未生成面试报告。")

    if st.button("刷新状态"):
        st.rerun()


def _render_markdown_report(data_dict: dict[str, Any]) -> None:
    """Render completed markdown report."""
    markdown_text = data_dict.get("markdown_text")
    if not markdown_text:
        st.warning("该记录状态已完成，但尚未获取到面试报告内容。")
        return

    interview_time = str(data_dict.get("interview_time", ""))[:10]
    name = data_dict.get("name", "未知")
    company_name = data_dict.get("company_name", "未知公司")

    st.download_button(
        "下载md文件",
        data=str(markdown_text),
        file_name=f"{interview_time}_{name}_{company_name}_面试评价.md",
        mime="text/markdown",
    )
    st.markdown(str(markdown_text))


def page_detail() -> None:
    """Render interview record detail and status page."""
    if st.button("← 返回主界面"):
        st.session_state.update({"page": "page_main"})
        st.rerun()

    st.title("面试处理详情")

    record_id = st.session_state.get("record_id", "")
    if not record_id:
        st.error("缺少记录 ID，请从主界面重新进入。")
        return

    data_dict = get_data_by_id(record_id)
    if not data_dict:
        st.error("未获取到面试记录详情，请稍后重试。")
        return

    status_value = _render_record_summary(data_dict)

    if status_value == int(InterviewProcessingStatus.FAILED):
        _render_failed_state(record_id, data_dict)
        return

    if status_value != int(InterviewProcessingStatus.COMPLETED):
        _render_incomplete_state(status_value)
        return

    _render_markdown_report(data_dict)
