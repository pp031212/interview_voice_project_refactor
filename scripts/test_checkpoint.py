"""
测试 LangGraph 检查点功能
"""
import sys
import os

# Add project root to Python path
refactor_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if refactor_root not in sys.path:
    sys.path.insert(0, refactor_root)

from pipelines.langgraph_agent import graph, clear_checkpoint
from core.utils.path_utils import get_file_path


def test_checkpoint():
    """测试检查点功能"""
    print("=" * 80)
    print("测试 LangGraph 检查点功能")
    print("=" * 80)
    print()
    
    # 测试线程 ID
    test_thread_id = "test_record_999"
    config = {"configurable": {"thread_id": test_thread_id}}
    
    print(f"1. 检查是否有现有检查点...")
    try:
        state_snapshot = graph.get_state(config)
        if state_snapshot and state_snapshot.values:
            print(f"   ✓ 发现现有检查点")
            print(f"   上次执行到: {state_snapshot.next}")
        else:
            print(f"   ✓ 没有检查点")
    except Exception as e:
        print(f"   ⚠️ 检查失败: {e}")
    
    print()
    print(f"2. 测试清除检查点...")
    try:
        # 清除测试检查点
        import sqlite3
        checkpoint_db_path = get_file_path(
            "data/checkpoints/langgraph_checkpoints.db"
        )
        if os.path.exists(checkpoint_db_path):
            conn = sqlite3.connect(checkpoint_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (test_thread_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            print(f"   ✓ 清除了 {deleted_count} 个测试检查点")
        else:
            print(f"   ✓ 检查点数据库不存在")
    except Exception as e:
        print(f"   ⚠️ 清除失败: {e}")
    
    print()
    print("=" * 80)
    print("✅ 检查点功能测试完成")
    print("=" * 80)
    print()
    print("说明：")
    print("- 检查点会在每个节点执行后自动保存")
    print("- 失败后重新执行会自动从断点继续")
    print("- 使用 'python manage_checkpoints.py' 管理检查点")
    print()


if __name__ == "__main__":
    test_checkpoint()
