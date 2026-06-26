from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import requests
import streamlit as st

from core.config import get_config


ALLOWED_AUDIO_EXTENSIONS: set[str] = {".aac", ".flac", ".m4a", ".mp3", ".wav"}
MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024
API_CHECK_TIMEOUT_SECONDS = 5
UPLOAD_TIMEOUT_SECONDS = 60


def _format_file_size(size_bytes: int) -> str:
    """Format bytes as a compact user-facing size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _get_uploaded_file_size(file: Any) -> int:
    """Return uploaded file size without consuming its content."""
    if file is None:
        return 0
    size = getattr(file, "size", None)
    if isinstance(size, int):
        return size
    try:
        return len(file.getbuffer())
    except Exception:
        return 0


def _get_uploaded_file_extension(file_name: str | None) -> str:
    """Return lowercase file extension."""
    if not file_name:
        return ""
    return Path(file_name).suffix.lower()


def _validate_upload_inputs(
    *,
    name: str,
    company: str,
    subject: str,
    interview_date_str: str,
    file: Any,
) -> list[str]:
    """Validate upload form inputs before submitting to API."""
    errors: list[str] = []

    if not name.strip():
        errors.append("请填写姓名。")
    if not company.strip():
        errors.append("请填写公司名称。")
    if not subject.strip():
        errors.append("请选择学科。")
    if not interview_date_str:
        errors.append("请选择面试日期。")
    if file is None:
        errors.append("请上传面试录音文件。")
        return errors

    extension = _get_uploaded_file_extension(getattr(file, "name", ""))
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        errors.append(f"不支持的文件格式：{extension or '未知'}。支持格式：{allowed}。")

    file_size = _get_uploaded_file_size(file)
    if file_size <= 0:
        errors.append("无法读取文件大小，请重新选择录音文件。")
    elif file_size > MAX_UPLOAD_SIZE_BYTES:
        errors.append(
            "文件过大："
            f"{_format_file_size(file_size)}，最大支持 "
            f"{_format_file_size(MAX_UPLOAD_SIZE_BYTES)}。"
        )

    return errors


def _check_api_ready(api_base_url: str) -> tuple[bool, str]:
    """Check whether API service is reachable before upload."""
    try:
        response = requests.get(
            f"{api_base_url}/readiness",
            timeout=API_CHECK_TIMEOUT_SECONDS,
        )
        if response.ok:
            return True, "后端服务可用。"
        return False, f"后端服务异常：HTTP {response.status_code}"
    except requests.RequestException as exc:
        return False, f"无法连接后端服务：{exc}"


def _parse_error_response(response: requests.Response) -> dict[str, str]:
    """Parse API error response into user-facing fields."""
    trace_id = response.headers.get("X-Trace-ID", "")
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if isinstance(payload, dict):
        trace_id = str(payload.get("trace_id") or trace_id or "")
        error_code = str(payload.get("error_code") or "")
        error_type = str(payload.get("error_type") or "")
        message = str(payload.get("error") or "")

        detail = payload.get("detail")
        if not message and isinstance(detail, list):
            message = "请求参数不完整或格式不正确。"
        elif not message and detail:
            message = str(detail)
    else:
        error_code = ""
        error_type = ""
        message = ""

    if not message:
        message = response.text[:500] or f"HTTP {response.status_code}"

    return {
        "message": message,
        "error_code": error_code,
        "error_type": error_type,
        "trace_id": trace_id,
        "status_code": str(response.status_code),
    }


def _build_upload_error_hint(error_info: dict[str, str]) -> str:
    """Build action hint from parsed API error."""
    message = error_info.get("message", "")
    error_code = error_info.get("error_code", "")
    status_code = error_info.get("status_code", "")
    combined = f"{message} {error_code} {status_code}"

    if "FILE_UPLOAD_ERROR" in combined or "文件" in combined:
        return "请确认录音文件仍在本机、格式正确，并重新选择文件后再提交。"
    if "VALIDATION_ERROR" in combined or status_code in {"400", "422"}:
        return "请检查姓名、公司、学科、日期和文件格式后再提交。"
    if "DATABASE_ERROR" in combined or status_code == "503":
        return "后端服务或数据库暂时不可用，稍后重试即可，不需要更换录音文件。"
    if status_code.startswith("5"):
        return "后端处理异常。可以稍后重试；如果反复失败，请记录 trace_id 方便排查。"
    return "请根据错误信息调整后重试。"


def _render_upload_error(response: requests.Response) -> None:
    """Render friendly upload error details."""
    error_info = _parse_error_response(response)
    st.error(f"提交失败：{error_info['message']}")
    st.write(f"状态码：{error_info['status_code']}")
    if error_info["error_code"]:
        st.write(f"错误代码：{error_info['error_code']}")
    if error_info["error_type"]:
        st.write(f"错误类型：{error_info['error_type']}")
    if error_info["trace_id"]:
        st.write(f"追踪 ID：{error_info['trace_id']}")
    st.info(_build_upload_error_hint(error_info))


def _remember_recent_record(record_id: int | str, label: str) -> None:
    """Store latest submitted record in Streamlit session."""
    st.session_state.update(
        {
            "last_submitted_record_id": record_id,
            "last_submitted_record_label": label,
        }
    )


def _render_recent_record_shortcut() -> None:
    """Render shortcut to latest submitted record detail page."""
    record_id = st.session_state.get("last_submitted_record_id")
    if not record_id:
        return

    label = st.session_state.get("last_submitted_record_label") or f"记录 {record_id}"
    st.info(f"最近提交：{label}")
    if st.button("查看最近任务"):
        st.session_state.update({"record_id": record_id, "page": "page_detail"})
        st.rerun()


def page_add() -> None:
    """Render upload form and submit interview audio."""
    if st.button("← 返回主界面"):
        st.session_state.update({"page": "page_main"})
        st.rerun()

    st.title("上传与处理面试录音")
    st.write("上传面试语音文件，系统将自动进行转写、要点提取与分析。")
    _render_recent_record_shortcut()

    api_base_url = get_config().api_base_url
    with st.expander("服务状态", expanded=False):
        st.write(f"API：{api_base_url}")
        if st.button("检查后端服务"):
            is_ready, message = _check_api_ready(api_base_url)
            if is_ready:
                st.success(message)
            else:
                st.error(message)

    name = st.text_input("姓名：").strip()
    company = st.text_input("公司名称：").strip()
    subject = st.selectbox("选择学科", ["python大模型人工智能", "java大模型", "新媒体运营"])
    interview_date: date = st.date_input("面试日期", min_value=None, max_value=None)
    interview_date_str = interview_date.strftime("%Y%m%d")
    file = st.file_uploader(
        "上传面试录音",
        type=["mp3", "wav", "flac", "aac", "m4a"],
        help="限制每个文件最大200MB，支持格式：MP3, WAV, FLAC, AAC, M4A",
    )

    if file is not None:
        file_size = _get_uploaded_file_size(file)
        extension = _get_uploaded_file_extension(file.name)
        st.caption(
            f"已选择：{file.name} · {extension or '未知格式'} · "
            f"{_format_file_size(file_size)}"
        )

    json_data = {
        "name": name,
        "company": company,
        "subject": subject,
        "interview_date_str": interview_date_str,
    }

    validation_errors = _validate_upload_inputs(
        name=name,
        company=company,
        subject=subject,
        interview_date_str=interview_date_str,
        file=file,
    )

    if validation_errors:
        st.warning("请先处理以下问题：")
        for error in validation_errors:
            st.write(f"- {error}")

    is_click_button = st.button("开始分析", disabled=bool(validation_errors))
    if not is_click_button:
        return

    is_ready, ready_message = _check_api_ready(api_base_url)
    if not is_ready:
        st.error(ready_message)
        st.info("请先启动或修复后端 API 服务，再重新提交。")
        return

    if file is None:
        st.error("请上传面试录音文件。")
        return

    try:
        files = {
            "file": (
                file.name,
                file.getbuffer(),
                getattr(file, "type", "application/octet-stream"),
            )
        }
        data = {
            "json_data_str": json.dumps(json_data, ensure_ascii=False)
        }
        resp = requests.post(
            f"{api_base_url}/add_interview_record",
            data=data,
            files=files,
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )
        if resp.ok:
            result = resp.json()
            record_id = result.get("record_id")
            st.success("已提交，开始处理！")
            if record_id:
                _remember_recent_record(record_id, f"{name} / {company}")
                st.session_state.update({
                    "record_id": record_id,
                    "page": "page_detail",
                })
            else:
                st.session_state.update({"page": "page_main"})
            st.rerun()
        else:
            _render_upload_error(resp)
    except requests.RequestException as exc:
        st.error(f"提交出错：无法连接后端服务：{exc}")
        st.info("请确认 API 服务已启动，然后重新提交。")
    except Exception as exc:
        st.error(f"提交出错：{exc}")
