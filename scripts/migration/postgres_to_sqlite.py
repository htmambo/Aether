"""
PostgreSQL → SQLite 数据迁移器

处理 PostgreSQL 特定类型到 SQLite 的转换。
"""

import logging
from typing import Dict, Any
from .base import BaseMigrator

logger = logging.getLogger(__name__)


class PostgresToSQLiteMigrator(BaseMigrator):
    """PostgreSQL 到 SQLite 迁移器"""

    def transform_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 PostgreSQL 数据到 SQLite 格式

        主要转换:
        - JSONB → JSON（自动转换）
        - Dict → JSON 字符串（SQLite 需要序列化）
        - DateTime 时区处理（转为 UTC 文本）
        - Array 类型（转为 JSON 数组）
        """
        import json

        transformed = {}

        for key, value in row.items():
            # JSONB → JSON: SQLAlchemy 会自动转换
            # PostgreSQL 的 JSONB 会转为 JSON 格式

            # DateTime: 确保转换为 ISO 8601 格式字符串
            if hasattr(value, 'isoformat'):
                # datetime 对象
                if value.tzinfo is not None:
                    # 有时区信息，转为 UTC
                    value = value.astimezone(None).isoformat()
                else:
                    # 无时区信息，直接转换
                    value = value.isoformat()
                transformed[key] = value
            # Dict 类型（JSONB/JSON 字段）：转为 JSON 字符串
            # SQLite 不支持直接绑定 dict 对象，必须序列化为 JSON 字符串
            elif isinstance(value, dict):
                transformed[key] = json.dumps(value)
            # Array 类型（PostgreSQL 特有）
            elif isinstance(value, list):
                # 转为 JSON 字符串
                transformed[key] = json.dumps(value)
            # Boolean 类型：确保是 True/False
            elif isinstance(value, bool):
                transformed[key] = value
            # None 值
            elif value is None:
                transformed[key] = None
            # 其他类型（int, float, str 等）
            else:
                transformed[key] = value

        return transformed


def main():
    """CLI 入口"""
    import argparse
    import sys
    import os

    # 添加项目根目录到 Python 路径
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, script_dir)

    parser = argparse.ArgumentParser(
        description="PostgreSQL → SQLite 数据迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python -m scripts.migration.postgres_to_sqlite \\
      --postgres "postgresql://user:pass@localhost:5432/aether" \\
      --sqlite "sqlite:///./data/aether.db"

  # 指定批处理大小
  python -m scripts.migration.postgres_to_sqlite \\
      --postgres "postgresql://user:pass@localhost:5432/aether" \\
      --sqlite "sqlite:///./data/aether.db" \\
      --batch-size 500

  # 仅验证不迁移
  python -m scripts.migration.postgres_to_sqlite \\
      --postgres "postgresql://user:pass@localhost:5432/aether" \\
      --sqlite "sqlite:///./data/aether.db" \\
      --verify-only
        """
    )

    parser.add_argument(
        "--postgres",
        required=True,
        help="PostgreSQL 数据库 URL (例如: postgresql://user:pass@localhost:5432/aether)"
    )
    parser.add_argument(
        "--sqlite",
        required=True,
        help="SQLite 数据库 URL (例如: sqlite:///./data/aether.db)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="批处理大小 (默认: 1000)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证数据完整性，不执行迁移"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="迁移后不验证数据完整性"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="减少日志输出"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳过确认提示，直接执行迁移"
    )

    args = parser.parse_args()

    # 创建迁移器
    migrator = PostgresToSQLiteMigrator(
        source_url=args.postgres,
        target_url=args.sqlite,
        batch_size=args.batch_size,
        verbose=not args.quiet
    )

    try:
        if args.verify_only:
            # 仅验证
            success = migrator.verify_migration()
            if success:
                print("\n✅ 数据完整性验证通过")
                sys.exit(0)
            else:
                print("\n❌ 数据完整性验证失败")
                sys.exit(1)
        else:
            # 执行迁移
            print("\n📋 迁移前检查清单:")
            print("  1. 确保 SQLite 数据库文件可创建")
            print("  2. 确保 PostgreSQL 数据库可访问")
            print("  3. 建议备份 PostgreSQL 数据库")
            print("  4. 注意: SQLite 性能不如 PostgreSQL\n")

            print("⚠️  警告:")
            print("  SQLite 不适合高并发或大数据量场景")
            print("  建议仅用于开发/测试环境\n")

            # 如果没有 --yes 参数，请求确认
            if not args.yes:
                response = input("确认开始迁移？(yes/no): ")
                if response.lower() not in ["yes", "y"]:
                    print("已取消迁移")
                    sys.exit(0)

            success = migrator.migrate_all()

            if success and not args.no_verify:
                print("\n正在验证数据完整性...")
                verify_success = migrator.verify_migration()
                success = verify_success

            if success:
                print("\n" + "=" * 60)
                print("✅ 迁移成功完成！")
                print("=" * 60)
                print("\n下一步:")
                print(f"  1. 更新 .env 配置:")
                print(f"     DATABASE_URL={args.sqlite}")
                print(f"  2. 重启应用")
                print(f"  3. 验证功能正常")
                print(f"  4. 考虑备份 SQLite 数据库")
                print("\n⚠️  注意:")
                print("  SQLite 不适合生产环境使用")
                print("  如需生产环境，请使用 PostgreSQL")
                print("=" * 60)
                sys.exit(0)
            else:
                print("\n" + "=" * 60)
                print("❌ 迁移失败！")
                print("=" * 60)
                print("\n请检查:")
                print("  1. SQLite 文件路径是否可写")
                print("  2. 数据库连接是否正确")
                print("  3. 日志中的详细错误信息")
                print("\n修复问题后可以重新运行迁移脚本")
                print("=" * 60)
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  迁移被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        logger.exception("详细错误信息")
        sys.exit(1)
    finally:
        migrator.cleanup()


if __name__ == "__main__":
    main()
