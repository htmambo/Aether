# SQLite 数据库可行性分析报告

## 执行摘要

**结论**: ⚠️ **有条件推荐** - 仅适用于开发/测试环境或单用户低并发场景

**关键发现**:
- 项目已部分支持 SQLite（包含 aiosqlite 依赖和 URL 转换逻辑）
- 存在 PostgreSQL 特定特性（JSONB、GIN 索引、高级 SQL 函数）导致迁移成本中等
- 小规模场景（< 10 req/s，数据 < 100MB）技术可行，但需接受功能限制
- 生产环境当前强制使用 PostgreSQL，需显式放宽限制

**预计迁移工作量**: 9.5-11.5 开发小时（约 1 个工作日）

---

## 1. 现状调研

### 1.1 当前数据库技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 数据库 | PostgreSQL | 15 |
| ORM | SQLAlchemy | 2.0.43 |
| 迁移工具 | Alembic | 1.16.5 |
| 同步驱动 | psycopg2-binary | 2.9.10 |
| 异步驱动 | asyncpg | 0.29.0 |
| SQLite 驱动 | aiosqlite | 0.20.0 ✅ (已安装) |

### 1.2 数据模型统计

| 模型类型 | 数量 | 主要字段 |
|---------|------|---------|
| 核心业务表 | 18+ | User, ApiKey, Provider, Usage, GlobalModel 等 |
| 统计表 | 4 | StatsDaily, StatsDailyModel, StatsSummary, StatsUserDaily |
| 审计日志表 | 1 | AuditLog |
| 辅助表 | 8+ | LDAPConfig, Announcement, ManagementToken, RequestCandidate 等 |

### 1.3 PostgreSQL 特性使用情况

#### JSONB 类型（3 处）
- `src/models/database.py:560` - `Provider.proxy`
- `src/models/database.py:621` - `ProviderEndpoint.proxy`
- `src/models/database.py:709` - `GlobalModel.config`

#### JSON 类型（广泛使用）
- `User.allowed_providers`, `User.allowed_api_formats`, `User.allowed_models`
- `ApiKey.allowed_providers`, `ApiKey.force_capabilities`
- `ProviderAPIKey.api_formats`, `ProviderAPIKey.capabilities`
- `ManagementToken.allowed_ips`
- 等共计 20+ 个字段

#### 时区感知时间戳
- 全部时间字段使用 `DateTime(timezone=True)`
- SQLite 无原生时区支持，需应用层处理

#### 枚举类型
- `UserRole`, `AuthSource`, `ProviderBillingType`
- 配置 `create_type=False`，SQLite 兼容性较好

#### 连接池配置
- 同步引擎: `QueuePool` + 连接池参数
- 异步引擎: `AsyncAdaptedQueuePool`
- SQLite 需使用 `NullPool` 或 `StaticPool`

#### 外键级联
- 广泛使用 `ondelete="CASCADE"` 和 `ondelete="SET NULL"`
- SQLite 需启用 `PRAGMA foreign_keys=ON`

---

## 2. SQLite 适用性技术评估

### 2.1 特性兼容性矩阵

| PostgreSQL 特性 | SQLite 支持 | 兼容性 | 备注 |
|----------------|-------------|--------|------|
| JSONB 类型 | ❌ | 不兼容 | 需改为 JSON（性能下降） |
| JSON 类型 | ✅ | 兼容 | 功能减弱，无 GIN 索引 |
| DateTime(tz=True) | ⚠️ | 部分兼容 | 存为文本，无时区校验 |
| Enum(create_type=False) | ✅ | 兼容 | 退化为字符串 + CHECK |
| QueuePool | ❌ | 不兼容 | 需改用 NullPool/StaticPool |
| 外键级联 | ✅ | 需配置 | 需 `PRAGMA foreign_keys=ON` |
| GIN 索引 | ❌ | 不兼容 | 影响 JSON 查询性能 |
| ALTER TABLE | ⚠️ | 有限支持 | 部分操作需重建表 |
| Alembic batch | ⚠️ | 有限支持 | 需 `render_as_batch=True` |
| 并发写入 | ⚠️ | 有限 | 单写入者 + WAL 模式 |
| 全文搜索 | ⚠️ | 需配置 | 需启用 FTS5，语法不同 |
| 窗口函数 | ✅ | 支持 | SQLite 3.25+ |
| CTE (WITH) | ✅ | 支持 | 基本支持 |
| 行级锁 | ✅ | ❌ | SQLite 无行级锁，仅数据库级锁 |
| SELECT FOR UPDATE | ✅ | ❌ | 需应用层互斥机制 |

