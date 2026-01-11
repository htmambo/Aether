# SQLite ↔ PostgreSQL 双数据库支持架构设计

## 设计目标

实现一个系统同时支持 SQLite 和 PostgreSQL，支持从 SQLite 无缝迁移到 PostgreSQL，但不建议运行时自动切换。

---

## 1. 核心设计原则

### 1.1 可行性分析

| 方案 | 技术可��性 | 复杂度 | 推荐度 |
|------|-----------|--------|--------|
| ❌ 运行时自动切换 | 低（数据一致性难以保证） | 极高 | 不推荐 |
| ✅ 配置级切换 | 高（已有基础） | 中 | **强烈推荐** |
| ⚠️ 渐进式迁移 | 中 | 高 | 可考虑 |
| ⚠️ 读写分离 | 中 | 高 | 特定场景 |

### 1.2 为什么不推荐运行时自动切换？

**技术障碍**：

1. **数据迁移问题**
   - SQLite → PostgreSQL 不是"切换"，而是"迁移"
   - 需要停机或双写保证数据一致性
   - 大数据量迁移可能需要数小时

2. **Schema 差异**
   - JSONB vs JSON
   - 序列 vs 自增
   - 索引策略不同
   - 约束检查时机不同

3. **连接池管理**
   - SQLite: `NullPool` / `StaticPool`
   - PostgreSQL: `QueuePool`
   - 需要维护两套连接池配置

4. **业务中断风险**
   - 切换过程中的请求如何处理？
   - 切换失败如何回滚？
   - 部分写入如何保证一致性？

---

## 2. 推荐方案：配置级数据库抽象

### 2.1 架构设计

```
┌─────────────────────────────────────────────┐
│           Application Layer                 ���
│  (Business Logic - Database Agnostic)       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         Database Abstraction Layer          │
│  - Unified JSON Type                        │
│  - Dialect-specific PRAGMA config           │
│  - Connection pool abstraction              │
└─────────┬───────────────────┬───────────────┘
          │                   │
    ┌─────▼─────┐       ┌────▼──────┐
    │  SQLite   │       │ PostgreSQL│
    │  Engine   │       │  Engine   │
    └───────────┘       └───────────┘
```

### 2.2 实现方案

#### 方案 A: 环境变量配置（最简单）

```bash
# .env - 开发环境（SQLite）
DATABASE_URL=sqlite:///./data/aether.db
ENVIRONMENT=development

# .env.production - 生产环境（PostgreSQL）
DATABASE_URL=postgresql://user:pass@host:5432/aether
ENVIRONMENT=production
```

**优点**：
- ✅ 零代码修改
- ✅ 部署时选择数据库
- ✅ 降低复杂度

**缺点**：
- ❌ 需要重启应用切换
- ❌ 需要手动迁移数据

#### 方案 B: 工厂模式（推荐）

创建统一的数据库引擎工厂：

```python
# src/database/engine_factory.py
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool, StaticPool, NullPool
from typing import Literal
import os

DatabaseType = Literal["sqlite", "postgresql"]

class DatabaseEngineFactory:
    """数据库引擎工厂 - 支持 SQLite 和 PostgreSQL"""

    @staticmethod
    def create_engine(
        db_url: str,
        environment: str = "production"
    ):
        """创建数据库引擎（自动检测数据库类型）"""

        is_sqlite = db_url.startswith("sqlite:///")
        is_production = environment == "production"

        # 生产环境保护
        if is_production and is_sqlite:
            if not os.getenv("ALLOW_SQLITE_IN_PRODUCTION"):
                raise ValueError(
                    "生产环境使用 SQLite 需要显式设置 ALLOW_SQLITE_IN_PRODUCTION=true"
                )

        if is_sqlite:
            return DatabaseEngineFactory._create_sqlite_engine(db_url)
        else:
            return DatabaseEngineFactory._create_postgres_engine(db_url)

    @staticmethod
    def _create_sqlite_engine(db_url: str):
        """创建 SQLite 引擎"""
        engine = create_engine(
            db_url,
            poolclass=StaticPool,  # SQLite 使用 StaticPool
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # 配置 SQLite PRAGMA
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB
            cursor.execute("PRAGMA busy_timeout=5000")  # 5秒
            cursor.close()

        return engine

    @staticmethod
    def _create_postgres_engine(db_url: str):
        """创建 PostgreSQL 引擎"""
        from src.config import config

        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_timeout=config.db_pool_timeout,
            pool_recycle=config.db_pool_recycle,
            pool_pre_ping=True,
            echo=False,
        )

        return engine

# 使用示例
from src.database.engine_factory import DatabaseEngineFactory

engine = DatabaseEngineFactory.create_engine(
    db_url=config.database_url,
    environment=config.environment
)
```

