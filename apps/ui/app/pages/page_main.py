from datetime import datetime
from typing import Any

import requests
import streamlit as st

from core.config import get_config
from core.task_status import (
    InterviewProcessingStatus,
    get_processing_stage_label,
    get_processing_status_label,
    infer_processing_stage_from_tip,
)


STALE_PROGRESS_SECONDS = 10 * 60
STATUS_FILTER_OPTIONS = (
    "全部",
    "待处理",
    "处理中",
    "处理失败",
    "已完成",
    "疑似卡住",
)
SORT_OPTIONS = (
    "最近更新优先",
    "最近进度优先",
    "创建时间最新",
    "面试时间最新",
    "记录ID倒序",
)


def parse_datetime(value: Any) -> datetime | None:
    """Parse API datetime value."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def format_datetime(value: Any) -> str:
    """Format datetime-like value for display."""
    parsed = parse_datetime(value)
    if parsed is None:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def now_like(value: datetime) -> datetime:
    """Return current time with timezone compatibility."""
    return datetime.now(value.tzinfo) if value.tzinfo else datetime.now()


def seconds_since(value: Any) -> int | None:
    """Return seconds elapsed since datetime-like value."""
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    try:
        return max(int((now_like(parsed) - parsed).total_seconds()), 0)
    except TypeError:
        return None


def format_duration(seconds: int | None) -> str:
    """Format elapsed seconds for compact display."""
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds} 秒"

    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} 分 {sec} 秒" if sec else f"{minutes} 分"

    hours, minute = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} 小时 {minute} 分" if minute else f"{hours} 小时"

    days, hour = divmod(hours, 24)
    return f"{days} 天 {hour} 小时" if hour else f"{days} 天"


def compact_text(value: Any, limit: int = 80) -> str:
    """Return compact single-line text for list display."""
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def safe_status_value(value: Any) -> int:
    """Convert status to int with fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def latest_progress_time(record: dict[str, Any]) -> datetime | None:
    """Return latest progress timestamp, falling back to update_time."""
    return record.get("last_progress_at") or record.get("update_time")


def is_stale_processing(record: dict[str, Any]) -> bool:
    """Return True when a processing record has no recent progress."""
    if safe_status_value(record.get("processing_status")) != int(
        InterviewProcessingStatus.PROCESSING
    ):
        return False
    elapsed = seconds_since(latest_progress_time(record))
    return elapsed is not None and elapsed >= STALE_PROGRESS_SECONDS


def get_interview_data() -> list[dict[str, Any]]:
    """Fetch interview records from API."""
    interview_data = []
    try:
        api_base_url = get_config().api_base_url
        resp = requests.get(f"{api_base_url}/interview_records", timeout=10)
        payload = resp.json() if resp.ok else {"data": []}
        raw_list = payload.get("data", []) or []
        for item in raw_list:
            interview_data.append({
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "interview_time": parse_datetime(item.get("interview_time")),
                "company_name": item.get("company_name", ""),
                "subject": item.get("subject", ""),
                "processing_status": safe_status_value(
                    item.get("processing_status", 0)
                ),
                "processing_tips": item.get("processing_tips", ""),
                "processing_stage": item.get("processing_stage"),
                "processing_trace_id": item.get("processing_trace_id"),
                "error_code": item.get("error_code"),
                "error_message": item.get("error_message"),
                "create_time": parse_datetime(item.get("create_time")),
                "update_time": parse_datetime(item.get("update_time")),
                "processing_started_at": parse_datetime(
                    item.get("processing_started_at")
                ),
                "stage_started_at": parse_datetime(item.get("stage_started_at")),
                "last_progress_at": parse_datetime(item.get("last_progress_at")),
                "completed_at": parse_datetime(item.get("completed_at")),
                "failed_at": parse_datetime(item.get("failed_at")),
            })
    except Exception as e:
        st.error(f"获取面试记录失败：{e}")
    return interview_data


def goto_detail_page(record_id: int | str) -> None:
    """Navigate to detail page."""
    st.session_state.update({"record_id": record_id})
    st.session_state.update({"page": "page_detail"})
    st.rerun()


def record_matches_search(record: dict[str, Any], keyword: str) -> bool:
    """Return True when record matches search keyword."""
    if not keyword:
        return True
    haystack = " ".join(
        str(record.get(field, ""))
        for field in (
            "name",
            "company_name",
            "subject",
            "processing_tips",
            "processing_trace_id",
            "error_message",
            "id",
        )
    )
    return keyword.lower() in haystack.lower()


def record_matches_status_filter(record: dict[str, Any], status_filter: str) -> bool:
    """Return True when record matches selected status filter."""
    if status_filter == "全部":
        return True
    if status_filter == "疑似卡住":
        return is_stale_processing(record)

    status_value = safe_status_value(record.get("processing_status"))
    mapping = {
        "待处理": int(InterviewProcessingStatus.PENDING),
        "处理中": int(InterviewProcessingStatus.PROCESSING),
        "处理失败": int(InterviewProcessingStatus.FAILED),
        "已完成": int(InterviewProcessingStatus.COMPLETED),
    }
    return status_value == mapping.get(status_filter)


def filter_records(
    records: list[dict[str, Any]],
    keyword: str,
    status_filter: str,
) -> list[dict[str, Any]]:
    """Filter records by search keyword and status."""
    return [
        record
        for record in records
        if record_matches_search(record, keyword)
        and record_matches_status_filter(record, status_filter)
    ]


