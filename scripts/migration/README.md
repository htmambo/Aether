# 数据库迁移工具使用指南

本工具包支持 SQLite 和 PostgreSQL 之间的双向数据迁移。

---

## 📋 目录

- [快速开始](#快速开始)
- [迁移方向](#迁移方向)
- [详细使用说明](#详细使用说明)
- [常见问题](#常见问题)
- [故障排除](#故障排除)

---

## 🚀 快速开始

### SQLite → PostgreSQL

```bash
python -m scripts.migration.sqlite_to_postgres \
    --sqlite "sqlite:///./data/aether.db" \
    --postgres "postgresql://user:pass@localhost:5432/aether"
```

### PostgreSQL → SQLite

```bash
python -m scripts.migration.postgres_to_sqlite \
    --postgres "postgresql://user:pass@localhost:5432/aether" \
    --sqlite "sqlite:///./data/aether.db"
```

---

## 🔄 迁移方向

### 1. SQLite → PostgreSQL

**使用场景**:
- 从开发环境（SQLite）迁移到生产环境（PostgreSQL）
- 数据量增长，需��更高性能
- 需要支持高并发

**前提条件**:
1. ✅ PostgreSQL 数据库已创建
2. ✅ 已运行所有 Alembic 迁移 (`alembic upgrade head`)
3. ✅ SQLite 数据库可访问

**执行步骤**:

```bash
# 1. 准备 PostgreSQL 数据库
export DATABASE_URL="postgresql://user:pass@localhost:5432/aether"
alembic upgrade head

# 2. 备份 SQLite 数据库（可选但推荐）
cp data/aether.db data/aether.db.backup

# 3. 执行迁移
python -m scripts.migration.sqlite_to_postgres \
    --sqlite "sqlite:///./data/aether.db" \
    --postgres "postgresql://user:pass@localhost:5432/aether"

# 4. 验证迁移
# 脚本会自动验证数据完整性

# 5. 切换配置
# 编辑 .env: DATABASE_URL=postgresql://...

# 6. 重启应用
systemctl restart aether
```

**预期输出**:

```
============================================================
开始数据迁移
============================================================
源数据库: sqlite:///./data/aether.db
目标数据库: postgresql://...@localhost:5432/aether
批处理大小: 1000
------------------------------------------------------------
开始迁移表: users
  总记录数: 150
  进度: 100/150 (66%)
  进度: 150/150 (100%)
  ✅ users 迁移完成: 150 条记录
...
============================================================
迁移统计
============================================================
总表数: 18
成功迁移: 12,345 条记录
耗时: 2 分 15 秒
速度: 92.1 条/秒
============================================================
正在验证数据完整性...
  ✅ users: 150 条记录
  ✅ api_keys: 320 条记录
...
============================================================
✅ 数据完整性验证通过！
```

### 2. PostgreSQL → SQLite

**使用场景**:
- 从生产环境导出数据进行本地开发
- 创建测试环境
- 降级到轻量级数据库

**前提条件**:
1. ✅ SQLite 文件路径可写
2. ✅ PostgreSQL 数据库可访问
3. ✅ SQLite 数据库已初始化（运行 Alembic 迁移）

**执行步骤**:

```bash
# 1. 初始化 SQLite 数据库
export DATABASE_URL="sqlite:///./data/aether.db"
alembic upgrade head

# 2. 备份 PostgreSQL 数据库（推荐）
pg_dump -U user -d aether -f backup.sql

# 3. 执行迁移
python -m scripts.migration.postgres_to_sqlite \
    --postgres "postgresql://user:pass@localhost:5432/aether" \
    --sqlite "sqlite:///./data/aether.db"

# 4. 验证并切换配置
```

---

## 📖 详细使用说明

### 命令行参数

#### SQLite → PostgreSQL

```bash
python -m scripts.migration.sqlite_to_postgres \
    --sqlite "sqlite:///./data/aether.db" \      # 必需：SQLite 数据库 URL
    --postgres "postgresql://..." \              # 必需：PostgreSQL 数据库 URL
    --batch-size 1000 \                          # 可选：批处理大小（默认: 1000）
    --verify-only \                              # 可选：仅验证，不迁移
    --no-verify \                                # 可选：迁移后不验证
    --quiet                                      # 可选：减少日志输出
```

#### PostgreSQL → SQLite

```bash
python -m scripts.migration.postgres_to_sqlite \
    --postgres "postgresql://..." \              # 必需：PostgreSQL 数据库 URL
    --sqlite "sqlite:///./data/aether.db" \      # 必需：SQLite 数据库 URL
    --batch-size 1000 \                          # 可选：批处理大小（默认: 1000）
    --verify-only \                              # 可选：仅验证，不迁移
    --no-verify \                                # 可选：迁移后不验证
    --quiet                                      # 可选：减少日志输出
```

### 数据类型转换

#### SQLite → PostgreSQL

| SQLite 类型 | PostgreSQL 类型 | 说明 |
|-------------|-----------------|------|
| JSON | JSONB | 自动转换，性能提升 |
| TEXT | TIMESTAMP WITH TIME ZONE | 自动解析 |
| INTEGER (0/1) | BOOLEAN | 自动转换 |
| INTEGER | SERIAL/BIGINT | 保持不变 |

#### PostgreSQL → SQLite

| PostgreSQL 类型 | SQLite 类型 | 说明 |
|-----------------|-------------|------|
| JSONB | JSON | 自动转换 |
| TIMESTAMP WITH TIME ZONE | TEXT (ISO 8601) | 转为 UTC 字符串 |
| BOOLEAN | INTEGER (0/1) | 保持布尔值 |
| ARRAY | TEXT (JSON) | 转为 JSON 数组 |
| SERIAL | INTEGER | 自动生成 ID |

---

## ❓ 常见问题

### Q1: 迁移需要多长时间？

**A**: 取决于数据量：

| 数据量 | 预计时间 |
|--------|---------|
| < 10,000 条 | < 1 分钟 |
| 10,000 - 100,000 条 | 1-5 分钟 |
| 100,000 - 1,000,000 条 | 5-30 分钟 |
| > 1,000,000 条 | 30 分钟以上 |

### Q2: 迁移过程中可以中断吗？

**A**: 不推荐。如果中断：
- 已迁移的数据会保留在目标数据库
- 重新运行会继续迁移（不会重复）
- 建议先清空目标数据库再重新迁移

### Q3: 如何验证迁移是否成功？

**A**: 脚本会自动验证：
- ✅ 检查每个表的记录数是否一致
- ✅ 输出详细的验证报告

手动验证：
```bash
# 验证用户数
python -c "
from src.database.database import create_session
from src.models.database import User
db = create_session()
print(f'用户数: {db.query(User).count()}')
db.close()
"
```

### Q4: 迁移失败如何回滚？

**A**: 根据迁移方向：

**SQLite → PostgreSQL 失败**:
```bash
# 回滚到 SQLite
# 编辑 .env: DATABASE_URL=sqlite:///./data/aether.db
systemctl restart aether
```

**PostgreSQL → SQLite 失败**:
```bash
# 回滚到 PostgreSQL
# 编辑 .env: DATABASE_URL=postgresql://...
systemctl restart aether
```

### Q5: 能否只迁移部分表？

**A**: 当前版本不支持，会迁移所有表。如需迁移部分表：
1. 修改 `scripts/migration/base.py` 中的 `TABLES` 列表
2. 或使用数据库特定的导出/导入工具

### Q6: 大数据量如何优化迁移速度？

**A**: 调整参数：
```bash
# 增加批处理大小（减少数据库往返）
python -m scripts.migration.sqlite_to_postgres \
    --sqlite "sqlite:///./data/aether.db" \
    --postgres "postgresql://..." \
    --batch-size 5000  # 默认 1000
```

其他优化：
- 关闭不必要的索引
- 使用本地网络（避免网络延迟）
- 增加数据库连接池大小

---

## 🔧 故障排除

### 错误 1: 表不存在

**错误信息**:
```
目标表 users 不存在，请先运行迁移
```

**解决方案**:
```bash
# 确保目标数据库已运行所有迁移
alembic upgrade head
```

### 错误 2: 连接失败

**错误信息**:
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect
```

**解决方案**:
1. 检查数据库 URL 是否正确
2. 检查数据库服务是否运行
3. 检查网络连接
4. 检查用户名密码

### 错误 3: 权限不足

**错误信息**:
```
permission denied to create table
```

**解决方案**:
```sql
-- PostgreSQL: 授予权限
GRANT ALL PRIVILEGES ON DATABASE aether TO user;
GRANT ALL PRIVILEGES ON SCHEMA public TO user;
```

### 错误 4: 外键约束失败

**错误信息**:
```
IntegrityError: foreign key constraint failed
```

**解决方案**:
1. 确保外键 PRAGMA 已启用（SQLite）
2. 检查迁移顺序（已在代码中处理）
3. 验证父表数据已迁移

### 错误 5: 内存不足

**错误信息**:
```
MemoryError: cannot allocate memory
```

**解决方案**:
```bash
# 减小批处理大小
python -m scripts.migration.sqlite_to_postgres \
    --batch-size 100  # 从 1000 减到 100
```

---

## 📊 迁移性能参考

### 测试环境

- CPU: 4 核
- 内存: 8 GB
- 磁盘: SSD

### SQLite → PostgreSQL

| 数据量 | 记录数 | 时间 | 速度 |
|--------|--------|------|------|
| 小型 | 1,000 | 2 秒 | 500 条/秒 |
| 中型 | 50,000 | 45 秒 | 1,111 条/秒 |
| 大型 | 500,000 | 8 分钟 | 1,041 条/秒 |

### PostgreSQL → SQLite

| 数据量 | 记录数 | 时间 | 速度 |
|--------|--------|------|------|
| 小型 | 1,000 | 3 秒 | 333 条/秒 |
| 中型 | 50,000 | 60 秒 | 833 条/秒 |
| 大型 | 500,000 | 12 分钟 | 694 条/秒 |

---

## 🔒 安全建议

### 迁移前

1. **备份数据库**
   ```bash
   # SQLite
   cp data/aether.db data/aether.db.backup

   # PostgreSQL
   pg_dump -U user -d aether > backup.sql
   ```

2. **在测试环境验证**
   ```bash
   # 先在开发环境测试迁移
   python -m scripts.migration.sqlite_to_postgres \
       --sqlite "sqlite:///./dev.db" \
       --postgres "postgresql://user@localhost:5432/aether_dev"
   ```

3. **选择低峰时段**
   - 避免业务高峰期
   - 提前通知用户

### 迁移后

1. **保留备份 7 天**
   ```bash
   # 保留原始数据库文件
   # 确认无问题后再删除
   ```

2. **监控应用日志**
   ```bash
   # 检查是否有数据库相关错误
   tail -f logs/app.log | grep -i database
   ```

3. **性能测试**
   ```bash
   # 运行性能测试脚本
   pytest tests/test_performance.py
   ```

---

## 📞 获取帮助

如遇问题：

1. 查看日志文件：`logs/migration.log`
2. 检查故障排除章节
3. 提交 Issue：[GitHub Issues](https://github.com/fawney19/Aether/issues)

---

**文档版本**: 1.0
**更新时间**: 2026-01-11