### 2.2 性能对比（小规模场景 - 假设数据）

> **注意**: 以下数据为假设性估算，实际性能需通过基准测试验证。

| 指标 | PostgreSQL | SQLite (WAL) | 备注 |
|------|-----------|--------------|------|
| 读取性能 | 高 | 中等 | 小数据量差异不大 |
| 写入性能 | 高 | 低 | 单写入者限制 |
| 并发连接 | 100+ | 1 写 / 多读 | 文件锁限制 |
| JSON 查询 | 快（GIN） | 慢（全表扫描） | 显著差异 |
| 启动时间 | 秒级 | 毫秒级 | SQLite 优势 |
| 内存占用 | 100MB+ | < 10MB | SQLite 优势 |
| 数据文件 | 需要 | 单文件 | SQLite 优势 |

### 2.3 潜在问题与风险

#### 🔴 高风险

1. **JSONB 性能骤降**
   - 影响: `Provider.proxy`, `ProviderEndpoint.proxy`, `GlobalModel.config` 查询
   - 风险: 复杂 JSON 查询从毫秒级降至秒级
   - 缓解: 改用应用层过滤或添加表达式索引

2. **连接池不兼容**
   - 影响: 当前 `QueuePool` 配置在 SQLite 下会失败
   - 风险: 多进程环境会导致 "database is locked" 错误
   - 缓解: 改用 `NullPool` + WAL 模式 + 限制 worker 数量

3. **外键级联失效**
   - 影响: 所有 `ondelete="CASCADE"` 和 `SET NULL` 操作
   - 风险: 产生孤儿数据，违反数据完整性
   - 缓解: 强制启用 `PRAGMA foreign_keys=ON`

#### 🟡 中等风险

4. **Alembic 迁移脚本不兼容**
   - 影响: 需逐个审查现有迁移，凡包含列类型变更/并发索引/ENUM 变更等均需改写或重建表
   - 风险: 迁移失败或需要手动重建表
   - 缓解: 审查并改写迁移脚本，或创建 SQLite 专用 baseline

5. **时区时间戳处理**
   - 影响: 时间范围查询和时区转换
   - 风险: 混用时区导致数据错误
   - 缓解: 应用层统一使用 UTC，禁止存储 naive datetime

6. **生产环境保护绕过**
   - 影响: 可能误将 SQLite 用于生产环境
   - 风险: 性能瓶颈和数据损坏风险
   - 缓解: 显式配置开关并记录警告日志

7. **无行级锁 / SELECT FOR UPDATE**
   - 影响: 依赖数据库级悲观锁的业务逻辑
   - 风险: 并发冲突和死锁
   - 缓解: 避免使用 `SELECT FOR UPDATE`，改用应用层互斥机制

8. **备份和维护缺失**
   - 影响: 数据丢失风险
   - 风险: 缺少 WAL checkpoint、vacuum 策略
   - 缓解: 实现定期备份脚本，配置 WAL 自动 checkpoint

5. **时区时间戳处理**
   - 影响: 时间范围查询和时区转换
   - 风险: 混用时区导致数据错误
   - 缓解: 应用层统一使用 UTC，禁止存储 naive datetime

6. **生产环境保护绕过**
   - 影响: 可能误将 SQLite 用于生产环境
   - 风险: 性能瓶颈和数据损坏风险
   - 缓解: 显式配置开关并记录警告日志

#### 🟢 低风险

7. **枚举类型**
   - 当前配置 `create_type=False`，兼容性良好
   - 无需额外处理

---

## 3. 迁移成本评估

### 3.1 需要修改的文件清单

#### 核心代码修改

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `src/models/database.py` | JSONB → JSON，检查 Enum 配置 | 1.5h |
| `src/database/database.py` | 添加 SQLite 分支配置（NullPool, PRAGMA） | 2h |
| `src/config/settings.py` | 添加 SQLite 开关配置 | 0.5h |
| `alembic/env.py` | 添加 SQLite 分支支持，启用外键 | 1h |

#### 迁移脚本修改

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `alembic/versions/*.py` | 审查并改写 PostgreSQL 特定语法 | 3-5h |

#### 文档和测试

| 任务 | 工作量 |
|------|--------|
| 添加 SQLite 模式文档 | 1h |
| 端到端测试验证 | 1h |
| **总计** | **9.5-11.5h** |

### 3.2 关键修改点详解

