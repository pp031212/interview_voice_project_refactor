"""
重置失败的面试记录
将处理失败（status=3）的记录重置为未处理（status=0），以便重新处理
"""
import sys
import os

# Add project root to Python path
refactor_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if refactor_root not in sys.path:
    sys.path.insert(0, refactor_root)

from core.task_status import InterviewProcessingStatus, get_processing_status_label
from infra.db.db_helper import get_my_db_helper

def reset_failed_records():
    """重置所有失败或处理中的面试记录"""
    try:
        db_helper = get_my_db_helper()
        
        # 获取所有失败的记录和处理中的记录
        failed_records = db_helper.get_all_interview_records({"processing_status": InterviewProcessingStatus.FAILED})
        processing_records = db_helper.get_all_interview_records({"processing_status": InterviewProcessingStatus.PROCESSING})
        
        # 合并两个列表
        all_records_to_reset = failed_records + processing_records
        
        if not all_records_to_reset:
            print("✓ 没有需要重置的记录（失败或处理中）")
            return
        
        print(f"找到 {len(all_records_to_reset)} 条需要重置的记录：")
        print(f"  - 失败的记录: {len(failed_records)} 条")
        print(f"  - 处理中的记录: {len(processing_records)} 条")
        print("-" * 80)
        
        for record in all_records_to_reset:
            print(f"ID: {record['id']}")
            print(f"  姓名: {record['name']}")
            print(f"  公司: {record['company_name']}")
            print(f"  失败原因: {record.get('processing_tips', 'N/A')}")
            print()
        
        print("-" * 80)
        print("⚠️  重要提示：")
        print("  - 重置后将从上次失败的地方继续执行（断点续传）")
        print("  - 不会重新执行已完成的步骤（如音频分割、语音识别）")
        print("  - 请确保已修复导致失败的问题（如 API 配置）")
        print("  - 处理中的记录可能是因为程序异常退出导致的")
        print("-" * 80)
        choice = input("是否要重置这些记录为未处理状态？(y/n): ")
        
        if choice.lower() == 'y':
            for record in all_records_to_reset:
                db_helper.reset_interview_record_to_pending(record['id'])
                print(f"✓ 已重置记录 ID={record['id']}")
            
            print(f"\n✅ 成功重置 {len(all_records_to_reset)} 条记录")
        else:
            print("取消操作")
            
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        import traceback
        traceback.print_exc()

def reset_specific_record(record_id):
    """重置指定的面试记录"""
    try:
        db_helper = get_my_db_helper()
        
        # 获取记录信息
        records = db_helper.get_all_interview_records({"id": record_id})
        
        if not records:
            print(f"❌ 未找到 ID={record_id} 的记录")
            return
        
        record = records[0]
        print(f"找到记录：")
        print(f"  ID: {record['id']}")
        print(f"  姓名: {record['name']}")
        print(f"  公司: {record['company_name']}")
        print(f"  当前状态: {record['processing_status']} ({get_processing_status_label(record['processing_status'])})")
        print(f"  提示信息: {record.get('processing_tips', 'N/A')}")
        print()
        
        print("⚠️  重要提示：")
        print("  - 重置后将从上次失败的地方继续执行（断点续传）")
        print("  - 不会重新执行已完成的步骤")
        print()
        
        choice = input("是否要重置此记录为未处理状态？(y/n): ")
        
        if choice.lower() == 'y':
            db_helper.reset_interview_record_to_pending(record_id)
            print(f"✅ 已重置记录 ID={record_id}")
        else:
            print("取消操作")
            
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 80)
    print("面试记录重置工具")
    print("=" * 80)
    print()
    print("选择操作：")
    print("1. 重置所有失败的记录")
    print("2. 重置指定 ID 的记录")
    print("3. 退出")
    print()
    
    choice = input("请输入选项 (1-3): ")
    
    if choice == "1":
        reset_failed_records()
    elif choice == "2":
        record_id = input("请输入记录 ID: ")
        try:
            record_id = int(record_id)
            reset_specific_record(record_id)
        except ValueError:
            print("❌ 无效的 ID")
    elif choice == "3":
        print("退出")
    else:
        print("❌ 无效的选项")

if __name__ == "__main__":
    main()
