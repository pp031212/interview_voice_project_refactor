import sys
import os
import sqlite3
from pathlib import Path

REFACTOR_ROOT = Path(__file__).resolve().parents[1]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from core.output_graph_utils import output_pic_graph
from core.utils.path_utils import get_file_path
from pipelines.agent_state import AgentState
from pipelines.nodes.__001__split_voice_node import split_voice_node
from pipelines.nodes.__002__voice_to_text_node import voice_to_text_node
from pipelines.nodes.__003__voice_text_arrange_node import voice_text_arrange_node
from pipelines.nodes.__004__extract_interview_topic_node import extract_interview_topic_node
from pipelines.nodes.__005__offer_sample_answer_node import offer_sample_answer_node
from pipelines.nodes.__006__offer_interview_advice_node import offer_interview_advice_node
from pipelines.nodes.__007__generate_markdown_node import generate_markdown_node

# 创建检查点保存器（使用 AsyncSqliteSaver）
checkpoint_db_path = get_file_path("data/checkpoints/langgraph_checkpoints.db")
os.makedirs(os.path.dirname(checkpoint_db_path), exist_ok=True)

# 全局 checkpointer 实例
memory = None


def _is_malformed_sqlite_error(exc: Exception) -> bool:
    """判断是否为 SQLite 文件损坏错误。"""
    return "database disk image is malformed" in str(exc).lower()


def _checkpoint_related_paths() -> list[str]:
    """返回 checkpoint 数据库相关文件路径。"""
    return [
        checkpoint_db_path,
        f"{checkpoint_db_path}-wal",
        f"{checkpoint_db_path}-shm",
        f"{checkpoint_db_path}-journal",
    ]


def _rebuild_checkpoint_db(reason: str) -> None:
    """删除损坏的 checkpoint 数据库及 sidecar 文件，等待后续自动重建。"""
    print(f"⚠️ 检查点数据库异常，开始重建: {reason}")
    for path in _checkpoint_related_paths():
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"✓ 已删除损坏文件: {path}")
        except Exception as remove_error:
            print(f"⚠️ 删除文件失败({path}): {remove_error}")


def _startup_integrity_check() -> None:
    """启动时检查 checkpoint 数据库完整性，异常时自动重建。"""
    if not os.path.exists(checkpoint_db_path):
        return

    conn = None
    try:
        conn = sqlite3.connect(checkpoint_db_path)
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        if not row or row[0] != "ok":
            raise sqlite3.DatabaseError(f"integrity_check failed: {row[0] if row else 'unknown'}")
    except Exception as exc:
        if _is_malformed_sqlite_error(exc) or "integrity_check failed" in str(exc).lower():
            _rebuild_checkpoint_db(f"启动校验失败: {exc}")
        else:
            print(f"⚠️ 检查点完整性校验异常（已忽略）: {exc}")
    finally:
        if conn is not None:
            conn.close()


_startup_integrity_check()

async def get_checkpointer():
    """获取异步检查点保存器"""
    global memory
    if memory is None:
        # 使用 from_conn_string 创建异步上下文管理器
        memory = AsyncSqliteSaver.from_conn_string(checkpoint_db_path)
    return memory


def build_graph(use_checkpointer=True):
    """
    构建 LangGraph 图
    
    Args:
        use_checkpointer: 是否使用检查点功能
    """
    # 定义状态图
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node(split_voice_node.__name__, split_voice_node)
    graph_builder.add_node(voice_to_text_node.__name__, voice_to_text_node)
    graph_builder.add_node(voice_text_arrange_node.__name__, voice_text_arrange_node)
    graph_builder.add_node(extract_interview_topic_node.__name__, extract_interview_topic_node)
    graph_builder.add_node(offer_sample_answer_node.__name__, offer_sample_answer_node)
    graph_builder.add_node(offer_interview_advice_node.__name__, offer_interview_advice_node)
    graph_builder.add_node(generate_markdown_node.__name__, generate_markdown_node)

    # 添加边
    graph_builder.add_edge(START, split_voice_node.__name__)
    graph_builder.add_edge(split_voice_node.__name__, voice_to_text_node.__name__)
    graph_builder.add_edge(voice_to_text_node.__name__, voice_text_arrange_node.__name__)
    graph_builder.add_edge(voice_text_arrange_node.__name__, extract_interview_topic_node.__name__)
    graph_builder.add_edge(extract_interview_topic_node.__name__, offer_sample_answer_node.__name__)
    graph_builder.add_edge(offer_sample_answer_node.__name__, offer_interview_advice_node.__name__)
    graph_builder.add_edge(offer_interview_advice_node.__name__, generate_markdown_node.__name__)
    graph_builder.add_edge(generate_markdown_node.__name__, END)

    # 编译状态图（暂时不使用检查点，因为需要在异步上下文中）
    # 检查点功能将在 interview_voice_analyse 函数中动态添加
    graph = graph_builder.compile()
    return graph


graph = build_graph()
# 输出表的状态图
output_pic_graph(graph, get_file_path("pipelines/graph.jpg"))


