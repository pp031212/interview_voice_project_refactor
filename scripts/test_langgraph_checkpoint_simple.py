"""
简单测试 LangGraph checkpoint 功能
"""
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from typing import TypedDict

# 定义简单的状态
class SimpleState(TypedDict):
    count: int
    message: str

# 定义简单的节点
def node1(state: SimpleState):
    print("执行 node1")
    state["count"] = state.get("count", 0) + 1
    state["message"] = "node1 完成"
    return state

def node2(state: SimpleState):
    print("执行 node2")
    state["count"] = state.get("count", 0) + 1
    state["message"] = "node2 完成"
    return state

# 创建图
def create_graph():
    # 创建 SQLite 连接
    conn = sqlite3.connect("test_checkpoint.db", check_same_thread=False)
    
    # 创建 checkpointer
    checkpointer = SqliteSaver(conn)
    
    # 创建图
    builder = StateGraph(SimpleState)
    builder.add_node("node1", node1)
    builder.add_node("node2", node2)
    builder.add_edge(START, "node1")
    builder.add_edge("node1", "node2")
    builder.add_edge("node2", END)
    
    # 编译图（带 checkpointer）
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph

# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("测试 LangGraph Checkpoint")
    print("=" * 60)
    
    try:
        graph = create_graph()
        print("✅ 图创建成功（带 checkpointer）")
        
        # 测试执行
        config = {"configurable": {"thread_id": "test_1"}}
        result = graph.invoke({"count": 0, "message": ""}, config=config)
        print(f"✅ 执行成功: {result}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
