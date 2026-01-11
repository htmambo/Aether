"""
数据库迁移基���

提供迁移过程中的通用功能和接口定义。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class TableMigrationOrder:
    """表迁移顺序（考虑外键依赖关系）"""

    # 按依赖顺序排列的表列表
    # 父表在前，子表在后（迁移时）
    # 子表在前，父表在后（删除时）
    TABLES = [
        # 独立表（无外键依赖）
        "system_configs",
        "ldap_configs",

        # 用户相关
        "users",
        "user_preferences",
        "user_quotas",

        # 认证相关
        "api_keys",
        "management_tokens",

        # Provider 相关
        "providers",
        "provider_endpoints",
        "provider_api_keys",
        "global_models",
        "models",
        "api_key_provider_mappings",
        "provider_usage_tracking",

        # 公告相关
        "announcements",
        "announcement_reads",

        # 使用记录
        "usage",

        # 审计日志
        "audit_logs",

        # 请求候选
        "request_candidates",

        # 统计数据
        "stats_daily",
        "stats_daily_model",
        "stats_summary",
        "stats_user_daily",
    ]

    @classmethod
    def get_migration_order(cls) -> List[str]:
        """获取迁移顺序（父表 → 子表）"""
        return cls.TABLES

    @classmethod
    def get_deletion_order(cls) -> List[str]:
        """获取删除顺序（子表 → 父表）"""
        return list(reversed(cls.TABLES))


class BaseMigrator(ABC):
    """数据库迁移基类"""

    def __init__(
        self,
        source_url: str,
        target_url: str,
        batch_size: int = 1000,
        verbose: bool = True
    ):
        """
        初始化迁移器

        Args:
            source_url: 源数据库 URL
            target_url: 目标数据库 URL
            batch_size: 批处理大小
            verbose: 是否输出详细日志
        """
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.verbose = verbose

        # 创建引擎
        self.source_engine = self._create_engine(source_url, "source")
        self.target_engine = self._create_engine(target_url, "target")

        # 创建会话工厂
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.TargetSession = sessionmaker(bind=self.target_engine)

        # 统计信息
        self.stats = {
            "total_tables": 0,
            "total_rows": 0,
            "migrated_rows": 0,
            "failed_tables": [],
            "start_time": None,
            "end_time": None,
        }

        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _create_engine(self, url: str, name: str) -> Engine:
        """创建数据库引擎"""
        is_sqlite = url.startswith("sqlite:///")

        if is_sqlite:
            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
            )
            # 启用外键
            from sqlalchemy import event
            @event.listens_for(engine, "connect")
            def set_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        else:
            engine = create_engine(url)

        logger.info(f"创建 {name} 引擎: {url.split('@')[-1] if '@' in url else url}")
        return engine

    @abstractmethod
    def transform_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换行数据（处理数据库特定类型）

        Args:
            table_name: 表名
            row: 原始行数据

        Returns:
            转换后的行数据
        """
        pass

    def get_table_count(self, session: Session, table_name: str) -> int:
        """获取表的记录数"""
        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()

    def get_table_columns(self, engine: Engine, table_name: str) -> List[str]:
        """获取表的列名"""
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return [col['name'] for col in columns]

    def migrate_table(
        self,
        table_name: str,
        source_session: Session,
        target_session: Session
    ) -> Tuple[bool, int]:
        """
        迁移单个表

        Returns:
            (是否成功, 迁移行数)
        """
        logger.info(f"开始迁移表: {table_name}")

        try:
            # 获取总记录数
            total = self.get_table_count(source_session, table_name)

            if total == 0:
                logger.info(f"  表 {table_name} 为空，跳过")
                return True, 0

            logger.info(f"  总记录数: {total:,}")

            # 获取列名
            columns = self.get_table_columns(self.source_engine, table_name)
            columns_str = ", ".join(columns)

            # 分批迁移
            offset = 0
            migrated = 0

            while offset < total:
                # 从源数据库读取
                query = text(f"""
                    SELECT {columns_str}
                    FROM {table_name}
                    ORDER BY id
                    LIMIT :batch_size OFFSET :offset
                """)

                result = source_session.execute(
                    query,
                    {"batch_size": self.batch_size, "offset": offset}
                )

                # 写入目标数据库
                batch_count = 0
                for row in result:
                    # 转换行数据
                    data = self._transform_row_dict(row._mapping, table_name)

                    # 插入目标数据库
                    insert_query = text(f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES ({', '.join([f':{col}' for col in columns])})
                    """)

                    target_session.execute(insert_query, data)
                    batch_count += 1
                    migrated += 1

                # 提交批次
                target_session.commit()

                # 进度日志
                progress = migrated * 100 // total
                logger.info(f"  进度: {migrated:,}/{total:,} ({progress}%)")

                offset += self.batch_size

            logger.info(f"  ✅ {table_name} 迁移完成: {migrated:,} 条记录")
            return True, migrated

        except Exception as e:
            target_session.rollback()
            logger.error(f"  ❌ {table_name} 迁移失败: {e}")
            return False, 0

    def _transform_row_dict(self, row_dict: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """转换行数据（内部方法）"""
        return self.transform_row(table_name, row_dict)

    def migrate_all(self) -> bool:
        """迁移所有表"""
        logger.info("=" * 60)
        logger.info("开始数据迁移")
        logger.info("=" * 60)
        logger.info(f"源数据库: {self.source_url}")
        logger.info(f"目标数据库: {self.target_url}")
        logger.info(f"批处理大小: {self.batch_size}")
        logger.info("-" * 60)

        self.stats["start_time"] = time.time()

        # 创建会话
        source_session = self.SourceSession()
        target_session = self.TargetSession()

        try:
            # 按依赖顺序迁移
            tables = TableMigrationOrder.get_migration_order()

            for table in tables:
                # 检查源表是否存在
                if not self._table_exists(source_session, table):
                    logger.warning(f"表 {table} 不存在，跳过")
                    continue

                # 检查目标表是否存在
                if not self._table_exists(target_session, table):
                    logger.error(f"目标表 {table} 不存在，请先运行迁移")
                    self.stats["failed_tables"].append(table)
                    continue

                # 迁移表
                success, count = self.migrate_table(
                    table,
                    source_session,
                    target_session
                )

                self.stats["total_tables"] += 1
                if success:
                    self.stats["total_rows"] += count
                    self.stats["migrated_rows"] += count
                else:
                    self.stats["failed_tables"].append(table)

            self.stats["end_time"] = time.time()

            # 输出统计
            self._print_stats()

            return len(self.stats["failed_tables"]) == 0

        except Exception as e:
            logger.error(f"迁移过程发生错误: {e}")
            logger.exception("详细错误信息")
            return False

        finally:
            source_session.close()
            target_session.close()

    def verify_migration(self) -> bool:
        """验证迁移结果"""
        logger.info("=" * 60)
        logger.info("开始验证数据完整性")
        logger.info("=" * 60)

        source_session = self.SourceSession()
        target_session = self.TargetSession()

        try:
            tables = TableMigrationOrder.get_migration_order()
            all_ok = True

            for table in tables:
                # 检查表是否存在
                source_exists = self._table_exists(source_session, table)
                target_exists = self._table_exists(target_session, table)

                if not source_exists and not target_exists:
                    continue

                if source_exists != target_exists:
                    logger.error(f"表 {table} 存在性不一致")
                    all_ok = False
                    continue

                # 比较记录数
                source_count = self.get_table_count(source_session, table)
                target_count = self.get_table_count(target_session, table)

                if source_count == target_count:
                    logger.info(
                        f"  ✅ {table}: {source_count:,} 条记录"
                    )
                else:
                    logger.error(
                        f"  ❌ {table}: 源={source_count:,}, "
                        f"目标={target_count:,}"
                    )
                    all_ok = False

            logger.info("-" * 60)
            if all_ok:
                logger.info("✅ 数据完整性验证通过！")
            else:
                logger.error("❌ 数据完整性验证失败！")

            return all_ok

        finally:
            source_session.close()
            target_session.close()

    def _table_exists(self, session: Session, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            return True
        except Exception:
            return False

    def _print_stats(self):
        """打印统计信息"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        mins, secs = divmod(int(duration), 60)

        logger.info("=" * 60)
        logger.info("迁移统计")
        logger.info("=" * 60)
        logger.info(f"总表数: {self.stats['total_tables']}")
        logger.info(f"成功迁移: {self.stats['migrated_rows']:,} 条记录")
        logger.info(f"耗时: {mins} 分 {secs} 秒")

        if self.stats["migrated_rows"] > 0:
            rows_per_sec = self.stats["migrated_rows"] / duration
            logger.info(f"速度: {rows_per_sec:.1f} 条/秒")

        if self.stats["failed_tables"]:
            logger.error(f"失败的表: {', '.join(self.stats['failed_tables'])}")

        logger.info("=" * 60)

    def cleanup(self):
        """清理资源"""
        try:
            self.source_engine.dispose()
            self.target_engine.dispose()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"清理资源时发生错误: {e}")
