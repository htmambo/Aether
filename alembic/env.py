"""
Alembic 环境配置
用于数据库迁移的运行时环境设置
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 加载 .env 文件（本地开发时需要）
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# 导入所有数据库模型（确保 Alembic 能检测到所有表）
from src.models.database import Base

# Alembic Config 对象
config = context.config

# 从环境变量获取数据库 URL
# 优先使用 DATABASE_URL，否则从 DB_PASSWORD 自动构建（与 docker compose 保持一致）
database_url = os.getenv("DATABASE_URL")
if not database_url:
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aether")
    db_user = os.getenv("DB_USER", "postgres")
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
config.set_main_option("sqlalchemy.url", database_url)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（包含所有表定义）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移

    在离线模式下，不需要连接数据库，
    只生成 SQL 脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 比较列类型变更
        compare_server_default=True,  # 比较默认值变更
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移

    在线模式下，直接连接数据库执行迁移

    支持 SQLite 和 PostgreSQL:
    - SQLite: 启用 PRAGMA（外键、WAL），使用 batch 格式
    - PostgreSQL: 标准模式
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 检测数据库类型
    is_sqlite = connectable.dialect.name == 'sqlite'

    # SQLite PRAGMA 配置
    if is_sqlite:
        from sqlalchemy import event

        @event.listens_for(connectable, "connect")
        def set_sqlite_pragmas(dbapi_conn, connection_record):
            """配置 SQLite PRAGMA"""
            cursor = dbapi_conn.cursor()
            try:
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys=ON")
                # 启用 WAL 模式（提升并发性能）
                # 内存数据库不支持 WAL，捕获异常
                cursor.execute("PRAGMA journal_mode=WAL")
                # 优化同步策略（性能与安全平衡）
                cursor.execute("PRAGMA synchronous=NORMAL")
                # 增大缓存（64MB）
                cursor.execute("PRAGMA cache_size=-64000")
                # 设置锁超时（5秒）
                cursor.execute("PRAGMA busy_timeout=5000")
            except Exception as exc:
                # 内存数据库或只读数据库可能不支持某些 PRAGMA
                # 记录警告但不中断迁移
                import sys
                print(f"Warning: SQLite PRAGMA 配置失败（可能为内存库）: {exc}", file=sys.stderr)
            finally:
                cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 比较列类型变更
            compare_server_default=True,  # 比较默认值变更
            render_as_batch=is_sqlite,  # SQLite 需要 batch 模式
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据模式选择运行方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
