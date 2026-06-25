"""
数据库连接测试工具
用于检查 MySQL 数据库配置和连接是否正常
"""
from pathlib import Path
import sys

REFACTOR_ROOT = Path(__file__).resolve().parents[3]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from core.config import get_config
from infra.db.db_helper import get_db_helper


def test_db_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("数据库连接测试工具")
    print("=" * 60)

    print("\n1. 检查数据库配置...")
    conf = get_config()

    config_items = {
        "MYSQL_HOST": conf.mysql_host,
        "MYSQL_USER": conf.mysql_user,
        "MYSQL_PASSWORD": "***" if conf.mysql_password else None,
        "MYSQL_DATABASE_NAME": conf.mysql_database_name,
    }

    missing_config = []
    for key, value in config_items.items():
        if value:
            print(f"  [OK] {key}: {value}")
        else:
            print(f"  [ERR] {key}: 未配置")
            missing_config.append(key)

    if missing_config:
        print(f"\n错误: 以下配置项缺失: {', '.join(missing_config)}")
        print("请检查项目根目录下的 .env 文件")
        return False

    print("\n2. 测试数据库连接...")
    try:
        db_helper = get_db_helper(
            conf.mysql_host,
            conf.mysql_user,
            conf.mysql_password,
            conf.mysql_database_name,
            conf.mysql_port,
        )

        if db_helper._check_connection():
            print("  [OK] 数据库连接成功！")
        else:
            print("  [ERR] 数据库连接失败")
            return False

    except Exception as e:
        print(f"  [ERR] 连接失败: {e}")
        print("\n可能的原因：")
        print("  1. MySQL 服务未启动")
        print("  2. 数据库配置错误（主机、端口、用户名、密码）")
        print("  3. 数据库不存在")
        print("  4. 防火墙阻止连接")
        print("\n解决方案：")
        print("  1. 启动 MySQL 服务：")
        print("     - Windows: 在服务管理器中启动 MySQL 服务")
        print("     - 或运行: net start MySQL")
        print("  2. 检查 .env 文件中的配置是否正确")
        print("  3. 确认数据库已创建")
        print("  4. 检查 MySQL 用户权限")
        return False

    print("\n3. 测试数据库表创建...")
    try:
        db_helper._ensure_tables_created()
        print("  [OK] 数据库表检查/创建成功！")
    except Exception as e:
        print(f"  [ERR] 表创建失败: {e}")
        return False

    print("\n4. 测试基本数据库操作...")
    try:
        records = db_helper.get_all_interview_records()
        print(f"  [OK] 查询成功，当前有 {len(records)} 条记录")
    except Exception as e:
        print(f"  [ERR] 查询失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("[OK] 所有测试通过！数据库连接正常。")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)