#### 修改 1: 数据库引擎配置

**位置**: `src/database/database.py:106-147`

**当前代码**:
```python
def _ensure_engine() -> Engine:
    DATABASE_URL = config.database_url

    # 生产环境保护
    if is_production and not DATABASE_URL.startswith("postgresql://"):
        raise ValueError("生产环境只支持 PostgreSQL 数据库")

    _engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,  # ❌ SQLite 不兼容
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        # ...
    )
```

**建议修改**:
```python
def _ensure_engine() -> Engine:
    DATABASE_URL = config.database_url

    is_sqlite = DATABASE_URL.startswith("sqlite:///")

    # 生产环境保护（允许 SQLite 开发模式）
    if is_production and is_sqlite and not config.allow_sqlite_in_production:
        raise ValueError("生产环境使用 SQLite 需要显式配置 ALLOW_SQLITE_IN_PRODUCTION=true")

    if is_sqlite:
        # SQLite 配置
        _engine = create_engine(
            DATABASE_URL,
            poolclass=StaticPool,  # ✅ 使用 StaticPool
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # 启用外键和 WAL
        from sqlalchemy import event
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    else:
        # PostgreSQL 配置（保持不变）
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            # ...
        )
```

#### 修改 2: JSONB → JSON

**位置**: `src/models/database.py:30`, `:560`, `:621`, `:709`

**当前代码**:
```python
from sqlalchemy.dialects.postgresql import JSONB

class Provider(Base):
    proxy = Column(JSONB, nullable=True)
```

**建议修改**:
```python
from sqlalchemy import JSON  # 通用 JSON 类型

# 方案 A: 直接改为 JSON（SQLite 兼容）
class Provider(Base):
    proxy = Column(JSON, nullable=True)

# 方案 B: 方言自适应类型（推荐）
from sqlalchemy import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

class UniversalJSON(TypeDecorator):
    impl = JSON

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

class Provider(Base):
    proxy = Column(UniversalJSON, nullable=True)
```

#### 修改 3: Alembic 环境配置

**位置**: `alembic/env.py`

**当前代码** (约 line 82):
```python
def run_migrations_online():
    connectable = engine_from_config(
        config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
```

**建议修改**:
```python
def run_migrations_online():
    connectable = engine_from_config(
        config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # SQLite 启用外键
    if connectable.dialect.name == 'sqlite':
        from sqlalchemy import event
        @event.listens_for(connectable, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # ✅ 正确位置：在 context.configure() 中设置 render_as_batch
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # SQLite 需要 batch 模式
        )

        with context.begin_transaction():
            context.run_migrations()
```

### 3.3 工作量估算

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| 1. 数据模型调整 | JSONB → JSON，Enum 检查 | 1.5h |
| 2. 引擎配置 | 添加 SQLite 分支（同步+异步），PRAGMA 设置 | 2.5h |
| 3. Alembic 支持 | env.py 配置，迁移脚本审查或创建 baseline | 3-5h |
| 4. 配置管理 | 添加环境变量开关 | 0.5h |
| 5. 文档编写 | 使用说明，限制说明 | 1h |
| 6. 测试验证 | 跑完整迁移链 + 核心用例回归 | 2h |
| **总计** | | **10.5-12.5h** |

### 3.4 数据迁移路径

#### 从 PostgreSQL 迁移到 SQLite

**方案 A: Alembic 迁移链**
```bash
# 1. 导出 PostgreSQL 数据
pg_dump -U postgres -d aether -f dump.sql

# 2. 创建 SQLite 数据库
sqlite3 aether.db < schema.sql  # 使用生成的 baseline

# 3. 转换并导入数据（需要手动处理类型转换）
python scripts/migrate_pg_to_sqlite.py --dump dump.sql --db aether.db
```

**方案 B: 应用层导出/导入**（推荐）
```python
# scripts/export_from_postgres.py
from src.database.database import create_session
from src.models.database import Base, User, ApiKey, Provider

def export_data():
    """导出所有数据到 JSON"""
    db = create_session()
    data = {
        "users": [u.__dict__ for u in db.query(User).all()],
        "api_keys": [k.__dict__ for k in db.query(ApiKey).all()],
        "providers": [p.__dict__ for p in db.query(Provider).all()],
        # ... 其他表
    }
    db.close()
    return data

# scripts/import_to_sqlite.py
def import_data(data):
    """从 JSON 导入到 SQLite"""
    # 设置 DATABASE_URL=sqlite:///aether.db
    db = create_session()

    for user_data in data["users"]:
        user = User(**user_data)
        db.add(user)

    db.commit()
    db.close()
```

