"""
检查点管理工具
查看、清除 LangGraph 检查点
"""
import sys
import os
import asyncio
import aiosqlite
from datetime import datetime

# Add project root to Python path
refactor_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if refactor_root not in sys.path:
    sys.path.insert(0, refactor_root)

from core.utils.path_utils import get_file_path

checkpoint_db_path = get_file_path(
    "data/checkpoints/langgraph_checkpoints.db"
)


async def list_checkpoints_async():
    """列出所有检查点（异步）"""
    if not os.path.exists(checkpoint_db_path):
        print("✓ 没有检查点数据库")
        return
    
    try:
        async with aiosqlite.connect(checkpoint_db_path) as conn:
            # 查询所有检查点
            async with conn.execute("""
                SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
                FROM checkpoints 
                GROUP BY thread_id
                ORDER BY thread_id
            """) as cursor:
                results = await cursor.fetchall()
        
        if not results:
            print("✓ 没有检查点")
            return
        
        print(f"\n找到 {len(results)} 个检查点：")
        print("-" * 80)
        
        for thread_id, count in results:
            # 提取 record_id
            if thread_id.startswith("record_"):
                record_id = thread_id.replace("record_", "")
                print(f"记录 ID: {record_id}")
                print(f"  线程 ID: {thread_id}")
                print(f"  检查点数量: {count}")
                print()
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")


def list_checkpoints():
    """列出所有检查点"""
    asyncio.run(list_checkpoints_async())


async def clear_checkpoint_async(record_id):
    """清除指定记录的检查点（异步）"""
    if not os.path.exists(checkpoint_db_path):
        print("✓ 没有检查点数据库")
        return
    
    thread_id = f"record_{record_id}"
    
    try:
        async with aiosqlite.connect(checkpoint_db_path) as conn:
            # 检查是否存在
            async with conn.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (thread_id,)) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
            
            if count == 0:
                print(f"✓ 记录 {record_id} 没有检查点")
                return
            
            # 删除检查点
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            await conn.commit()
        
        print(f"✅ 已清除记录 {record_id} 的 {count} 个检查点")
        
    except Exception as e:
        print(f"❌ 清除失败: {e}")


def clear_checkpoint(record_id):
    """清除指定记录的检查点"""
    asyncio.run(clear_checkpoint_async(record_id))


async def clear_all_checkpoints_async():
    """清除所有检查点（异步）"""
    if not os.path.exists(checkpoint_db_path):
        print("✓ 没有检查点数据库")
        return
    
    try:
        async with aiosqlite.connect(checkpoint_db_path) as conn:
            # 统计数量
            async with conn.execute("SELECT COUNT(*) FROM checkpoints") as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
            
            if count == 0:
                print("✓ 没有检查点")
                return
            
            # 确认
            choice = input(f"确定要清除所有 {count} 个检查点吗？(y/n): ")
            
            if choice.lower() == 'y':
                await conn.execute("DELETE FROM checkpoints")
                await conn.commit()
                print(f"✅ 已清除所有 {count} 个检查点")
            else:
                print("取消操作")
        
    except Exception as e:
        print(f"❌ 清除失败: {e}")


def clear_all_checkpoints():
    """清除所有检查点"""
    asyncio.run(clear_all_checkpoints_async())


async def view_checkpoint_detail_async(record_id):
    """查看检查点详情（异步）"""
    if not os.path.exists(checkpoint_db_path):
        print("✓ 没有检查点数据库")
        return
    
    thread_id = f"record_{record_id}"
    
    try:
        async with aiosqlite.connect(checkpoint_db_path) as conn:
            # 查询检查点
            async with conn.execute("""
                SELECT checkpoint_id, thread_id, parent_checkpoint_id, checkpoint
                FROM checkpoints 
                WHERE thread_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 5
            """, (thread_id,)) as cursor:
                results = await cursor.fetchall()
        
        if not results:
            print(f"✓ 记录 {record_id} 没有检查点")
            return
        
        print(f"\n记录 {record_id} 的检查点详情（最近 5 个）：")
        print("-" * 80)
        
        for checkpoint_id, thread_id, parent_id, checkpoint_data in results:
            print(f"检查点 ID: {checkpoint_id}")
            print(f"  父检查点: {parent_id}")
            print(f"  数据大小: {len(checkpoint_data)} 字节")
            print()
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")


def view_checkpoint_detail(record_id):
    """查看检查点详情"""
    asyncio.run(view_checkpoint_detail_async(record_id))


def main():
    print("=" * 80)
    print("LangGraph 检查点管理工具")
    print("=" * 80)
    print()
    print("选择操作：")
    print("1. 列出所有检查点")
    print("2. 查看指定记录的检查点详情")
    print("3. 清除指定记录的检查点")
    print("4. 清除所有检查点")
    print("5. 退出")
    print()
    
    choice = input("请输入选项 (1-5): ")
    
    if choice == "1":
        list_checkpoints()
    elif choice == "2":
        record_id = input("请输入记录 ID: ")
        try:
            record_id = int(record_id)
            view_checkpoint_detail(record_id)
        except ValueError:
            print("❌ 无效的 ID")
    elif choice == "3":
        record_id = input("请输入记录 ID: ")
        try:
            record_id = int(record_id)
            clear_checkpoint(record_id)
        except ValueError:
            print("❌ 无效的 ID")
    elif choice == "4":
        clear_all_checkpoints()
    elif choice == "5":
        print("退出")
    else:
        print("❌ 无效的选项")


if __name__ == "__main__":
    main()
