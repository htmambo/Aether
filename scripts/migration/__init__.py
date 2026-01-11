"""
数据库迁移工具包

支持 SQLite 和 PostgreSQL 之间的双向数据迁移。

使用示例:
    # SQLite → PostgreSQL
    python -m scripts.migration.sqlite_to_postgres \
        --sqlite "sqlite:///./data/aether.db" \
        --postgres "postgresql://user:pass@localhost:5432/aether"

    # PostgreSQL → SQLite
    python -m scripts.migration.postgres_to_sqlite \
        --postgres "postgresql://user:pass@localhost:5432/aether" \
        --sqlite "sqlite:///./data/aether.db"
"""

from .base import BaseMigrator, TableMigrationOrder
from .sqlite_to_postgres import SQLiteToPostgresMigrator
from .postgres_to_sqlite import PostgresToSQLiteMigrator

__all__ = [
    "BaseMigrator",
    "TableMigrationOrder",
    "SQLiteToPostgresMigrator",
    "PostgresToSQLiteMigrator",
]