**数据完整性校验**:
```python
def validate_migration(pg_db, sqlite_db):
    """校验迁移后数据完整性"""
    assert pg_db.query(User).count() == sqlite_db.query(User).count()
    assert pg_db.query(ApiKey).count() == sqlite_db.query(ApiKey).count()
    # ... 其他表的校验
```

### 3.5 SQLite 专用 Baseline 方案

为了简化迁移，建议创建 SQLite 专用 baseline：

```bash
# 1. 在 PostgreSQL 上运行所有迁移
alembic upgrade head

# 2. 生成 SQLite baseline
alembic revision --autogenerate -m "SQLite baseline"

# 编辑生成的迁移文件，添加条件：
def upgrade():
    # 仅在非 SQLite 数据库执行
    if not op.get_context().dialect.name == 'sqlite':
        # 保留历史迁移逻辑
        pass

def downgrade():
    # 仅在非 SQLite 数据库执行
    if not op.get_context().dialect.name == 'sqlite':
        # 保留历史迁移逻辑
        pass
```

---

## 4. 可行性结论与建议

### 4.1 总体结论

**⚠️ 有条件推荐** - SQLite 适用于以下场景：

✅ **推荐使用场景**:
- 开发/测试环境
- 单用户或小团队使用（< 5 用户）
- 低并发场景（< 10 req/s）
- 数据量 < 100MB
- 对部署简便性要求高于性能

❌ **不推荐使用场景**:
- 生产环境（多用户、高并发）
- 需要复杂 JSON 查询
- 需要高可用性和数据安全性
- 多进程部署（Gunicorn workers > 1）

### 4.2 功能对比总结

| 功能 | PostgreSQL | SQLite (小规模) | 影响 |
|------|-----------|----------------|------|
| 基础 CRUD | ✅ | ✅ | 无影响 |
| JSON 查询 | ✅ 快速 | ⚠️ 较慢 | 中等影响 |
| 并发写入 | ✅ 高并发 | ⚠️ 单写入者 | 严重影响 |
| 数据完整性 | ✅ 强保证 | ✅ 有保证（需配置） | 需注意 |
| 迁移和备份 | ✅ 灵活 | ⚠️ 需手动 | 轻微影响 |
| 部署复杂度 | ❌ 需独立服务 | ✅ 零配置 | SQLite 优势 |

### 4.3 实施建议

#### 短期方案（开发环境）

1. **添加开发模式支持**
   - 通过环境变量 `ENABLE_SQLITE=true` 启用
   - 保留 PostgreSQL 作为默认选项
   - 在文档中明确说明 SQLite 的限制

2. **最小化修改**
   - 仅修改 `src/database/database.py` 添加 SQLite 分支
   - JSONB → JSON 改为方言自适应类型
   - 不修改现有 Alembic 迁移脚本（使用 `alembic revision --autogenerate` 重新生成）

3. **验证测试**
   - 运行现有单元测试
   - 手动验证核心功能（用户管理、API Key、Provider）

#### 长期方案（如需生产级 SQLite）

1. **完整迁移**
   - 改写所有 Alembic 迁移脚本
   - 优化 JSON 查询性能
   - 实现自动备份机制

2. **监控和告警**
   - 添加数据库性能监控
   - 设置锁等待超时告警
   - 定期数据完整性检查

3. **应急预案**
   - 准备 PostgreSQL 回迁方案
   - 实现数据导出/导入工具

### 4.4 推荐配置

#### 环境变量配置

```bash
# .env 文件
DATABASE_URL=sqlite:///./aether.db  # 或 postgresql://...

# 开发模式允许 SQLite
ENABLE_SQLITE_IN_DEVELOPMENT=true
ALLOW_SQLITE_IN_PRODUCTION=false  # 生产环境默认禁止

# SQLite 优化配置
SQLITE_WAL_MODE=true
SQLITE_SYNCHRONOUS=NORMAL  # 性能模式
SQLITE_CACHE_SIZE=-64000   # 64MB 缓存
SQLITE_JOURNAL_SIZE_LIMIT=1048576  # 1MB 日志
```

#### 数据库初始化脚本