def sort_records(
    records: list[dict[str, Any]],
    sort_option: str,
) -> list[dict[str, Any]]:
    """Sort records by selected ordering."""
    key_mapping = {
        "最近更新优先": "update_time",
        "最近进度优先": "last_progress_at",
        "创建时间最新": "create_time",
        "面试时间最新": "interview_time",
        "记录ID倒序": "id",
    }
    key = key_mapping.get(sort_option, "update_time")

    def sort_key(record: dict[str, Any]) -> float:
        if key == "id":
            try:
                return float(record.get("id") or 0)
            except (TypeError, ValueError):
                return 0

        value = record.get(key)
        if key == "last_progress_at" and value is None:
            value = record.get("update_time")
        parsed = parse_datetime(value)
        if parsed is None:
            return 0
        return parsed.timestamp()

    return sorted(records, key=sort_key, reverse=True)


def render_summary(records: list[dict[str, Any]]) -> None:
    """Render list summary metrics."""
    total = len(records)
    pending = sum(
        safe_status_value(record.get("processing_status"))
        == int(InterviewProcessingStatus.PENDING)
        for record in records
    )
    processing = sum(
        safe_status_value(record.get("processing_status"))
        == int(InterviewProcessingStatus.PROCESSING)
        for record in records
    )
    failed = sum(
        safe_status_value(record.get("processing_status"))
        == int(InterviewProcessingStatus.FAILED)
        for record in records
    )
    stale = sum(is_stale_processing(record) for record in records)

    cols = st.columns(5)
    cols[0].metric("全部记录", total)
    cols[1].metric("待处理", pending)
    cols[2].metric("处理中", processing)
    cols[3].metric("处理失败", failed)
    cols[4].metric("疑似卡住", stale)


def build_status_line(record: dict[str, Any]) -> str:
    """Build compact status text for list row."""
    status = get_processing_status_label(record.get("processing_status", -1))
    stage = record.get("processing_stage") or infer_processing_stage_from_tip(
        record.get("processing_tips")
    )
    stage_label = get_processing_stage_label(stage) if stage else "阶段未知"
    if is_stale_processing(record):
        return f"{status} / {stage_label} / 疑似卡住"
    return f"{status} / {stage_label}"


def build_progress_line(record: dict[str, Any]) -> str:
    """Build compact progress line for list row."""
    trace_text = ""
    if record.get("processing_trace_id"):
        trace_text = f" | Trace: {record.get('processing_trace_id')}"

    if record.get("error_message"):
        return compact_text(f"{record.get('error_message')}{trace_text}", limit=110)
    if record.get("processing_tips"):
        return compact_text(f"{record.get('processing_tips')}{trace_text}", limit=110)
    return compact_text(f"等待处理{trace_text}", limit=110)


def render_filters() -> tuple[str, str, str]:
    """Render search, status filter, and sorting controls."""
    search_col, status_col, sort_col = st.columns([3, 2, 2])
    with search_col:
        keyword = st.text_input("搜索", placeholder="姓名、公司、学科、记录ID")
    with status_col:
        status_filter = st.selectbox("状态筛选", STATUS_FILTER_OPTIONS)
    with sort_col:
        sort_option = st.selectbox("排序", SORT_OPTIONS)
    return keyword.strip(), status_filter, sort_option


def render_record_rows(records: list[dict[str, Any]]) -> None:
    """Render record rows with action buttons."""
    if not records:
        st.info("没有符合条件的面试记录。")
        return

    header_cols = st.columns([1.2, 1.6, 1.7, 2.4, 1.5, 1.2])
    header_cols[0].write("姓名")
    header_cols[1].write("公司 / 学科")
    header_cols[2].write("状态 / 阶段")
    header_cols[3].write("当前进度")
    header_cols[4].write("最近进度")
    header_cols[5].write("操作")

    for index, record in enumerate(records):
        cols = st.columns([1.2, 1.6, 1.7, 2.4, 1.5, 1.2])
        cols[0].write(record.get("name") or "-")
        cols[1].write(
            f"{record.get('company_name') or '-'}\n\n"
            f"{record.get('subject') or '-'}"
        )
        status_line = build_status_line(record)
        if is_stale_processing(record):
            cols[2].warning(status_line)
        elif safe_status_value(record.get("processing_status")) == int(
            InterviewProcessingStatus.FAILED
        ):
            cols[2].error(status_line)
        else:
            cols[2].write(status_line)

        cols[3].write(build_progress_line(record))
        latest_progress = latest_progress_time(record)
        elapsed = seconds_since(latest_progress)
        cols[4].write(format_datetime(latest_progress))
        cols[4].caption(f"距今 {_format_elapsed_for_caption(elapsed)}")

        button_label = (
            "查看报告"
            if safe_status_value(record.get("processing_status"))
            == int(InterviewProcessingStatus.COMPLETED)
            else "查看状态"
        )
        if cols[5].button(button_label, key=f"record_{record.get('id')}_{index}"):
            goto_detail_page(record["id"])


def _format_elapsed_for_caption(seconds: int | None) -> str:
    """Format elapsed text used by list captions."""
    if seconds is None:
        return "-"
    return format_duration(seconds)


def page_main() -> None:
    """Render interview record list page."""
    st.title("面试录音分析")

    top_left, top_right = st.columns([8, 2])
    with top_right:
        if st.button("处理语音"):
            st.session_state.update({"page": "page_add"})
            st.rerun()

    interview_data = get_interview_data()
    render_summary(interview_data)

    keyword, status_filter, sort_option = render_filters()
    filtered_records = filter_records(interview_data, keyword, status_filter)
    sorted_records = sort_records(filtered_records, sort_option)

    st.caption(f"当前显示 {len(sorted_records)} / {len(interview_data)} 条记录")
    render_record_rows(sorted_records)
