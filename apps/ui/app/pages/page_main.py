from datetime import datetime

import requests
import streamlit as st

from core.config import get_config
from core.task_status import InterviewProcessingStatus, get_processing_status_label


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # 处理 ISO 格式，如 '2025-10-16T12:00:00' 或带Z
        try:
            v = value.replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        except Exception:
            return None
    return None


def get_interview_data():
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
                "processing_status": item.get("processing_status", 0),
                "processing_tips": item.get("processing_tips", ""),
                "update_time": parse_datetime(item.get("update_time"))
            })
    except Exception as e:
        st.error(f"获取面试记录失败：{e}")
    return interview_data


def goto_detail_page(record_id):
    st.session_state.update({"record_id": record_id})
    st.session_state.update({"page": "page_detail"})
    st.rerun()


def page_main():
    st.title("面试录音分析")
    st.write("这是面试录音分析")

    # 顶部右侧“处理语音”按钮，跳转到上传/处理页
    col_left, col_right = st.columns([8, 2])
    with col_right:
        if st.button("处理语音"):
            st.session_state.update({"page": "page_add"})
            st.rerun()

    def status_text(status):
        return get_processing_status_label(status)

    interview_data = get_interview_data()
    # print(interview_data)

    # 添加表头
    st.markdown(
        """
        <style>
            .table-header {
                background-color: #f1f1f1;
                font-weight: bold;
                padding: 8px;
                text-align: left;
            }
            .table-row-even {
                background-color: #f9f9f9;
                padding: 8px;
            }
            .table-row-odd {
                background-color: #e9e9e9;
                padding: 8px;
            }
        </style>
        """, unsafe_allow_html=True)

    # 展示表头
    col_1, col_2, col_3, col_4, col_5, col_6, col_7 = st.columns([1, 1, 1, 1, 1, 1, 2])
    with col_1:
        st.write("姓名")
    with col_2:
        st.write("面试时间")
    with col_3:
        st.write("公司名称")
    with col_4:
        st.write("处理状态")
    with col_5:
        st.write("状态提示")
    with col_6:
        st.write("更新时间")
    with col_7:
        st.write("操作")

    # 使用for循环展示数据，并在同一行展示按钮
    for i, interview in enumerate(interview_data):
        # 根据行数设置背景色
        row_class = "table-row-even" if i % 2 == 0 else "table-row-odd"
        with st.container():
            # 展示每一行数据
            # 顶部右侧“处理语音”按钮，跳转到上传/处理页
            col_1, col_2, col_3, col_4, col_5, col_6, col_7 = st.columns([1, 1, 1, 1, 1, 1, 2])
            with col_1:
                st.write(interview['name'])
            with col_2:
                st.write(interview['interview_time'])
            with col_3:
                st.write(interview['company_name'])
            with col_4:
                st.write(status_text(interview['processing_status']))
            with col_5:
                if interview['processing_tips']:
                    st.write(interview['processing_tips'])
                else:
                    st.write("等待处理")
            with col_6:
                st.write(interview['update_time'])
            with col_7:
                if st.button("查看详情", key=f"button_{i}"):
                    if interview['processing_status'] == InterviewProcessingStatus.COMPLETED:
                        goto_detail_page(interview["id"])
                    else:
                        st.warning("请等待处理完成")
