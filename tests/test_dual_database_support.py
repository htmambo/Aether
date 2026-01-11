"""
双数据库支持测试脚本

验证 SQLite 和 PostgreSQL 的配置和功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_sqlite_environment():
    """测试 SQLite 环境配置"""
    print("\n" + "=" * 60)
    print("测试 1: SQLite 环境配置")
    print("=" * 60)

    # 设置 SQLite 环境变量
    os.environ["DATABASE_URL"] = "sqlite:///./test_aether.db"
    os.environ["ENVIRONMENT"] = "development"

    try:
        from src.config import config
        from src.database.engine_factory import DatabaseEngineFactory
        from src.models.database import Base

        # 创建引擎
        engine = DatabaseEngineFactory.create_engine(
            url=config.database_url,
            environment=config.environment
        )

        print(f"✅ 数据库 URL: {config.database_url}")
        print(f"✅ 环境类型: {config.environment}")
        print(f"✅ 数据库类型: {DatabaseEngineFactory.get_database_type(config.database_url)}")
        print(f"✅ 引擎创建成功")

        # 清理
        engine.dispose()
        os.remove("./test_aether.db")

        return True

    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_postgres_environment():
    """测试 PostgreSQL 环境配置"""
    print("\n" + "=" * 60)
    print("测试 2: PostgreSQL 环境配置")
    print("=" * 60)

    # 设置 PostgreSQL 环境变量
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/aether"

    try:
        from src.config import config
        from src.database.engine_factory import DatabaseEngineFactory

        # 验证数据库类型
        db_type = DatabaseEngineFactory.get_database_type(config.database_url)

        print(f"✅ 数据库 URL: {config.database_url}")
        print(f"✅ 数据库类型: {db_type}")

        return True

    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_universal_json_type():
    """测试 UniversalJSON 类型"""
    print("\n" + "=" * 60)
    print("测试 3: UniversalJSON 类型")
    print("=" * 60)

    try:
        from src.models.universal_types import UniversalJSON
        from sqlalchemy import create_engine
        from sqlalchemy.dialects import postgresql, sqlite

        # 创建类型实例
        json_type = UniversalJSON()

        # 测试 PostgreSQL 方言
        pg_dialect = postgresql.dialect()
        impl = json_type.load_dialect_impl(pg_dialect)
        print(f"✅ PostgreSQL 实现: {type(impl).__name__}")

        # 测试 SQLite 方言
        sqlite_dialect = sqlite.dialect()
        impl = json_type.load_dialect_impl(sqlite_dialect)
        print(f"✅ SQLite 实现: {type(impl).__name__}")

        # 测试值处理
        test_data = {"key": "value", "nested": {"a": 1}}
        processed = json_type.process_bind_param(test_data, pg_dialect)
        print(f"✅ 值处理: {processed}")

        return True

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_production_protection():
    """测试生产环境保护"""
    print("\n" + "=" * 60)
    print("测试 4: 生产环境保护")
    print("=" * 60)

    try:
        from src.database.engine_factory import DatabaseEngineFactory

        # 测试 1: 生产环境 + SQLite (应该失败)
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        os.environ["ENVIRONMENT"] = "production"
        os.environ["ALLOW_SQLITE_IN_PRODUCTION"] = "false"

        try:
            from src.config import config
            engine = DatabaseEngineFactory.create_engine(
                url=config.database_url,
                environment=config.environment,
                allow_sqlite_in_production=config.allow_sqlite_in_production
            )
            print("❌ 应该抛出异常但没有")
            return False
        except ValueError as e:
            print(f"✅ 正确阻止 SQLite 在生产环境: {e}")

        # 测试 2: 生产环境 + SQLite + 显式允许 (应该成功)
        os.environ["ALLOW_SQLITE_IN_PRODUCTION"] = "true"

        try:
            from importlib import reload
            from src.config import config as config_module
            reload(config_module)

            engine = DatabaseEngineFactory.create_engine(
                url="sqlite:///./test.db",
                environment="production",
                allow_sqlite_in_production=True
            )
            print("✅ 显式允许后可以使用 SQLite")
            engine.dispose()
            os.remove("./test.db")

        except Exception as e:
            print(f"❌ 显式允许后仍然失败: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("双数据库支持功能测试")
    print("=" * 60)

    results = {
        "SQLite 环境配置": test_sqlite_environment(),
        "PostgreSQL 环境配置": test_postgres_environment(),
        "UniversalJSON 类型": test_universal_json_type(),
        "生产环境保护": test_production_protection(),
    }

    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