```python
# scripts/init_sqlite.py
import sqlite3

def init_sqlite_db(db_path: str):
    conn = sqlite3.connect(db_path)

    # 启用外键
    conn.execute("PRAGMA foreign_keys=ON")

    # 启用 WAL 模式（提升并发性能）
    conn.execute("PRAGMA journal_mode=WAL")

    # 性能优化
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA temp_store=MEMORY")

    # 安全性设置
    conn.execute("PRAGMA busy_timeout=5000")  # 5秒锁超时

    conn.close()
```

### 4.5 性能基准测试建议

建议在实施前进行性能测试：

| 测试场景 | 指标 | PostgreSQL | SQLite (WAL) | 可接受阈值 |
|---------|------|-----------|--------------|-----------|
| 简单查询 QPS | 1000 | 1000 | 600 | > 500 |
| JSON 查询延迟 | 10ms | 10ms | 100ms | < 200ms |
| 并发写入 | 100 | 100 | 10 | > 5 |
| 数据库启动 | 2s | 2s | 0.05s | N/A |

### 4.6 风险缓解措施

| 风险 | 缓解措施 | 优先级 |
|------|---------|--------|
| JSONB 性能下降 | 应用层过滤，添加表达式索引 | 高 |
| 外键失效 | 强制 `PRAGMA foreign_keys=ON` | 高 |
| 连接池错误 | 使用 `NullPool` + WAL | 高 |
| 数据库锁 | 限制 worker 数量，设置超时 | 中 |
| 时区错误 | 应用层统一 UTC | 中 |
| 迁移失败 | 使用批量初始化替代迁移 | 中 |
| 生产误用 | 显式配置开关 + 警告日志 | 低 |

---

## 5. 附录

### 5.1 已发现的 SQLite 支持代码

**文件**: `src/database/database.py:189-190`

```python
elif DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
```

**说明**: 项目已包含 SQLite 异步驱动支持，表明开发者已考虑 SQLite 兼容性。

### 5.2 相关依赖

**已安装**:
```toml
aiosqlite>=0.20.0  # SQLite 异步驱动 ✅
```

**需添加**（可选，用于性能优化）:
```toml
# 无需额外依赖，SQLAlchemy 内置支持
```

### 5.3 性能基准测试建议

建议在实施前进行实际性能测试：

```python
# tests/benchmark_sqlite.py
import time
import statistics
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.database import User, ApiKey

def benchmark_simple_query(session, iterations=100):
    """测试简单查询性能"""
    times = []
    for _ in range(iterations):
        start = time.time()
        session.query(User).filter_by(is_active=True).all()
        times.append((time.time() - start) * 1000)  # 毫秒

    return {
        "avg": statistics.mean(times),
        "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
        "min": min(times),
        "max": max(times),
    }

def benchmark_json_query(session, iterations=100):
    """测试 JSON 查询性能"""
    times = []
    for _ in range(iterations):
        start = time.time()
        session.query(ApiKey).filter(ApiKey.allowed_models.is_not(None)).all()
        times.append((time.time() - start) * 1000)

    return {
        "avg": statistics.mean(times),
        "p95": statistics.quantiles(times, n=20)[18],
        "min": min(times),
        "max": max(times),
    }
```

### 5.4 Alembic 测试验证步骤

**验证清单**:

```bash
# 1. 新建空 SQLite 数据库
rm -f test_aether.db
export DATABASE_URL="sqlite:///test_aether.db"

# 2. 运行完整迁移链
alembic upgrade head

# 3. 验证所有表已创建
sqlite3 test_aether.db ".tables"

# 4. 验证外键已启用
sqlite3 test_aether.db "PRAGMA foreign_keys;"

# 5. 验证 WAL 模式已启用
sqlite3 test_aether.db "PRAGMA journal_mode;"

# 6. 运行核心用例测试
pytest tests/test_api_keys.py -v
pytest tests/test_providers.py -v

# 7. 回滚测试
alembic downgrade base
alembic upgrade head
```

### 5.5 参考资料

- [SQLite vs PostgreSQL](https://www.postgresql.org/about/news/graphical-sqlite-vs-postgresql-1891/)
- [SQLAlchemy SQLite 文档](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Alembic SQLite 批量模式](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [SQLite WAL 模式](https://www.sqlite.org/wal.html)
- [SQLite FTS5 全文搜索](https://www.sqlite.org/fts5.html)
- [aiosqlite 文档](https://aiosqlite.omnilib.dev/)

### 5.6 联系方式

如有疑问或需要进一步讨论，请联系项目维护者。

---

**报告生成时间**: 2026-01-11
**分析工具**: Claude Code + Codex MCP
**版本**: 1.1 (根据 Codex review 更新)