#### 方案 C: 方言自适应类型（推荐）

创建自动适配两种数据库的类型：

```python
# src/models/universal_types.py
from sqlalchemy import TypeDecorator, JSON
from sqlalchemy.dialects.postgresql import JSONB

class UniversalJSON(TypeDecorator):
    """自动适配 SQLite 和 PostgreSQL 的 JSON 类型"""

    impl = JSON

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # PostgreSQL 使用 JSONB（高性能）
            return dialect.type_descriptor(JSONB())
        else:
            # SQLite 使用 JSON
            return dialect.type_descriptor(JSON())

# 使用示例
from src.models.universal_types import UniversalJSON

class Provider(Base):
    __tablename__ = "providers"

    # 自动适配：PostgreSQL 用 JSONB，SQLite 用 JSON
    proxy = Column(UniversalJSON, nullable=True)
    config = Column(UniversalJSON, nullable=True)
```

### 2.3 Alembic 多数据库支持

```python
# alembic/env.py
from sqlalchemy import event

def run_migrations_online():
    """支持 SQLite 和 PostgreSQL 的在线迁移"""

    connectable = engine_from_config(
        config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    is_sqlite = connectable.dialect.name == 'sqlite'

    # SQLite 特定配置
    if is_sqlite:
        @event.listens_for(connectable, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # SQLite 需要 batch 模式
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()
```

---

## 3. 数据迁移方案

### 3.1 SQLite → PostgreSQL 迁移工具

