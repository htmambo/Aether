# 文件清单

## 文件映射表

| 迁移包内文件 | 目标路径 | 说明 |
|------------|---------|------|
| `header_rules.py` | `src/core/header_rules.py` | 规则引擎核心实现 |
| `header_rule_examples.py` | `src/core/header_rule_examples.py` | 规则示例和工具函数 |
| `HeadersRulesEditor.vue` | `frontend/src/features/providers/components/HeadersRulesEditor.vue` | 规则可视化编辑器 |
| `dialog_index.ts` | `frontend/src/components/ui/dialog/index.ts` | Dialog组件统一导出 |

## 新增文件

### 后端核心文件
1. `header_rules.py` -> `src/core/header_rules.py` - Header 规则引擎核心实现（237 行）
2. `header_rule_examples.py` -> `src/core/header_rule_examples.py` - 规则示例和工具函数（336 行）

### 前端核���文件
3. `HeadersRulesEditor.vue` -> `frontend/src/features/providers/components/HeadersRulesEditor.vue` - Header 规则可视化编辑器（532 行）
4. `dialog_index.ts` -> `frontend/src/components/ui/dialog/index.ts` - Dialog 组件统一导出（6 行）

## 修改文件

### 后端
5. `src/models/endpoint_models.py` - 修改 headers 字段类型为 `Dict[str, Any]`
6. `src/api/handlers/base/request_builder.py` - 添加规则应用逻辑
7. `src/services/provider/transport.py` - 添加规则应用逻辑
8. `src/api/handlers/base/endpoint_checker.py` - 添加规则应用逻辑

### 前端
9. `frontend/src/features/providers/components/EndpointFormDialog.vue` - 集成规则编辑器
10. `frontend/src/api/endpoints/types.ts` - 更新类型定义
11. `frontend/src/api/endpoints/endpoints.ts` - 更新类型定义

## 修改文件详细diff

### src/models/endpoint_models.py

```python
# 修改位置：所��� endpoint 相关模型的 headers 字段
# 修改前：
headers: Optional[Dict[str, str]] = None

# 修改后：
from typing import Any
headers: Optional[Dict[str, Any]] = None
```

### src/api/handlers/base/request_builder.py

```python
# 在 PassthroughRequestBuilder.build_headers() 方法中添加：

from src.core.header_rules import apply_header_rules

# 检查 endpoint.headers 是否包含规则键
endpoint_headers = self.endpoint.headers or {}
rule_keys = ['add', 'remove', 'replace_name', 'replace_value']
has_rules = any(key in endpoint_headers for key in rule_keys)

if has_rules:
    # 应用规则
    headers = apply_header_rules(headers, endpoint_headers)
else:
    # 旧格式：直接合并
    headers.update(endpoint_headers)
```

### src/services/provider/transport.py

```python
# 在 build_provider_headers() 函数中添加：

from src.core.header_rules import apply_header_rules

# 检测是否是规则对象
rule_keys = ['add', 'remove', 'replace_name', 'replace_value']
has_rules = any(key in endpoint_headers for key in rule_keys)

if has_rules:
    headers = apply_header_rules(headers, endpoint_headers)
else:
    # 旧格式：直接合并
    headers.update(endpoint_headers)
```

### src/api/handlers/base/endpoint_checker.py

```python
# 在 build_safe_headers() 函数中添加：

from src.core.header_rules import apply_header_rules

# 应用规则（如果存在）
headers = apply_header_rules(headers, extra_headers)
```

### frontend/src/api/endpoints/types.ts

```typescript
// 添加类型定义：
export interface HeaderReplaceValueRule {
  search: string
  replace: string
  regex?: boolean
  case_sensitive?: boolean
}

export interface HeaderRules {
  add?: Record<string, string>
  remove?: string[]
  replace_name?: Record<string, string>
  replace_value?: Record<string, HeaderReplaceValueRule>
}

export type EndpointHeadersConfig = Record<string, string> | HeaderRules

// 修改 ProviderEndpoint 接口：
export interface ProviderEndpoint {
  // ... 其他字段
  headers?: EndpointHeadersConfig | null  // 改为 union 类型
}
```

### frontend/src/features/providers/components/EndpointFormDialog.vue

需要添加：
1. 导入 HeadersRulesEditor 组件
2. 添加 HeaderRules 类型定义
3. 在 form 中添加 headers_rules 字段
4. 添加 convertHeadersToRules() 转换函数
5. 在模板中添加规则编辑器UI
6. 在 loadEndpointData() 中转换 headers
7. 在 handleSubmit() 中将 headers_rules 写回 headers

详细修改请参考 MIGRATION_GUIDE.md 中的完整代码片段。
