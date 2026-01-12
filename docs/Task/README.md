# 任务索引

## 活跃任务 (Active)

当前没有活跃任务。

---

## 已完成任务 (Archive)

### 2026-01
- ✅ [修复 created_at.isoformat() AttributeError](Archive/2026-01/FIX_DATETIME_ISOFORMAT_ERROR.md) - 完成于 2026-01-13
  - 使用 `text().columns()` 显式声明列类型，让 SQLAlchemy 自动反序列化 datetime
  - 添加 `format_datetime()` 辅助函数统一时区处理（UTC）
  - 处理 `None` 和非 datetime 类型的边界情况
  - 确保跨数据库（SQLite/PostgreSQL）输出格式统一
  - **Codex Review**: ✅ 通过，可以投入生产使用

- ✅ [修复 analyze_cache_affinity_ttl SQL 语法错误](Archive/2026-01/FIX_CACHE_AFFINITY_TTL_SQL.md) - 完成于 2026-01-13
  - 为 SQLite 和 PostgreSQL 提供不同的 SQL 实现
  - SQLite 使用 `julianday()` 计算时间差
  - SQLite 使用 `SUM(CASE WHEN ...)` 替代 `FILTER`
  - SQLite 在 Python 中计算百分位数
  - 修复 `filter_id` 参数错配问题
  - 修复 `0.0` 被当成 `None` 的问题
  - **Codex Review**: ✅ 通过，发现并修复了 2 个重要问题

---

## 任务归档规则

- 按完成月份归档到 `Archive/YYYY-MM/` 目录
- 任务完成后立即归档并更新本索引
- 保留完整的任务文档作为历史记录
