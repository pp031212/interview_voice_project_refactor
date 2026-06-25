import json

import requests
import streamlit as st

from core.config import get_config


def page_add():
    # 左上角返回主界面按钮
    if st.button("← 返回主界面"):
        st.session_state.update({"page": "page_main"})
        st.rerun()
    # print(st.query_params['page'])

    # 标题与副标题（根据业务调整）
    st.title("上传与处理面试录音")
    st.write("上传面试语音文件，系统将自动进行转写、要点提取与分析。")

    # 获取用户输入的字段
    name = st.text_input("姓名：")
    company = st.text_input("公司名称：")
    subject = st.selectbox("选择学科", ["python大模型人工智能", "java大模型", "新媒体运营"])
    # 添加日期选择器
    interview_date = st.date_input("面试日期", min_value=None, max_value=None)
    interview_date_str = interview_date.strftime('%Y%m%d')
    file = st.file_uploader(
        "上传面试录音",
        type=["mp3", "wav", "flac", "aac", "m4a"],
        help="限制每个文件最大200MB，支持的格式有：MP3, WAV, FLAC, AAC, M4A",

    )

    # 构建输入数据字典
    json_data = {
        "name": name,
        "company": company,
        "subject": subject,
        "interview_date_str": interview_date_str
    }
    print(json_data)

    # 确保用户输入完整并上传了文件
    if file is not None and name and company and subject and interview_date_str:
        is_click_button = st.button("开始分析")
        if is_click_button:
            try:
                # 组织 multipart/form-data
                files = {
                    "file": (file.name, file.getbuffer(), getattr(file, "type", "application/octet-stream"))
                }
                data = {
                    "json_data_str": json.dumps(json_data, ensure_ascii=False)
                }
                api_base_url = get_config().api_base_url
                resp = requests.post(
                    f"{api_base_url}/add_interview_record",
                    data=data,
                    files=files,
                    timeout=60,
                )
                if resp.ok:
                    result = resp.json()
                    record_id = result.get("record_id")
                    st.success("已提交，开始处理！")
                    if record_id:
                        st.session_state.update({
                            "record_id": record_id,
                            "page": "page_detail",
                        })
                    else:
                        st.session_state.update({"page": "page_main"})
                    st.rerun()
                else:
                    st.error(f"提交失败：{resp.status_code} {resp.text}")
            except Exception as e:
                st.error(f"提交出错：{e}")
    else:
        st.warning("请填写所有字段并上传录音文件。")
