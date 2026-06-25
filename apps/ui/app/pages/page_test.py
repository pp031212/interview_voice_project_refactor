import streamlit as st


def page_test():
    # 创建示例数据
    data = [
        {"ID": 1, "姓名": "张三", "年龄": 25, "城市": "北京"},
        {"ID": 2, "姓名": "李四", "年龄": 30, "城市": "上海"},
        {"ID": 3, "姓名": "王五", "年龄": 28, "城市": "广州"},
        {"ID": 4, "姓名": "赵六", "年龄": 35, "城市": "深圳"},
    ]

    # 标题
    st.title("员工信息列表")

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
    st.markdown(
        f"""
        <div class="table-header">
            <span style="width: 20%; display: inline-block;">姓名</span>
            <span style="width: 20%; display: inline-block;">年龄</span>
            <span style="width: 30%; display: inline-block;">城市</span>
            <span style="width: 20%; display: inline-block;">查看详情</span>
        </div>
        """, unsafe_allow_html=True)

    # 使用for循环展示数据，并在同一行展示按钮
    for i, person in enumerate(data):
        # 根据行数设置背景色
        row_class = "table-row-even" if i % 2 == 0 else "table-row-odd"

        # 展示每一行数据
        st.markdown(
            f"""
            <div class="{row_class}">
                <span style="width: 20%; display: inline-block;">{person['姓名']}</span>
                <span style="width: 20%; display: inline-block;">{person['年龄']}</span>
                <span style="width: 30%; display: inline-block;">{person['城市']}</span>
                <span style="width: 20%; display: inline-block;">
                    <button onclick="window.location.href='#'">查看详情 {person['ID']}</button>
                </span>
            </div>
            """, unsafe_allow_html=True)

        # # 创建查看详情按钮
        # if st.button(f"查看详情 {person['ID']}"):
        #     st.write(f"你选择查看的是: {person['姓名']}的详细信息")
        #     st.write(f"ID: {person['ID']}")
        #     st.write(f"姓名: {person['姓名']}")
        #     st.write(f"年龄: {person['年龄']}")
        #     st.write(f"城市: {person['城市']}")