```python
# scripts/migrate_sqlite_to_postgres.py
import sys
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.models.database import Base
from src.models.universal_types import UniversalJSON
import logging

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """SQLite 到 PostgreSQL 迁移工具"""

    def __init__(self, sqlite_url: str, postgres_url: str):
        self.sqlite_engine = create_engine(sqlite_url)
        self.postgres_engine = create_engine(postgres_url)
        self.SQLiteSession = sessionmaker(bind=self.sqlite_engine)
        self.PostgresSession = sessionmaker(bind=self.postgres_engine)

    def migrate_all(self, batch_size=1000):
        """迁移所有数据"""
        logger.info("开始数据迁移...")

        # 按依赖顺序迁移表
        tables = [
            'users',
            'api_keys',
            'providers',
            'provider_endpoints',
            'provider_api_keys',
            'models',
            'global_models',
            # ... 其他表
        ]

        for table in tables:
            self.migrate_table(table, batch_size)

        logger.info("数据迁移完成！")

    def migrate_table(self, table_name: str, batch_size=1000):
        """迁移单个表"""
        logger.info(f"正在迁移表: {table_name}")

        sqlite_session = self.SQLiteSession()
        postgres_session = self.PostgresSession()

        try:
            # 获取总记录数
            total = sqlite_session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()

            logger.info(f"  总记录数: {total}")

            # 分批迁移
            offset = 0
            migrated = 0

            while offset < total:
                # 从 SQLite 读取
                result = sqlite_session.execute(
                    text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                )

                # 写入 PostgreSQL
                for row in result:
                    # 转换行数据为字典
                    data = dict(row._mapping)

                    # 插入 PostgreSQL
                    postgres_session.execute(
                        text(f"""
                            INSERT INTO {table_name}
                            VALUES ({', '.join([':'] * len(data))})
                        """),
                        data
                    )
                    migrated += 1

                postgres_session.commit()
                offset += batch_size

                logger.info(f"  进度: {migrated}/{total} ({migrated*100//total}%)")

            logger.info(f"  ✅ {table_name} 迁移完成")

        except Exception as e:
            postgres_session.rollback()
            logger.error(f"  ❌ {table_name} 迁移失败: {e}")
            raise

        finally:
            sqlite_session.close()
            postgres_session.close()

    def verify_migration(self):
        """验证迁移结果"""
        logger.info("正在验证数据完整性...")

        sqlite_session = self.SQLiteSession()
        postgres_session = self.PostgresSession()

        tables = ['users', 'api_keys', 'providers', ...]  # 列表同上

        all_ok = True
        for table in tables:
            sqlite_count = sqlite_session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()

            postgres_count = postgres_session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()

            if sqlite_count == postgres_count:
                logger.info(f"  ✅ {table}: {sqlite_count} 条记录")
            else:
                logger.error(
                    f"  ❌ {table}: SQLite={sqlite_count}, "
                    f"PostgreSQL={postgres_count}"
                )
                all_ok = False

        sqlite_session.close()
        postgres_session.close()

        if all_ok:
            logger.info("✅ 数据完整性验证通过！")
        else:
            logger.error("❌ 数据完整性验证失败！")

        return all_ok

# CLI 接口
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 迁移工具")
    parser.add_argument("--sqlite", required=True, help="SQLite 数据库 URL")
    parser.add_argument("--postgres", required=True, help="PostgreSQL 数据库 URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="批处理大小")

    args = parser.parse_args()

    migrator = DatabaseMigrator(args.sqlite, args.postgres)

    try:
        # 执行迁移
        migrator.migrate_all(batch_size=args.batch_size)

        # 验证数据
        if migrator.verify_migration():
            print("\n✅ 迁移成功！")
            print(f"\n下一步:")
            print(f"1. 更新 .env: DATABASE_URL={args.postgres}")
            print(f"2. 重启应用")
            print(f"3. 验证功能正常")
            print(f"4. 备份 SQLite 数据库: cp {args.sqlite} {args.sqlite}.backup")
            sys.exit(0)
        else:
            print("\n❌ 迁移验证失败，请检查日志")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        logger.exception("Migration failed")
        sys.exit(1)
```

**使用方法**：

```bash
# 1. 确保 PostgreSQL 数据库已创建（运行所有迁移）
export DATABASE_URL="postgresql://user:pass@localhost:5432/aether"
alembic upgrade head

# 2. 执行数据迁移
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite "sqlite:///./data/aether.db" \
  --postgres "postgresql://user:pass@localhost:5432/aether" \
  --batch-size 1000

# 3. 更新配置
# 编辑 .env: DATABASE_URL=postgresql://...

# 4. 重启应用
systemctl restart aether

# 5. 验证功能
curl -X GET http://localhost:8084/api/health
```

### 3.2 零停机迁移方案（高级）

对于需要零停机的场景，可以使用双写方案：

