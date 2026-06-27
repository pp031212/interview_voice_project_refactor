"""
数据库初始化脚本
自动创建数据库和表结构
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

REFACTOR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REFACTOR_ROOT not in sys.path:
    sys.path.insert(0, REFACTOR_ROOT)

from infra.db.model.base import Base  # noqa: E402
from infra.db.model.tb_user import TbUser  # noqa: E402,F401
from infra.db.model.tb_interview_recording_analysis import (  # noqa: E402,F401
    TbInterviewRecordingAnalysis,
)
from infra.db.model.tb_interview_recording_analysis_detail import (  # noqa: E402,F401
    TbInterviewRecordingAnalysisDetail,
)
from infra.db.model.tb_asr_segment_cache import TbAsrSegmentCache  # noqa: E402,F401

# 加载环境变量
load_dotenv(os.path.join(REFACTOR_ROOT, ".env"))

def create_database():
    """创建数据库（如果不存在）"""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '1234')
    database = os.getenv('MYSQL_DATABASE_NAME', 'interview_voice')
    
    # 连接到 MySQL 服务器（不指定数据库）
    engine = create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/',
        echo=True
    )
    
    try:
        with engine.connect() as conn:
            # 创建数据库
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            print(f"✅ 数据库 '{database}' 创建成功或已存在")
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        raise
    finally:
        engine.dispose()

def create_tables():
    """创建所有表"""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '1234')
    database = os.getenv('MYSQL_DATABASE_NAME', 'interview_voice')
    
    # 连接到指定数据库
    engine = create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4',
        echo=True
    )
    
    try:
        # 创建所有表
        Base.metadata.create_all(engine)
        print("✅ 所有表创建成功")
        
        # 显示创建的表
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"\n📋 已创建的表: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        raise
    finally:
        engine.dispose()

def fix_text_columns():
    """
    修复文本字段的长度限制
    将 TEXT 类型改为 LONGTEXT 类型，避免大文本保存失败
    """
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '1234')
    database = os.getenv('MYSQL_DATABASE_NAME', 'interview_voice')
    
    # 连接到指定数据库
    engine = create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4',
        echo=False  # 关闭SQL日志，避免输出过多
    )
    
    try:
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                print("\n正在优化文本字段类型...")
                
                # 需要修改的字段列表
                columns_to_fix = [
                    ('markdown_text', '面试评价格式生成'),
                    ('interview_text', '面试文本'),
                    ('processing_tips', '处理提示'),
                    ('overall_comments', '整体点评'),
                    ('strengths', '优势点'),
                    ('weaknesses', '不足点'),
                    ('improvement_suggestions', '改进建议'),
                ]
                
                for column_name, comment in columns_to_fix:
                    # 检查字段是否存在
                    check_sql = text("""
                        SELECT COLUMN_TYPE 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = :database 
                        AND TABLE_NAME = 'tb_interview_recording_analysis' 
                        AND COLUMN_NAME = :column_name
                    """)
                    
                    result = conn.execute(
                        check_sql, 
                        {"database": database, "column_name": column_name}
                    ).fetchone()
                    
                    if result:
                        current_type = result[0]
                        
                        # 如果不是 LONGTEXT，则修改
                        if current_type.lower() != 'longtext':
                            alter_sql = text(f"""
                                ALTER TABLE tb_interview_recording_analysis 
                                MODIFY COLUMN {column_name} LONGTEXT COMMENT :comment
                            """)
                            
                            conn.execute(alter_sql, {"comment": comment})
                            print(f"  ✓ {column_name}: {current_type} → LONGTEXT")
                        else:
                            print(f"  ✓ {column_name}: 已是 LONGTEXT，跳过")

                columns_to_add = [
                    (
                        "processing_stage",
                        "VARCHAR(64) NULL COMMENT '处理阶段' AFTER processing_tips",
                    ),
                    (
                        "processing_trace_id",
                        "VARCHAR(64) NULL COMMENT '任务追踪ID' AFTER processing_stage",
                    ),
                    (
                        "error_code",
                        "VARCHAR(64) NULL COMMENT '错误代码' AFTER processing_trace_id",
                    ),
                    (
                        "error_type",
                        "VARCHAR(32) NULL COMMENT '错误类型' AFTER error_code",
                    ),
                    (
                        "error_message",
                        "LONGTEXT NULL COMMENT '错误信息' AFTER error_type",
                    ),
                    (
                        "retry_count",
                        "INT NULL DEFAULT 0 COMMENT '当前重试次数' AFTER error_message",
                    ),
                    (
                        "max_retries",
                        "INT NULL COMMENT '最大重试次数' AFTER retry_count",
                    ),
                    (
                        "failed_at",
                        "DATETIME NULL COMMENT '失败时间' AFTER max_retries",
                    ),
                    (
                        "processing_started_at",
                        "DATETIME NULL COMMENT '开始处理时间' AFTER failed_at",
                    ),
                    (
                        "stage_started_at",
                        "DATETIME NULL COMMENT '当前阶段开始时间' "
                        "AFTER processing_started_at",
                    ),
                    (
                        "last_progress_at",
                        "DATETIME NULL COMMENT '最近进度更新时间' "
                        "AFTER stage_started_at",
                    ),
                    (
                        "completed_at",
                        "DATETIME NULL COMMENT '完成时间' AFTER last_progress_at",
                    ),
                    (
                        "overall_rubric_score",
                        "FLOAT NULL COMMENT 'Rubric整体评分' AFTER interview_score",
                    ),
                    (
                        "overall_rubric_json",
                        "LONGTEXT NULL COMMENT 'Rubric整体评分详情JSON' "
                        "AFTER overall_rubric_score",
                    ),
                ]
                for column_name, column_definition in columns_to_add:
                    column = conn.execute(
                        text("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = :database
                            AND TABLE_NAME = 'tb_interview_recording_analysis'
                            AND COLUMN_NAME = :column_name
                        """),
                        {"database": database, "column_name": column_name},
                    ).fetchone()
                    if column is None:
                        conn.execute(
                            text(
                                "ALTER TABLE tb_interview_recording_analysis "
                                f"ADD COLUMN {column_name} {column_definition}"
                            )
                        )
                        print(f"  ✓ {column_name}: 已补齐兼容列")
                    else:
                        print(f"  ✓ {column_name}: 已存在，跳过")

                detail_columns_to_add = [
                    (
                        "rubric_score",
                        "FLOAT NULL COMMENT 'Rubric评分' AFTER answer_score",
                    ),
                    (
                        "rubric_json",
                        "LONGTEXT NULL COMMENT 'Rubric评分详情JSON' AFTER rubric_score",
                    ),
                ]
                for column_name, column_definition in detail_columns_to_add:
                    column = conn.execute(
                        text("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = :database
                            AND TABLE_NAME = 'tb_interview_recording_analysis_detail'
                            AND COLUMN_NAME = :column_name
                        """),
                        {"database": database, "column_name": column_name},
                    ).fetchone()
                    if column is None:
                        conn.execute(
                            text(
                                "ALTER TABLE tb_interview_recording_analysis_detail "
                                f"ADD COLUMN {column_name} {column_definition}"
                            )
                        )
                        print(f"  ✓ {column_name}: 已补齐明细兼容列")
                    else:
                        print(f"  ✓ {column_name}: 已存在，跳过")
                
                # 提交事务
                trans.commit()
                print("✅ 文本字段优化完成")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 字段优化失败: {e}")
                raise
                
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        raise
    finally:
        engine.dispose()

def main():
    """主函数"""
    print("=" * 60)
    print("开始初始化数据库...")
    print("=" * 60)
    
    try:
        # 步骤 1: 创建数据库
        print("\n[步骤 1/3] 创建数据库...")
        create_database()
        
        # 步骤 2: 创建表
        print("\n[步骤 2/3] 创建表结构...")
        create_tables()
        
        # 步骤 3: 优化字段类型
        print("\n[步骤 3/3] 优化字段类型并补齐兼容列...")
        fix_text_columns()
        
        print("\n" + "=" * 60)
        print("✅ 数据库初始化完成！")
        print("=" * 60)
        print("\n说明:")
        print("  • 数据库已创建")
        print("  • 表结构已创建")
        print("  • 文本字段已优化为 LONGTEXT（支持大文本）")
        print("  • 主表兼容列已检查")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 数据库初始化失败: {e}")
        print("=" * 60)
        print("\n请检查:")
        print("1. MySQL 服务是否已启动")
        print("2. .env 文件中的数据库配置是否正确")
        print("3. MySQL 用户是否有创建数据库的权限")

if __name__ == '__main__':
    main()