async def interview_voice_analyse(file_location, record_id, interview_info_dict, use_checkpoint=True):
    """
    分析面试录音
    
    Args:
        file_location: 音频文件路径
        record_id: 面试记录ID
        interview_info_dict: 面试信息字典
        use_checkpoint: 是否使用检查点功能
    
    Returns:
        生成的 Markdown 文本
    """
    # 使用 record_id 作为线程 ID，这样每个记录都有独立的检查点
    thread_id = f"record_{record_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"📌 使用线程 ID: {thread_id}")
    
    # 如果使用检查点，需要在异步上下文中创建带检查点的图
    if use_checkpoint:
        for attempt in range(2):
            try:
                async with AsyncSqliteSaver.from_conn_string(checkpoint_db_path) as checkpointer:
                    # 重新编译图，添加检查点
                    graph_builder = StateGraph(AgentState)
                    graph_builder.add_node(split_voice_node.__name__, split_voice_node)
                    graph_builder.add_node(voice_to_text_node.__name__, voice_to_text_node)
                    graph_builder.add_node(voice_text_arrange_node.__name__, voice_text_arrange_node)
                    graph_builder.add_node(extract_interview_topic_node.__name__, extract_interview_topic_node)
                    graph_builder.add_node(offer_sample_answer_node.__name__, offer_sample_answer_node)
                    graph_builder.add_node(offer_interview_advice_node.__name__, offer_interview_advice_node)
                    graph_builder.add_node(generate_markdown_node.__name__, generate_markdown_node)

                    graph_builder.add_edge(START, split_voice_node.__name__)
                    graph_builder.add_edge(split_voice_node.__name__, voice_to_text_node.__name__)
                    graph_builder.add_edge(voice_to_text_node.__name__, voice_text_arrange_node.__name__)
                    graph_builder.add_edge(voice_text_arrange_node.__name__, extract_interview_topic_node.__name__)
                    graph_builder.add_edge(extract_interview_topic_node.__name__, offer_sample_answer_node.__name__)
                    graph_builder.add_edge(offer_sample_answer_node.__name__, offer_interview_advice_node.__name__)
                    graph_builder.add_edge(offer_interview_advice_node.__name__, generate_markdown_node.__name__)
                    graph_builder.add_edge(generate_markdown_node.__name__, END)

                    graph_with_checkpoint = graph_builder.compile(checkpointer=checkpointer)

                    print(f"✓ 检查点功能已启用")

                    # 检查是否有现有的检查点
                    try:
                        state_snapshot = await graph_with_checkpoint.aget_state(config)
                        if state_snapshot and state_snapshot.values:
                            print(f"✓ 发现现有检查点，将从断点继续执行")
                            print(f"  上次执行到: {state_snapshot.next}")
                        else:
                            print(f"✓ 没有检查点，将从头开始执行")
                    except Exception as e:
                        if _is_malformed_sqlite_error(e):
                            raise
                        print(f"⚠️ 检查检查点时出错: {e}")

                    # 执行图（如果有检查点会自动从断点继续）
                    result = await graph_with_checkpoint.ainvoke(
                        {
                            "input_audio_path": file_location,
                            "record_id": record_id,
                            "interview_info_dict": interview_info_dict
                        },
                        config=config
                    )

                    return result.get("interview_markdown_text", "")
            except Exception as e:
                if _is_malformed_sqlite_error(e) and attempt == 0:
                    _rebuild_checkpoint_db(f"运行期损坏: {e}")
                    print("🔄 已重建 checkpoint 数据库，重试一次...")
                    continue

                print(f"⚠️ 使用检查点功能失败: {e}")
                print("将不使用检查点功能继续执行")
                use_checkpoint = False
                break
    
    # 不使用检查点的情况
    if not use_checkpoint:
        print("✓ 不使用检查点功能")
        result = await graph.ainvoke(
            {
                "input_audio_path": file_location, 
                "record_id": record_id, 
                "interview_info_dict": interview_info_dict
            }
        )
        return result.get("interview_markdown_text", "")


def clear_checkpoint(record_id):
    """
    清除指定记录的检查点
    
    Args:
        record_id: 面试记录ID
    """
    thread_id = f"record_{record_id}"
    # 清除检查点：失败时若检测到数据库损坏，自动重建并重试一次
    import asyncio
    import aiosqlite

    async def _clear():
        async with aiosqlite.connect(checkpoint_db_path) as conn:
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            await conn.commit()

    for attempt in range(2):
        try:
            asyncio.run(_clear())
            print(f"✓ 已清除记录 {record_id} 的检查点")
            return True
        except Exception as e:
            if _is_malformed_sqlite_error(e) and attempt == 0:
                _rebuild_checkpoint_db(f"清理检查点失败: {e}")
                print("🔄 已重建 checkpoint 数据库，重试一次清理...")
                continue
            print(f"⚠️ 清除检查点失败: {e}")
            return False


if __name__ == '__main__':
    result = interview_voice_analyse(get_file_path("__001__data/新录音20.m4a"), "",
                                     {"name": "张三", "company": "传智播客", "subject": "python大模型人工智能",
                                      "interview_date_str": "2023-05-05"})
    print(result)
    ...

