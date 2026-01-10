# 快速参考

## 核心数据结构

### Header Rules 格式

```typescript
// TypeScript 定义
interface HeaderRules {
  // 新增固定的 headers（不覆盖已存在的）
  add?: Record<string, string>

  // 删除指定的 headers（大小写不敏感）
  remove?: string[]

  // 重命名 header（旧名称 -> 新名称）
  replace_name?: Record<string, string>

  // 替换 header 的值
  replace_value?: Record<string, {
    search: string        // 搜索值
    replace: string       // 替换值
    regex: boolean        // 是否使用正则表达式
    case_sensitive?: boolean  // 是否区分大小写（仅非正则模式）
  }>
}
```

### 使用示例

```json
{
  "add": {
    "X-Custom-Header": "custom-value",
    "X-Request-ID": "12345"
  },
  "remove": ["User-Agent", "Server"],
  "replace_name": {
    "X-Old-Name": "X-New-Name"
  },
  "replace_value": {
    "Authorization": {
      "search": "Bearer old_token",
      "replace": "Bearer new_token",
      "regex": false
    },
    "User-Agent": {
      "search": "MyApp/\\d+\\.\\d+\\.\\d+",
      "replace": "MyApp/2.0.0",
      "regex": true
    }
  }
}
```

## 执行顺序

```
remove → replace_name → replace_value → add
```

**示例**:
```javascript
// 原始 headers
{
  "X-Remove-Me": "gone",
  "X-Old-Name": "value1",
  "X-Replace-Value": "old"
}

// 应用规则后
{
  "X-New-Name": "value1",      // replace_name 生效
  "X-Replace-Value": "new",    // replace_value 生效
  "X-New-Header": "added"      // add 生效
}
// X-Remove-Me 已被删除
```

## 后端集成

### 导入规则引擎

```python
from src.core.header_rules import apply_header_rules, HeaderRules
```

### 应用规则

```python
# 基础用法
headers = {"Content-Type": "application/json"}
rules = {"add": {"X-Custom": "value"}}
result = apply_header_rules(headers, rules)

# 旧格式自动转换
old_headers = {"X-Api-Key": "secret"}  # 旧格式
result = apply_header_rules(headers, old_headers)  # 自动转为 add 规则

# 错误处理：规则无效时返回原 headers
invalid_rules = {"invalid": "data"}
result = apply_header_rules(headers, invalid_rules)  # 返回原 headers
```

## 前端集成

### 使用编辑器组件

```vue
<template>
  <HeadersRulesEditor v-model="headersRules" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HeadersRulesEditor from '@/features/providers/components/HeadersRulesEditor.vue'

const headersRules = ref({
  add: { "X-Custom": "value" },
  remove: ["User-Agent"]
})
</script>
```

### 兼容旧数据转换

```typescript
function convertHeadersToRules(headers: Record<string, string> | null): HeaderRules | null {
  if (!headers) return null

  // 检查是否已经是新格式
  const ruleKeys = ['add', 'remove', 'replace_name', 'replace_value']
  const hasRuleKeys = Object.keys(headers).some(key => ruleKeys.includes(key))

  if (hasRuleKeys) {
    return headers as HeaderRules
  }

  // 旧格式转换为 add 规则
  return { add: { ...headers } }
}
```

## API 请求格式

### 创建 Endpoint

```json
POST /api/endpoints
{
  "name": "My Endpoint",
  "url": "https://api.example.com",
  "headers": {
    "add": {"X-API-Key": "secret"},
    "remove": ["User-Agent"]
  }
}
```

### 更新 Endpoint

```json
PATCH /api/endpoints/{id}
{
  "headers": {
    "replace_value": {
      "Authorization": {
        "search": "old_token",
        "replace": "new_token",
        "regex": false
      }
    }
  }
}
```

### 清空 Headers

```json
PATCH /api/endpoints/{id}
{
  "headers": null
}
```

**注意**: 发送 `headers: undefined` 不会覆盖旧值，必须显式发送 `null`

## 常见用例

### 1. 添加认证 Header

```json
{
  "add": {
    "Authorization": "Bearer YOUR_TOKEN",
    "X-API-Key": "your-api-key"
  }
}
```

### 2. 移除敏感信息

```json
{
  "remove": [
    "Cookie",
    "X-Server-Info",
    "Server"
  ]
}
```

### 3. 动态替换 Token

```json
{
  "replace_value": {
    "Authorization": {
      "search": "Bearer expired_token",
      "replace": "Bearer new_token",
      "regex": false,
      "case_sensitive": true
    }
  }
}
```

### 4. 批量替换版本号

```json
{
  "replace_value": {
    "User-Agent": {
      "search": "MyApp/\\d+\\.\\d+\\.\\d+",
      "replace": "MyApp/2.0.0",
      "regex": true
    }
  }
}
```

### 5. 组合使用

```json
{
  "add": {
    "X-Request-ID": "12345",
    "X-Client-Version": "2.0.0"
  },
  "remove": ["User-Agent"],
  "replace_name": {
    "X-Old-Auth": "X-New-Auth"
  },
  "replace_value": {
    "X-New-Auth": {
      "search": "Bearer (.+)",
      "replace": "Token $1",
      "regex": true
    }
  }
}
```

## 调试技巧

### 后端日志

```python
import logging
logger = logging.getLogger(__name__)

# 在 apply_header_rules 调用前后添加日志
logger.debug(f"Original headers: {headers}")
logger.debug(f"Applying rules: {rules}")
result = apply_header_rules(headers, rules)
logger.debug(f"Result headers: {result}")
```

### 前端调试

```typescript
// 监听规则变化
watch(headersRules, (newRules) => {
  console.log('Headers rules changed:', JSON.stringify(newRules, null, 2))
}, { deep: true })
```

## 错误处理

### 无效正则表达式

当正则表达式无效时，规则会跳过该替换，返回原值：

```json
{
  "replace_value": {
    "X-Test": {
      "search": "[invalid(regex",
      "replace": "new",
      "regex": true
    }
  }
}
```

**结果**: `X-Test` 保持原值，不会报错

### 规则键冲突

如果同时包含规则键和普通键：

```json
{
  "add": {"X-A": "1"},
  "X-B": "2"  // 这个会被忽略
}
```

**正确写法**:

```json
{
  "add": {
    "X-A": "1",
    "X-B": "2"
  }
}
```

## 性能考虑

1. **规则执行顺序**：规则按固定顺序执行，无法跳过某个步骤
2. **大小写处理**：`remove`、`replace_name`、`replace_value` 的 key 匹配是大小写不敏感的
3. **正则性能**：避免使用复杂正则，可能影响性能
4. **规则数量**：建议单个 endpoint 的规则不超过 20 条

## 迁移检查清单

- [ ] 后端 `header_rules.py` 文件已添加
- [ ] 后端 `header_rule_examples.py` 文件已添加
- [ ] 所有 `headers` 字段类型已改为 `Dict[str, Any]`
- [ ] `request_builder.py` 已集成规则应用
- [ ] `transport.py` 已集成规则应用
- [ ] `endpoint_checker.py` 已集成规则应用
- [ ] 前端 `HeadersRulesEditor.vue` 已添加
- [ ] 前端类型定义已更新
- [ ] `EndpointFormDialog.vue` 已集成编辑器
- [ ] 旧格式数据兼容性测试通过
- [ ] 四种规则类型功能测试通过
- [ ] 规则执行顺序验证通过

---

**最后更新**: 2026-01-10
