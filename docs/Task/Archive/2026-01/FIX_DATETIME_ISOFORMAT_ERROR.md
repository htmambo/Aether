# 修复 created_at.isoformat() AttributeError

## 状态: ✅ 已完成 (完成时间: 2026-01-13)

## 背景

在 `src/services/usage/service.py` 的 `get_interval_timeline` 函数中出现 AttributeError 错误。

### 错误信息
```
AttributeError: 'str' object has no attribute 'isoformat'. Did you mean: 'format'?
```

### 错误位置
- **文件**: `src/services/usage/service.py`
- **行号**: 2294, 2308（最初错误位置）
- **函数**: `get_interval_timeline`

## 问题分析

### 根本原因
1. SQLite 数据库返回的 `created_at` 字段���字符串类型（TEXT），而不是 Python datetime 对象
2. 代码使用 `text()` 原生 SQL 查询，没有通过 ORM 的类型绑定
3. SQLAlchemy 不会自动将字符串反序列化为 datetime 对象
4. 代码假设 `created_at` 是 datetime 对象并调用 `.isoformat()` 方法
5. 字符串对象没有 `.isoformat()` 方法，导致 AttributeError

### 影响范围
- `src/services/usage/service.py:2294`: `include_user_info=True` 的代码路径
- `src/services/usage/service.py:2308`: `include_user_info=False` 的代码路径

## 解决方案演进

### 方案 1: 就地兜底（初步方案）❌

**内容**：使用类型检查，支持字符串和 datetime 对象两种类型

```python
# 修改前
"x": created_at.isoformat(),

# 修改后
x_value = created_at if isinstance(created_at, str) else created_at.isoformat()
"x": x_value,
```

**问题**：
- ❌ 时间格式不一致（SQLite 可能返回非 ISO 格式）
- ❌ 未处理 `None` 边界情况
- ❌ 代码重复（两处相同逻辑）
- ❌ 输出契约不明确（API 返回的时间格式不统一）
- ❌ 不同数据库返回格式不一致（SQLite vs PostgreSQL）

**Codex Review 结果**：能够解决 AttributeError，但只是"就地兜底"，带来时间格式不一致与少数边界值未覆盖的问题。

---

### 方案 2: 使用 `.columns()` 类型声明（最终方案）✅

**思路**：让 SQLAlchemy 在结果集层把 `created_at` 反序列化为 `datetime`，从根上避免 SQLite 返回 `str` 导致的问题。

#### 实施步骤

**1. 导入必要的类型**
```python
from sqlalchemy import DateTime, Float, String, text
```

**2. 添加辅助函数统一时区处理**
```python
def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string, ensuring UTC aware output."""
    if dt is None:
        return None
    # Defensive: ensure dt is a datetime object
    if not isinstance(dt, datetime):
        logger.warning(f"Unexpected datetime type: {type(dt)}, skipping row")
        return None
    # If naive (SQLite), treat as UTC; if aware (PostgreSQL), convert to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()
```

**3. 为 SQL 查询添加 `.columns()` 声明**

管理员视图（SQLite 和 PostgreSQL）：
```python
sql = text(f"""
    ...
""").columns(
    created_at=DateTime(timezone=True),
    user_id=String(),
    model=String(),
    username=String(),
    interval_minutes=Float()
)
```

普通视图：
```python
sql = text(f"""
    ...
""").columns(
    created_at=DateTime(timezone=True),
    model=String(),
    interval_minutes=Float()
)
```

**4. 使用辅助函数格式化时间**
```python
# Format datetime with consistent UTC timezone handling
x_value = format_datetime(created_at)
if x_value is None:
    continue  # Skip rows with invalid created_at
point_data = {
    "x": x_value,
    "y": round(float(interval_minutes), 2),
    ...
}
```

#### 优势
- ✅ **类型安全**：SQLAlchemy 自动反序列化为 datetime 对象
- ✅ **时间格式统一**：所有输出都是 UTC aware 的 ISO 格式字符串
- ✅ **跨数据库兼容**：SQLite（naive）和 PostgreSQL（aware）统一处理为 UTC
- ✅ **防御式编程**：处理 `None` 和非 datetime 类型
- ✅ **代码清晰**：移除了分支判断，逻辑更简洁
- ✅ **可维护性高**：类型声明明确，易于理解和修改

#### Codex Review 最终结论
- ✅ 解决了之前指出的所有问题
- ✅ `.columns()` 类型声明完全正确
- ✅ 时区处理逻辑合理（naive 按 UTC，aware 转为 UTC）
- ✅ None 处理逻辑完善（跳过无效数据）
- ✅ **可以投入生产使用**

## 修改文件

- `src/services/usage/service.py` (4 处修改)
  - 导入 `DateTime`, `Float`, `String` 类型
  - 添加 `format_datetime()` 辅助函数
  - 为 3 个 SQL 查询添加 `.columns()` 声明
  - 在 2 处使用 `format_datetime()` 替代直接调用 `.isoformat()`

## 验证步骤

1. ✅ 代码已修复并经过 codex review
2. 重启应用服务（由用户执行）
3. 调用 `/admin/usage/timeline` 接口
4. 确认返回的 JSON 中 `x` 字���为有效的 ISO 格式时间字符串
5. 确认无 AttributeError 异常

## 风险评估

### 低风险 ✅
- 修改涉及类型声明和格式化，不影响数据逻辑
- 修改向后兼容，同时支持 SQLite 和 PostgreSQL
- 代码简洁清晰，易于维护
- 防御式编程，处理边界情况

### 注意事项
- ⚠️ **前提假设**：SQLite 中存储的 naive 时间必须是 UTC。如果历史数据曾以"本地时区 naive"写入，会产生偏移。
- ⚠️ **输出格式**：`.isoformat()` 输出通常是 `...+00:00` 而不是 `Z`。如果前端严格要求 `Z`，需要额外处理。

## 备注

### 问题根源
SQLite 的 `created_at` 字段存储为 TEXT 类型（ISO 格式字符串），SQLAlchemy 在使用 `text()` 原生 SQL 查询时不会自动进行类型转换，直接返回字符串。

### 技术细节
- **SQLAlchemy 2.x 要求**：`.columns()` 中的类型必须是 `TypeEngine` 对象，不能使用 `None`
- **类型声明影响**：使用 `DateTime(timezone=True)` 告诉 SQLAlchemy 按带时区的 datetime 处理
- **时区一致性**：通过统一转换为 UTC，确保 SQLite（naive）和 PostgreSQL（aware）输出一致

### 经验教训
1. **数据库字段类型与 Python 对象类型可能不一致**
2. **在处理外部数据时应进行类型检查**
3. **使用 `text()` 查询时，需要显式声明列类型以获得类型安全的反序列化**
4. **时区一致性在跨数据库场景中非常重要**
5. **防御式编程可以提高代码健壮性**

## 总结

**完成时间**: 2026-01-13

**修复内容**:
1. 使用 `text().columns()` 显式声明列类型，让 SQLAlchemy 自动反序列化
2. 添加 `format_datetime()` 辅助函数统一时区处理（UTC）
3. 处理 `None` 和非 datetime 类型的边界情况
4. 确保输出格式统一为 UTC aware 的 ISO 字符串

**与初步方案的对比**:
- 初步方案：就地兜底，解决了 AttributeError 但带来新问题
- 最终方案：从根本解决问题，提高类型安全性和一致性

**Codex Review**: ✅ 通过，可以投入生产使用

**相关提交**: (待用户提交)
