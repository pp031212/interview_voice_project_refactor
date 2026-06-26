"""
检查数据库中面试记录的状态
"""
import sys
import os

# Add project root to Python path
refactor_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if refactor_root not in sys.path:
    sys.path.insert(0, refactor_root)

from core.task_status import (  # noqa: E402
    InterviewProcessingStatus,
    get_processing_stage_label,
    get_processing_status_label,
)
from infra.db.db_helper import get_my_db_helper  # noqa: E402

def check_all_records():
    """检查所有面试记录的状态"""
    try:
        db_helper = get_my_db_helper()
        
        print("=" * 80)
        print("数据库中所有面试记录的状态")
        print("=" * 80)
        
        # 获取所有记录（不过滤）
        all_records = db_helper.get_all_interview_records()
        
        if not all_records:
            print("\n❌ 数据库中没有任何面试记录！")
            print("\n可能的原因：")
            print("  1. 数据库表为空")
            print("  2. 数据库连接错误")
            print("  3. 查询条件有误")
            return
        
        print(f"\n找到 {len(all_records)} 条记录：\n")
        
        for record in all_records:
            status = record.get('processing_status', -1)
            stage = record.get('processing_stage')

            print(f"记录 ID: {record['id']}")
            print(f"  姓名: {record['name']}")
            print(f"  公司: {record['company_name']}")
            print(f"  学科: {record.get('subject', 'N/A')}")
            print(f"  录音地址: {record.get('recording_url', 'N/A')}")
            print(f"  处理状态: {status} ({get_processing_status_label(status)})")
            stage_label = get_processing_stage_label(stage) if stage else "N/A"
            print(f"  处理阶段: {stage or 'N/A'} ({stage_label})")
            print(f"  提示信息: {record.get('processing_tips', 'N/A')}")
            print(f"  创建时间: {record.get('create_time', 'N/A')}")
            print(f"  更新时间: {record.get('update_time', 'N/A')}")
            print("-" * 80)

        # 统计各状态的数量
        print("\n状态统计：")
        status_count: dict[str, int] = {}
        for record in all_records:
            status = record.get('processing_status', -1)
            label = get_processing_status_label(status)
            status_count[label] = status_count.get(label, 0) + 1
        
        for status_text, count in status_count.items():
            print(f"  {status_text}: {count} 条")
        
        # 检查未处理的记录
        print("\n" + "=" * 80)
        unprocessed_records = db_helper.get_all_interview_records({"processing_status": InterviewProcessingStatus.PENDING})
        print(f"未处理的记录数量: {len(unprocessed_records)}")
        
        if unprocessed_records:
            print("\n未处理的记录详情：")
            for record in unprocessed_records:
                print(f"  - ID={record['id']}, 姓名={record['name']}, 公司={record['company_name']}")
        else:
            print("  (没有未处理的记录)")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_records()
