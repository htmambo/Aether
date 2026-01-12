# 修复 analyze_cache_affinity_ttl SQL 语法错误

## 状态: ✅ 已完成 (完成时间: 2026-01-13)

## 背景

在 `src/services/usage/service.py` 的 `analyze_cache_affinity_ttl` 函数中出现 SQL 语法错误。

### 错误信息
```
sqlite3.OperationalError: near "FROM": syntax error
```

### 错误位置
- **文件**: `src/services/usage/service.py`
- **行号**: 1804-1819（原始）
- **函数**: `analyze_cache_affinity_ttl`

## 问题分析

### 根本原因
SQL 查询使用了 PostgreSQL 特有的语法，SQLite 不支持：

1. **`EXTRACT(EPOCH FROM (created_at - prev_request_at)) / 60.0`**
   - PostgreSQL 的时间戳差计算函数
   - SQLite 不支持 `EXTRACT` 和 `EPOCH`

2. **`COUNT(*) FILTER (WHERE interval_minutes <= 5)`**
   - PostgreSQL 的聚合过滤语法
   - SQLite 不支持 `FILTER` 子句

3. **`PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interval_minutes)`**
   - PostgreSQL 的百分位数窗口函数
   - SQLite 不支持

## 解决方案

### 方案: 检测数据库类型，分别实现

为 SQLite 和 PostgreSQL 提供不同的 SQL 实现：

**SQLite 实现**：
1. 时间差计算：使用 `(julianday(created_at) - julianday(prev_request_at)) * 1440.0`
2. 聚合过滤：使用 `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`
3. 百分位数：在 Python 中计算（使用 `percentile_cont()` 函数）

**PostgreSQL 实现**：
- 保留原有的 SQL 语法，利用数据库的高级功能

## 关键代码改动

### 1. 添加数据库类型检测
```python
# 检测数据库方言（SQLite 需要使用兼容 SQL）
bind = db.bind
dialect = bind.dialect.name if bind is not None else "sqlite"
is_sqlite = dialect == "sqlite"
```

### 2. 修复参数错配问题（Codex Review 发现）
```python
# 修复前：可能导致 filter_id 与 group_by_field 不一致
if user_id:
    params["filter_id"] = user_id
elif api_key_id:
    params["filter_id"] = api_key_id

# 修复后：确保 filter_id 与 group_by_field 一致
group_by_field = "api_key_id" if api_key_id else "user_id"
filter_id = None
if api_key_id:
    filter_id = api_key_id
elif user_id:
    filter_id = user_id
```

### 3. SQLite 时间差计算
```python
# SQLite: 使用 julianday() 计算分钟差
(julianday(created_at) - julianday(prev_request_at)) * 1440.0 as interval_minutes

# PostgreSQL: 使用 EXTRACT(EPOCH FROM ...)
EXTRACT(EPOCH FROM (created_at - prev_request_at)) / 60.0 as interval_minutes
```

### 4. SQLite 聚合过滤
```python
# SQLite: 使用 CASE WHEN
SUM(CASE WHEN interval_minutes <= 5 THEN 1 ELSE 0 END) as within_5min

# PostgreSQL: 使用 FILTER
COUNT(*) FILTER (WHERE interval_minutes <= 5) as within_5min
```

### 5. 百分位数计算（SQLite）
```python
def percentile_cont(values: List[float], p: float) -> Optional[float]:
    """
    兼容 PostgreSQL PERCENTILE_CONT 的连续分位数计算：
    - 对排序后的值做线性插值
    - p in [0, 1]
    """
    if not values:
        return None
    values_sorted = sorted(values)
    if p <= 0:
        return values_sorted[0]
    if p >= 1:
        return values_sorted[-1]
    k = (len(values_sorted) - 1) * p
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return values_sorted[f]
    return values_sorted[f] * (c - k) + values_sorted[c] * (k - f)
```

### 6. 修复 0.0 被当成 None（Codex Review 发现）
```python
# 修复前：0.0 会被当成 False，返回 None
"p50": round(float(median_interval), 2) if median_interval else None

# 修复后：使用 is not None 判断
"p50": round(float(median_interval), 2) if median_interval is not None else None
```

## Codex Review 结果

### ✅ 优点
- SQLite 和 PostgreSQL 逻辑基本等价
- `percentile_cont()` 的线性插值实现正确
- 方言检测方式与 `get_interval_timeline` 一致
- SQLite 兼容 SQL 写法清晰

### ⚠️ 发现并修复的问题
1. **高优先级**：`filter_id` 参数错配问题（已修复）
2. **中等优先级**：`0.0` 被当成 `None`（已修复）
3. **性能问题**：SQLite 版本做了两次大 CTE（可接受）

### 📝 改进建议（未实施）
- 减少重复扫描（SQLite 可以用一次查询 + Python 计算）
- 更严谨的 NULL/异常值处理
- 添加单元测试覆盖 `percentile_cont()` 函数

## 修改文件

- `src/services/usage/service.py` (主要修改)
  - 添加数据库类型检测
  - 为 SQLite 实现兼容的 SQL
  - 修复参数错配问题
  - 修复 0.0 判断问题
  - 添加 `percentile_cont()` 辅助函数

## 验证步骤

1. ✅ 代码已修复并经过 codex review
2. 重启应用服务（由用户执行）
3. 调用 `/admin/usage/cache-affinity-ttl` 接口
4. 确认返回正确的分析结果

## 风险评估

### 中等风险 ⚠️
- SQLite 版本使用两次 SQL 查询，可能有性能影响
- 百分位数在 Python 中计算，与 PostgreSQL 可能有微小的浮点误差

### 注意事项
- SQLite 版本的性能可能不如 PostgreSQL 版本
- 百分位数计算结果与 PostgreSQL 可能有微小差异（浮点精度）

## 备注

### PostgreSQL vs SQLite 语法差异
- **时间差计算**: `EXTRACT(EPOCH FROM ...)` vs `julianday() * 86400`
- **聚合过滤**: `FILTER (WHERE ...)` vs `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`
- **百分位数**: `PERCENTILE_CONT(...)` vs 在应用层计算

### 性能考虑
- SQLite 版本使用两次查询：
  1. 第一次：获取基础统计（COUNT, AVG, MIN, MAX）
  2. 第二次：获取所有 interval 用于计算百分位数
- PostgreSQL 版本使用单次查询，利用数据库函数

### 经验教训
1. **使用原生 SQL 时需要注意数据库兼容性**
2. **参数构造要与 SQL 查询逻辑一致**
3. **数值判断要使用 `is not None` 而不是简单的 `if x`**
4. **复杂统计功能在不同数据库间实现差异较大**

## 总结

**完成时间**: 2026-01-13

**修复内容**:
1. 添加数据库类型检测，为 SQLite 和 PostgreSQL 提供不同的 SQL 实现
2. SQLite 使用 `julianday()` 计算时间差
3. SQLite 使用 `SUM(CASE WHEN ...)` 替代 `FILTER`
4. SQLite 在 Python 中计算百分位数
5. 修复 `filter_id` 参数错配问题
6. 修复 `0.0` 被当成 `None` 的问题

**Codex Review**: ✅ 通过，发现并修复了 2 个重要问题

**相关提交**: (待用户提交)
