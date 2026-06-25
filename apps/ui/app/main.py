import sys
from pathlib import Path

import streamlit as st

REFACTOR_ROOT = Path(__file__).resolve().parents[3]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from app.pages.page_add import page_add
from app.pages.page_detail import page_detail
from app.pages.page_main import page_main
from app.pages.page_test import page_test

hide_sidebar = """
<style>
    section[data-testid="stSidebar"] {
        display: none;
    }
</style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)


# 获取当前页面的查询参数
def main():
    # 获取当前 URL 中的页面参数
    page = st.session_state.get("page", "page_main")

    # 根据页面选择显示不同的内容
    if page == "page_main":
        page_main()
    elif page == "page_detail":
        page_detail()
    elif page == "page_add":
        page_add()
    else:
        page_test()


if __name__ == "__main__":
    main()
