"""
SQLite → PostgreSQL 数据迁移器

处理 SQLite 特定类型到 PostgreSQL 的转换。
"""

import logging
from typing import Dict, Any
from .base import BaseMigrator

logger = logging.getLogger(__name__)


class SQLiteToPostgresMigrator(BaseMigrator):
    """SQLite 到 PostgreSQL 迁移器"""

    def transform_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 SQLite 数据到 PostgreSQL 格式

        主要转换:
        - JSON → JSONB（自动转换）
        - DateTime 时区处理
        - Boolean 类型
        """
        transformed = {}

        for key, value in row.items():
            # JSON 类型：PostgreSQL 会自动将 JSON 转为 JSONB
            # 无需手动转换，SQLAlchemy 会处理

            # DateTime 类型：确保是时区感知的
            # SQLite 存储为文本，PostgreSQL 会解析

            # Boolean 类型：确保是 True/False 而非 0/1
            if isinstance(value, int) and key.startswith("is_"):
                # 某些情况下 SQLite 可能存储为 0/1
                transformed[key] = bool(value)
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
        description="SQLite → PostgreSQL 数据迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python -m scripts.migration.sqlite_to_postgres \\
      --sqlite "sqlite:///./data/aether.db" \\
      --postgres "postgresql://user:pass@localhost:5432/aether"

  # 指定批处理大小
  python -m scripts.migration.sqlite_to_postgres \\
      --sqlite "sqlite:///./data/aether.db" \\
      --postgres "postgresql://user:pass@localhost:5432/aether" \\
      --batch-size 500

  # 仅验证不迁移
  python -m scripts.migration.sqlite_to_postgres \\
      --sqlite "sqlite:///./data/aether.db" \\
      --postgres "postgresql://user:pass@localhost:5432/aether" \\
      --verify-only
        """
    )

    parser.add_argument(
        "--sqlite",
        required=True,
        help="SQLite 数据库 URL (例如: sqlite:///./data/aether.db)"
    )
    parser.add_argument(
        "--postgres",
        required=True,
        help="PostgreSQL 数据库 URL (例如: postgresql://user:pass@localhost:5432/aether)"
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
    migrator = SQLiteToPostgresMigrator(
        source_url=args.sqlite,
        target_url=args.postgres,
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
            print("  1. 确保 PostgreSQL 数据库已创建并运行所有迁移")
            print("  2. 确保 SQLite 数据库可访问")
            print("  3. 建议备份 SQLite 数据库")
            print("  4. 确保有足够的磁盘空间\n")

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
                print(f"     DATABASE_URL={args.postgres}")
                print(f"  2. 重启应用")
                print(f"  3. 验证功能正常")
                print(f"  4. 备份 SQLite 数据库:")
                print(f"     cp {args.sqlite.replace('sqlite:///', '')} {{}}.backup".format(
                    args.sqlite.replace('sqlite:///', '')
                ))
                print("\n如遇问题，可以回滚到 SQLite:")
                print(f"  DATABASE_URL={args.sqlite}")
                print("=" * 60)
                sys.exit(0)
            else:
                print("\n" + "=" * 60)
                print("❌ 迁移失败！")
                print("=" * 60)
                print("\n请检查:")
                print("  1. PostgreSQL 数据库是否正常运行")
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
