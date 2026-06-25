import requests
import streamlit as st

from core.config import get_config


def get_data_by_id(record_id):
    api_base_url = get_config().api_base_url
    resp = requests.get(
        f"{api_base_url}/interview_records/{record_id}",
        timeout=60,
    )
    if resp.ok:
        result_dict = resp.json()
        data_dict = result_dict.get("data", {})
        return data_dict
    else:
        st.error(f"获取详情失败：{resp.status_code} {resp.text}")


def page_detail():
    if st.button("← 返回主界面"):
        st.session_state.update({"page": "page_main"})
        st.rerun()
    st.title("面试评价详情页")

    record_id = st.session_state.get("record_id", "")
    # print(record_id)
    data_dict = get_data_by_id(record_id)
    if not data_dict:
        st.error("未获取到面试记录详情，请稍后重试。")
        return

    markdown_text = data_dict.get("markdown_text")
    if not markdown_text:
        st.warning("该记录尚未生成面试报告，请等待处理完成。")
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