```python
# src/services/dual_write_manager.py
from typing import Optional
from sqlalchemy.orm import Session
import threading

class DualWriteManager:
    """双写管理器 - 同时写入 SQLite 和 PostgreSQL（迁移期间使用）"""

    def __init__(self, secondary_session_factory):
        self.secondary_enabled = False
        self.secondary_session_factory = secondary_session_factory
        self.lock = threading.Lock()

    def enable_secondary(self):
        """启用双写模式（迁移准备阶段）"""
        self.secondary_enabled = True
        logger.info("双写模式已启用 - 数据同时写入 SQLite 和 PostgreSQL")

    def disable_secondary(self):
        """禁用双写模式（迁移完成阶段）"""
        self.secondary_enabled = False
        logger.info("双写模式已禁用 - 仅写入 PostgreSQL")

    def write(self, primary_session: Session, operation, *args, **kwargs):
        """执行双写操作"""

        # 主库写入
        result = operation(primary_session, *args, **kwargs)

        # 从库写入（如果启用）
        if self.secondary_enabled:
            try:
                secondary_session = self.secondary_session_factory()
                operation(secondary_session, *args, **kwargs)
                secondary_session.commit()
                secondary_session.close()
            except Exception as e:
                logger.error(f"双写失败: {e}")
                # 不影响主库操作

        return result

# 使用示例（在应用中集成）
dual_write = DualWriteManager(secondary_session_factory=create_postgres_session)

# 迁移阶段 1: 启用双写（数据开始同步到 PostgreSQL）
dual_write.enable_secondary()

# 运行一段时间，确保数据同步完成
# 运行离线数据迁移脚本迁移历史数据

# 迁移阶段 2: 切换主库到 PostgreSQL
# 1. 更新 .env: DATABASE_URL=postgresql://...
# 2. 重启应用
# 3. 验证功能

# 迁移阶段 3: 禁用双写
dual_write.disable_secondary()

# 4. 备份 SQLite 数据库
```

---

## 4. 监控和自动切换建议

### 4.1 数据库性能监控

```python
# src/monitoring/database_monitor.py
from prometheus_client import Gauge, Histogram
import time

# Prometheus 指标
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['db_type', 'operation']
)

db_connection_pool_usage = Gauge(
    'db_connection_pool_usage',
    'Database connection pool usage',
    ['db_type']
)

sqlite_lock_waits = Gauge(
    'sqlite_lock_waits_total',
    'SQLite lock wait count'
)

class DatabaseMonitor:
    """数据库性能监控"""

    def __init__(self, db_type: str):
        self.db_type = db_type

    def track_query(self, operation: str):
        """装饰器：跟踪查询性能"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start
                    db_query_duration.labels(
                        db_type=self.db_type,
                        operation=operation
                    ).observe(duration)
            return wrapper
        return decorator

    def check_sqlite_performance(self):
        """检查 SQLite 性能指标"""
        if self.db_type != 'sqlite':
            return None

        # 检查锁等待次数
        lock_waits = self._get_sqlite_lock_waits()
        sqlite_lock_waits.set(lock_waits)

        # 检查 WAL 文件大小
        wal_size = self._get_wal_file_size()

        return {
            "lock_waits": lock_waits,
            "wal_size_mb": wal_size / 1024 / 1024,
            "recommend_upgrade": lock_waits > 100 or wal_size > 100 * 1024 * 1024
        }

# 使用示例
monitor = DatabaseMonitor(db_type="sqlite")

@monitor.track_query("user_lookup")
def get_user(user_id: str):
    return db.query(User).filter_by(id=user_id).first()
```

### 4.2 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: database_alerts
    rules:
      # SQLite 性能告警
      - alert: SQLitePerformanceDegraded
        expr: rate(sqlite_lock_waits_total[5m]) > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "SQLite 锁等待过多"
          description: "建议迁移到 PostgreSQL"

      # 连接池使用率告警
      - alert: DatabasePoolExhausted
        expr: db_connection_pool_usage{db_type="postgresql"} > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接池接近耗尽"
