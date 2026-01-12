"""
数据库引擎工厂

提供统一的数据库引擎创建接口，自动适配 SQLite 和 PostgreSQL。

特性:
- 自动检测数据库类型（通过 URL）
- SQLite: StaticPool + PRAGMA 优化（外键、WAL、缓存等）
- PostgreSQL: QueuePool + 连接池管理
- 生产环境保护：默认禁止 SQLite
- 支持同步和异步引擎
"""

import logging
from typing import Any, Union

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import QueuePool, StaticPool


logger = logging.getLogger(__name__)


class DatabaseEngineFactory:
    """
    数据库引擎工厂

    根据数据库 URL 自动创建优化的引擎配置：

    SQLite 配置:
    - 使用 StaticPool（单连接模式）
    - 启用外键约束
    - 启用 WAL 模式（提升并发性能）
    - 优化缓存和同步策略

    PostgreSQL 配置:
    - 使用 QueuePool（连接池）
    - 支持自定义连接池参数
    - 自动重连和连接回收

    使用示例:
        from src.database.engine_factory import DatabaseEngineFactory

        # 同步引擎
        engine = DatabaseEngineFactory.create_engine(
            url="sqlite:///./data/aether.db",
            environment="development"
        )

        # 异步引擎
        async_engine = DatabaseEngineFactory.create_async_engine(
            url="postgresql://user:pass@localhost:5432/aether",
            environment="production"
        )
    """

    # SQLite PRAGMA 配置
    SQLITE_PRAGMAS = {
        "foreign_keys": "ON",           # 启用外键约束
        "journal_mode": "WAL",          # 使用 WAL 模式（提升并发）
        "journal_size_limit": 67108864, # 限制 WAL 文件体积（64MB），避免长期膨胀
        "synchronous": "NORMAL",        # 性能模式（安全性与性能平衡）
        "cache_size": -64000,           # 64MB 负值表示 KB
        "busy_timeout": 5000,           # 5秒锁超时（毫秒）
        "temp_store": "MEMORY",         # 临时表在内存中
    }

    @classmethod
    def create_engine(
        cls,
        url: Union[str, URL],
        environment: str = "production",
        allow_sqlite_in_production: bool = False,
        **kwargs: Any,
    ) -> Engine:
        """
        创建同步数据库引擎

        Args:
            url: 数据库 URL
                - SQLite: sqlite:///./data/aether.db
                - PostgreSQL: postgresql://user:pass@host:5432/aether
            environment: 环境类型（development/production）
            allow_sqlite_in_production: 是否允许生产环境使用 SQLite
            **kwargs: 其他 create_engine 参数

        Returns:
            SQLAlchemy Engine 实例

        Raises:
            ValueError: 生产环境使用 SQLite 且未显式允许
            RuntimeError: 不支持的数据库类型

        Example:
            >>> engine = DatabaseEngineFactory.create_engine(
            ...     url="sqlite:///./data/aether.db",
            ...     environment="development"
            ... )
        """
        # 规范化 URL
        if isinstance(url, str):
            url = make_url(url)

        is_sqlite = url.drivername.startswith("sqlite")
        is_production = environment == "production"

        # 生产环境保护
        if is_production and is_sqlite and not allow_sqlite_in_production:
            raise ValueError(
                "生产环境使用 SQLite 需要显式设置 allow_sqlite_in_production=True。"
                "SQLite 不适合生产环境，建议使用 PostgreSQL。"
            )

        # 创建引擎
        if is_sqlite:
            return cls._create_sqlite_engine(url, **kwargs)
        else:
            return cls._create_postgres_engine(url, **kwargs)

    @classmethod
    def create_async_engine(
        cls,
        url: Union[str, URL],
        environment: str = "production",
        allow_sqlite_in_production: bool = False,
        **kwargs: Any,
    ) -> AsyncEngine:
        """
        创建异步数据库引擎

        Args:
            url: 数据库 URL
                - SQLite: sqlite:///./data/aether.db
                - PostgreSQL: postgresql://user:pass@host:5432/aether
            environment: 环境类型（development/production）
            allow_sqlite_in_production: 是否允许生产环境使用 SQLite
            **kwargs: 其他 create_async_engine 参数

        Returns:
            SQLAlchemy AsyncEngine 实例

        Raises:
            ValueError: 生产环境使用 SQLite 且未显式允许
            RuntimeError: 不支持的数据库类型

        Example:
            >>> async_engine = DatabaseEngineFactory.create_async_engine(
            ...     url="postgresql://user:pass@host:5432/aether",
            ...     environment="production"
            ... )
        """
        # 规范化 URL
        if isinstance(url, str):
            url = make_url(url)

        is_sqlite = url.drivername.startswith("sqlite")
        is_production = environment == "production"

        # 生产环境保护
        if is_production and is_sqlite and not allow_sqlite_in_production:
            raise ValueError(
                "生产环境使用 SQLite 需要显式设置 allow_sqlite_in_production=True。"
                "SQLite 不适合生产环境，建议使用 PostgreSQL。"
            )

        # 创建异步引擎
        if is_sqlite:
            return cls._create_sqlite_async_engine(url, **kwargs)
        else:
            return cls._create_postgres_async_engine(url, **kwargs)

    @classmethod
    def _create_sqlite_engine(cls, url: URL, **kwargs: Any) -> Engine:
        """创建 SQLite 同步引擎"""
        engine = create_engine(
            str(url),
            poolclass=StaticPool,  # SQLite 使用 StaticPool
            connect_args={"check_same_thread": False},  # 允许多线程
            echo=kwargs.get("echo", False),
            **{k: v for k, v in kwargs.items() if k != "echo"},  # 透传其他参数
        )

        # 应用 PRAGMA 配置
        cls._apply_sqlite_pragmas(engine, url.database)

        logger.info(f"创建 SQLite 同步引擎: {url.database}")
        return engine

    @classmethod
    def _create_sqlite_async_engine(cls, url: URL, **kwargs: Any) -> AsyncEngine:
        """创建 SQLite 异步引擎"""
        # 确保使用 aiosqlite 驱动
        if "+" not in url.drivername:
            url = url.set(drivername="sqlite+aiosqlite")

        engine = create_async_engine(
            str(url),
            poolclass=StaticPool,  # SQLite 使用 StaticPool
            connect_args={"check_same_thread": False},
            echo=kwargs.get("echo", False),
            **{k: v for k, v in kwargs.items() if k != "echo"},  # 透传其他参数
        )

        # 应用 PRAGMA 配置（应用到 sync_engine）
        cls._apply_sqlite_pragmas(engine.sync_engine, url.database)

        logger.info(f"创建 SQLite 异步引擎: {url.database}")
        return engine

    @classmethod
    def _create_postgres_engine(cls, url: URL, **kwargs: Any) -> Engine:
        """创建 PostgreSQL 同步引擎"""
        # 延迟导入以避免循环依赖
        from src.config import config

        # 不需要手动指定驱动，SQLAlchemy 会自动选择 psycopg2
        # if "+" not in url.drivername:
        #     url = url.set(drivername="postgresql+psycopg2")

        # 重建原始 URL 字符串（不隐藏密码）
        # str(url) 会将密码隐藏为 ***，所以需要手动构建
        if url.password:
            url_str = f"{url.drivername}://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}"
        else:
            url_str = f"{url.drivername}://{url.username}@{url.host}:{url.port}/{url.database}"

        engine = create_engine(
            url_str,
            poolclass=QueuePool,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_timeout=config.db_pool_timeout,
            pool_recycle=config.db_pool_recycle,
            pool_pre_ping=True,
            echo=kwargs.get("echo", False),
            **{k: v for k, v in kwargs.items() if k != "echo"},  # 透传其他参数
        )

        logger.info(f"创建 PostgreSQL 同步引擎: {url.host}:{url.port}")
        return engine

    @classmethod
    def _create_postgres_async_engine(cls, url: URL, **kwargs: Any) -> AsyncEngine:
        """创建 PostgreSQL 异步引擎"""
        # 延迟导入以避免循环依赖
        from src.config import config

        # 确保使用 asyncpg 驱动
        if "+" not in url.drivername:
            url = url.set(drivername="postgresql+asyncpg")

        engine = create_async_engine(
            str(url),
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_timeout=config.db_pool_timeout,
            pool_recycle=config.db_pool_recycle,
            pool_pre_ping=True,
            echo=kwargs.get("echo", False),
            **{k: v for k, v in kwargs.items() if k != "echo"},  # 透传其他参数
        )

        logger.info(f"创建 PostgreSQL 异步引擎: {url.host}:{url.port}")
        return engine

    @classmethod
    def _apply_sqlite_pragmas(cls, engine: Engine, db_name: str = None) -> None:
        """
        应用 SQLite PRAGMA 配置

        配置项:
        - foreign_keys: ON（启用外键约束）
        - journal_mode: WAL（提升并发性能）
        - synchronous: NORMAL（性能与安全平衡）
        - cache_size: -64000（64MB 缓存）
        - busy_timeout: 5000（5秒锁超时）
        - temp_store: MEMORY（临时表在内存）

        Args:
            engine: SQLAlchemy 引擎
            db_name: 数据库名称（用于日志）
        """
        @event.listens_for(engine, "connect")
        def set_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            try:
                # 检查是否为内存数据库（不支持 WAL）
                is_memory = db_name == ":memory:" or db_name is None

                for pragma_name, pragma_value in cls.SQLITE_PRAGMAS.items():
                    # 内存数据库不支持 WAL，跳过
                    if is_memory and pragma_name == "journal_mode":
                        continue

                    cursor.execute(f"PRAGMA {pragma_name}={pragma_value}")

                logger.debug(
                    f"SQLite PRAGMA 配置已应用: "
                    f"{cls.SQLITE_PRAGMAS if not is_memory else 'skipped WAL for :memory:'}"
                )
            except Exception as exc:
                # 内存数据库或只读数据库可能不支持某些 PRAGMA
                # 记录警告但不中断引擎创建
                logger.warning(f"SQLite PRAGMA 配置失败（可能为内存库或只读库）: {exc}")
            finally:
                cursor.close()

    @classmethod
    def get_database_type(cls, url: Union[str, URL]) -> str:
        """
        获取数据库类型

        Args:
            url: 数据库 URL

        Returns:
            'sqlite' 或 'postgresql'

        Raises:
            ValueError: 不支持的数据库类型
        """
        if isinstance(url, str):
            url = make_url(url)

        backend = url.get_backend_name()

        if backend == "sqlite":
            return "sqlite"
        elif backend in ("postgresql", "postgres"):
            return "postgresql"
        else:
            raise ValueError(
                f"不支持的数据库类型: {backend}。"
                f"本项目仅支持 SQLite 和 PostgreSQL。"
            )
