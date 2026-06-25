from __future__ import annotations

import asyncio
import time

from sqlalchemy.exc import OperationalError

from core.utils.path_utils import get_file_path
from core.utils.time_utils import get_datetime_str_from_datetime
from core.task_status import InterviewProcessingStatus
from core.worker_exception_handler import handle_worker_exception
from infra.db.db_helper import get_my_db_helper
from pipelines.langgraph_agent import clear_checkpoint, interview_voice_analyse
from pipelines.nodes.__002__voice_to_text_node import clear_asr_resume_cache
from pipelines.nodes.__004__extract_interview_topic_node import clear_extract_resume_cache
from pipelines.nodes.__005__offer_sample_answer_node import clear_analysis_resume_cache


def check_db_connection() -> bool:
    try:
        db_helper = get_my_db_helper()
        return db_helper._check_connection()
    except Exception:
        return False


def run_loop() -> None:
    print("正在检查数据库连接...")
    if not check_db_connection():
        print("\n" + "=" * 60)
        print("错误: 无法连接到 MySQL 数据库")
        print("=" * 60)
        print("\n可能的原因：")
        print("  1. MySQL 服务未启动")
        print("  2. 数据库配置错误（检查 .env 文件）")
        print("  3. 数据库不存在")
        print("  4. 防火墙阻止连接")
        print("\n解决方案：")
        print("  1. 启动 MySQL 服务：")
        print("     - Windows: 在服务管理器中启动 MySQL 服务")
        print("     - 或运行: net start MySQL")
        print("     - 或在 PowerShell 中运行: Get-Service MySQL* | Start-Service")
        print("  2. 检查 .env 文件中的数据库配置：")
        print("     - MYSQL_HOST")
        print("     - MYSQL_USER")
        print("     - MYSQL_PASSWORD")
        print("     - MYSQL_DATABASE_NAME")
        print("  3. 确认数据库已创建")
        print("  4. 运行测试脚本检查连接：")
        print("     python apps/worker/scripts/test_db_connection.py")
        print("\n程序将在 30 秒后重试...")
        print("=" * 60)
        return

    print("✓ 数据库连接正常，开始运行...\n")

    while True:
        try:
            db_helper = get_my_db_helper()

            # 使用原子认领方法获取下一条待处理记录
            interview_record, from_failed = db_helper.claim_next_interview_record()

            if interview_record:
                record_id = interview_record['id']

                print(f"\n{'='*60}")
                if from_failed:
                    print(f"开始断点续传失败记录 ID={record_id}")
                else:
                    print(f"开始处理面试记录 ID={record_id}")
                print(f"姓名: {interview_record['name']}")
                print(f"公司: {interview_record['company_name']}")
                print(f"{'='*60}\n")

                interview_info_dict = {
                    "name": interview_record["name"],
                    "company": interview_record["company_name"],
                    "subject": interview_record["subject"],
                    "interview_date_str": get_datetime_str_from_datetime(
                        interview_record['interview_time']
                    ),
                }

                try:
                    asyncio.run(
                        interview_voice_analyse(
                            get_file_path(interview_record['recording_url']),
                            record_id,
                            interview_info_dict,
                        )
                    )

                    db_helper.update_interview_record(record_id, {"processing_status": InterviewProcessingStatus.COMPLETED})
                    clear_checkpoint(record_id)
                    clear_asr_resume_cache(record_id)
                    clear_extract_resume_cache(record_id)
                    clear_analysis_resume_cache(record_id)

                    print(f"\n{'='*60}")
                    print(f"✅ 面试记录 {record_id} 处理完成")
                    print(f"{'='*60}\n")
                except Exception as exc:
                    # 使用统一的异常处理
                    error_message, is_retryable = handle_worker_exception(
                        record_id, exc, "处理面试记录"
                    )

                    print(f"\n{'='*60}")
                    print(f"❌ 处理面试记录 {record_id} 时出错")
                    print(f"{'='*60}")
                    print(f"错误信息: {error_message}")
                    print(f"可重试: {'是' if is_retryable else '否'}")

                    try:
                        db_helper = get_my_db_helper()
                        error_type = "临时错误（可重试）" if is_retryable else "永久错误（需人工介入）"
                        db_helper.update_interview_record(
                            record_id,
                            {
                                "processing_status": InterviewProcessingStatus.FAILED,
                                "processing_tips": (
                                    f"处理失败: {error_message}\n"
                                    f"错误类型: {error_type}\n"
                                    "提示: 修复问题后重置记录，将从断点继续"
                                ),
                            },
                        )
                        print(f"\n✓ 已将面试记录 {record_id} 标记为失败状态")
                        print("✓ 检查点已保留，修复问题后重置记录将从断点继续")
                        print("  使用命令: python scripts/reset_failed_records.py")
                        print(f"{'='*60}\n")
                    except Exception:
                        pass
            else:
                time.sleep(30)
        except OperationalError as exc:
            print(f"\n数据库连接错误: {exc}")
            print("MySQL 服务可能已停止，等待 30 秒后重试...")
            print("提示: 请确保 MySQL 服务正在运行\n")
            time.sleep(30)
        except Exception as exc:
            print(f"运行过程中出错: {exc}")
            import traceback

            traceback.print_exc()
            time.sleep(30)