```

---

## 5. 实施路线图

### 阶段 1: 数据库抽象层（1-2 天）

- [ ] 创建 `DatabaseEngineFactory`
- [ ] 创建 `UniversalJSON` 类型
- [ ] 更新 `src/database/database.py`
- [ ] 更新 `src/models/database.py`（JSONB → UniversalJSON）
- [ ] 配置 Alembic 多数据库支持

### 阶段 2: 测试和验证（1 天）

- [ ] SQLite 环境测试
- [ ] PostgreSQL 环境测试
- [ ] 数据一致性验证
- [ ] 性能基准测试

### 阶段 3: 迁移工具（1-2 天）

- [ ] 开发 `migrate_sqlite_to_postgres.py`
- [ ] 测试迁移工具（开发环境）
- [ ] 编写迁移文档

### 阶段 4: 监控和告警（1 天）

- [ ] 集成 Prometheus 监控
- [ ] 配置告警规则
- [ ] 编写运维文档

### 阶段 5: 生产就绪（持续）

- [ ] 灾难恢复演练
- [ ] 性能优化
- [ ] 文档完善

---

## 6. 最佳实践建议

### 6.1 开发环境

```bash
# .env.development
DATABASE_URL=sqlite:///./data/aether.dev.db
ENVIRONMENT=development

# 启动开发服务器
python -m uvicorn src.main:app --reload
```

### 6.2 生产环境

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@postgres:5432/aether
ENVIRONMENT=production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# 使用 Docker Compose
docker-compose -f docker-compose.yml up -d
```

### 6.3 迁移检查清单

**迁移前**：
- [ ] 备份 SQLite 数据库
- [ ] 备份 PostgreSQL 数据库（如果已有数据）
- [ ] 运行完整性检查
- [ ] 确认磁盘空间充足

**迁移中**：
- [ ] 启用维护模式（可选）
- [ ] 运行迁移脚本
- [ ] 验证数据完整性
- [ ] 更新配置文件
- [ ] 重启应用

**迁移后**：
- [ ] 功能验证测试
- [ ] 性能验证测试
- [ ] 保留 SQLite 备份 7 天
- [ ] 监控错误日志

---

## 7. 常见问题 FAQ

### Q1: 能否运行时自动切换数据库？

**A**: 不推荐。原因：
- 数据迁移需要时间
- 运行时切换无法保证数据一致性
- 连接池配置差异太大
- 需要停止所有请求才能安全切换

**推荐方案**：
- 手动执行迁移工具（计划维护窗口）
- 使用双写方案实现零停机（复杂度高）

### Q2: SQLite 性能瓶颈是什么时候出现？

**A**: 典型指标：
- 并发写入 > 5 req/s
- 数据量 > 100MB
- 锁等待次数 > 100/min
- WAL 文件 > 100MB

**建议**：设置监控告警，提前规划迁移。

### Q3: 如何回滚到 SQLite？

**A**:
```bash
# 1. 停止应用
systemctl stop aether

# 2. 更新配置
# .env: DATABASE_URL=sqlite:///./data/aether.db

# 3. 重启应用
systemctl start aether

# 4. 验证功能
```

注意：PostgreSQL → SQLite 需要开发反向迁移工具。

---

## 8. 总结

### 推荐架构

```
✅ 配置级数据库抽象
   ├─ UniversalJSON（自动适配 JSONB/JSON）
   ├─ DatabaseEngineFactory（统一引擎创建）
   ├─ Alembic 多数据库支持
   └─ 手动迁移工具（migrate_sqlite_to_postgres.py）

❌ 运行时自动切换
   ├─ 数据一致性难以保证
   ├─ 复杂度极高
   └─ 维护成本高
```

### 关键决策

| 决策点 | 推荐 | 理由 |
|--------|------|------|
| 数据库选择 | 开发用 SQLite，生产用 PostgreSQL | 降低部署复杂度 |
| 切换方式 | 手动迁移工具 | 可控、可验证、可回滚 |
| 类型系统 | UniversalJSON | 代码复用，性能最优 |
| 监控 | Prometheus + 告警 | 提前发现问题 |

### 下一步行动

1. ✅ 实现 `UniversalJSON` 类型
2. ✅ 创建 `DatabaseEngineFactory`
3. ✅ 开发迁移工具
4. ✅ 编写部署文档
5. ✅ 配置监控告警

---

**文档版本**: 1.0
**创建时间**: 2026-01-11
**作者**: Claude Code Assistant
