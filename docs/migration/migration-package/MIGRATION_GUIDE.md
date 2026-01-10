# 高级 Header 规则处理功能迁移指南

## 概述

本指南详细说明如何将"高级 Header 规则处理"功能从当前项目迁移到上游项目。该功能允许用户通过规则 DSL（领域特定语言）动态修改 HTTP 请求 Headers，支持添加、删除、重命名和替换操作。

**来源提交**:
- `4fff85e` - Docker 数据卷配置更新（可选迁移，见附录）
- `edb3710` - 高级 Header 规则处理和 UI 编辑器（核心功能）

## 功能说明

### 核心能力

1. **Header 规则 DSL**: 将原本简单的 `Dict[str, str]` headers 扩展为支持四种操作的结构化规则
2. **前端可视化编辑器**: 提供直观的 UI 界面配置规则
3. **后端规则引擎**: 解析并应用规则到实际 HTTP 请求
4. **向后兼容**: 自动识别旧格式 headers 并转换为规则格式

### 规则类型

| 规则类型 | 说明 | 示例 |
|---------|------|------|
| `add` | 新增固定的 header（不覆盖已存在的） | `{"add": {"X-Custom": "value"}}` |
| `remove` | 删除指定的 headers（大小写不敏感） | `{"remove": ["User-Agent"]}` |
| `replace_name` | 重命名 header 名称 | `{"replace_name": {"X-Old": "X-New"}}` |
| `replace_value` | 替换 header 的值（支持正则） | `{"replace_value": {"Authorization": {"search": "Bearer", "replace": "Token", "regex": false}}}` |

### 执行顺序

规则按照以下顺序执行（最终效果取决于顺序）：
```
remove → replace_name → replace_value → add
```

---

## 迁移清单

### 阶段 1: 后端核心逻辑（必须）

#### 1.1 新增文件

**文件**: `src/core/header_rules.py`
- **作用**: Header 规则引擎核心实现
- **关键类**:
  - `ReplaceValueRule`: 定义值替换规则模型
  - `HeaderRules`: 定义完整的规则模型
- **关键函数**:
  - `apply_header_rules(headers, rules)`: 应用规则到 headers
  - `validate_header_rules(rules)`: 验证规则格式

**文件**: `src/core/header_rule_examples.py`
- **作用**: 提供规则示例和工具函数
- **内容**: 预定义的常见规则模板（如安全 headers、移除服务器信息等）

#### 1.2 修改文件

**文件**: `src/models/endpoint_models.py`

**修改内容**:
```python
# 修改前
class ProviderEndpointCreate(BaseModel):
    headers: Optional[Dict[str, str]] = None

class ProviderEndpointUpdate(BaseModel):
    headers: Optional[Dict[str, str]] = None

class ProviderEndpointResponse(BaseModel):
    headers: Optional[Dict[str, str]] = None

# 修改后
from typing import Any

class ProviderEndpointCreate(BaseModel):
    headers: Optional[Dict[str, Any]] = None  # 允许规则对象

class ProviderEndpointUpdate(BaseModel):
    headers: Optional[Dict[str, Any]] = None

class ProviderEndpointResponse(BaseModel):
    headers: Optional[Dict[str, Any]] = None
```

**原因**: `headers` 字段需要支持嵌套的规则对象结构，不能仅限于 `Dict[str, str]`

**注意事项**:
- 确保数据库 ORM 层的 `headers` 字段是 JSON/JSONB 类型
- 如果是 SQLAlchemy，应该是 `Column(JSON)` 或 `Column(JSONB)`

---

**文件**: `src/api/handlers/base/request_builder.py`

**修改位置**: `PassthroughRequestBuilder.build_headers()` 方法

**修改内容**:
```python
def build_headers(self) -> Dict[str, str]:
    """
    透传请求头 - 清理敏感头部（黑名单），透传其他所有头部

    支持高级 headers 规则处理（从 endpoint.headers 读取）：
    - add: 新增固定的参数和值
    - remove: 删除指定的参数
    - replace_name: 替换参数名
    - replace_value: 替换参数值
    """
    from src.core.header_rules import apply_header_rules

    # 基础 headers（不含敏感字段）
    headers = self._filter_sensitive_headers(self.incoming_headers)

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

    return headers
```

**关键点**:
- 必须先导入 `apply_header_rules` 函数
- 使用规则键检测来判断是规则对象还是旧格式
- 保持向后兼容

---

**文件**: `src/services/provider/transport.py`

**修改位置**: `build_provider_headers()` 函数

**修改内容**:
```python
def build_provider_headers(
    provider_headers: Dict[str, str],
    endpoint_headers: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    构建 provider 的请求 headers

    支持高级 headers 规则处理
    """
    from src.core.header_rules import apply_header_rules

    headers = dict(provider_headers)

    if not endpoint_headers:
        return headers

    # 检测是否是规则对象
    rule_keys = ['add', 'remove', 'replace_name', 'replace_value']
    has_rules = any(key in endpoint_headers for key in rule_keys)

    if has_rules:
        headers = apply_header_rules(headers, endpoint_headers)
    else:
        # 旧格式：直接合并
        headers.update(endpoint_headers)

    return headers
```

---

**文件**: `src/api/handlers/base/endpoint_checker.py`

**修改位置**: `build_safe_headers()` 函数

**修改内容**:
```python
def build_safe_headers(
    base_headers: Dict[str, str],
    extra_headers: Optional[Dict[str, Any]],  # 改为 Any
    protected_keys: Iterable[str],
) -> Dict[str, str]:
    """
    合并 extra_headers，但防止覆盖 protected_keys（大小写不敏感）。

    支持高级 headers 规则处理：
    - 如果 header_rules 存在，会先应用规则处理 headers
    - 规则包括：add（新增）、remove（删除）、replace_name（改名）、replace_value（改值）
    """
    from src.core.header_rules import apply_header_rules

    headers = dict(base_headers)
    if not extra_headers:
        return headers

    # 应用规则（如果存在）
    headers = apply_header_rules(headers, extra_headers)

    return headers
```

---

### 阶段 2: 前端 UI 组件（必须）

#### 2.1 新增文件

**文件**: `frontend/src/components/ui/dialog/index.ts`
- **作用**: Dialog 组件统一导出点
- **内容**: 导出所有 Dialog 相关子组件

```typescript
export { default as Dialog } from './Dialog.vue'
export { default as DialogContent } from './DialogContent.vue'
export { default as DialogDescription } from './DialogDescription.vue'
export { default as DialogFooter } from './DialogFooter.vue'
export { default as DialogHeader } from './DialogHeader.vue'
export { default as DialogTitle } from './DialogTitle.vue'
```

**迁移注意**:
- 如果目标项目已有类似组件，可以跳过
- 确保组件 API 兼容（`model-value`、`@update:model-value`、`title`、`#footer` slot）

---

**文件**: `frontend/src/features/providers/components/HeadersRulesEditor.vue`
- **作用**: Header 规则的可视化编辑器
- **大小**: 约 530 行
- **依赖组件**:
  - `Dialog`（对话框）
  - `Button`（按钮）
  - `Input`（输入框）
  - `Label`（标签）
  - `Badge`（徽章）
  - `Switch`（开关）
  - 图标库：`lucide-vue-next`（`Plus`、`Trash2`、`Edit3`、`Replace`、`X`、`ArrowRight`、`Settings`）

**TypeScript 类型定义**:
```typescript
type HeaderRules = {
  add?: Record<string, string>
  remove?: string[]
  replace_name?: Record<string, string>
  replace_value?: Record<string, {
    search: string
    replace: string
    regex: boolean
    case_sensitive?: boolean
  }>
}
```

**组件特性**:
- `v-model` 双向绑定规则对象
- 四种规则类型的独立配置对话框
- 规则列表展示和单条删除
- 一键清空所有规则
- 空状态提示

**迁移注意**:
- 如果目标项目 UI 组件库不兼容，需要调整组件实现
- 确保图标库可用，或替换为其他图标库

#### 2.2 修改文件

**文件**: `frontend/src/features/providers/components/EndpointFormDialog.vue`

**修改内容**:

1. **导入 HeadersRulesEditor 组件**:
```typescript
import HeadersRulesEditor from './HeadersRulesEditor.vue'
```

2. **添加 HeaderRules 类型定义**:
```typescript
type HeaderRules = {
  add?: Record<string, string>
  remove?: string[]
  replace_name?: Record<string, string>
  replace_value?: Record<string, {
    search: string
    replace: string
    regex: boolean
    case_sensitive?: boolean
  }>
}
```

3. **表单数据结构添加 headers_rules 字段**:
```typescript
const form = ref({
  // ... 其他字段
  headers_rules: null as HeaderRules | null,
})
```

4. **添加转换函数**（兼容旧格式）:
```typescript
function convertHeadersToRules(headers: Record<string, string> | null): HeaderRules | null {
  if (!headers) return null

  // 检查是否已经是新格式（包含规则键）
  const ruleKeys = ['add', 'remove', 'replace_name', 'replace_value']
  const hasRuleKeys = Object.keys(headers).some(key => ruleKeys.includes(key))

  if (hasRuleKeys) {
    // 已经是新格式，直接返回
    return headers as unknown as HeaderRules
  }

  // 旧格式：直接的 headers 字典，转换为 add 规则
  return {
    add: { ...headers }
  }
}
```

5. **在表单模板中添加规则编辑器**:
```vue
<!-- Headers 规则配置 -->
<div class="space-y-4">
  <div class="flex items-center justify-between">
    <div>
      <h3 class="text-sm font-medium">Headers 规则</h3>
      <p class="text-xs text-muted-foreground">
        配置请求 Headers 的添加、删除、重命名和替换规则
      </p>
    </div>
  </div>

  <div class="rounded-lg border p-4">
    <HeadersRulesEditor v-model="form.headers_rules" />
  </div>
</div>
```

6. **加载 endpoint 数据时转换 headers**:
```typescript
function loadEndpointData() {
  // ... 其他字段
  headers_rules: convertHeadersToRules(props.endpoint.headers),
}
```

7. **提交时将 headers_rules 写回 headers 字段**:
```typescript
const handleSubmit = async (skipCredentialCheck = false) => {
  const submitData = {
    // ... 其他字段
    // 注意：如果要清空 headers，必须显式传 null（不能是 undefined）
    headers: form.value.headers_rules || undefined,
  }
  // ... 提交逻辑
}
```

**重要提示**:
- `headers: undefined` - 不会覆盖旧值（Pydantic `exclude_unset=True`）
- `headers: null` - 会清空 headers（包括规则）

---

### 阶段 3: 前端类型定义（强烈建议）

**文件**: `frontend/src/api/endpoints/types.ts`

**修改内容**:

```typescript
// 定义 Header 规则类型
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

// Union 类型：兼容旧格式和新格式
export type EndpointHeadersConfig = Record<string, string> | HeaderRules

// 修改 ProviderEndpoint 类型
export interface ProviderEndpoint {
  id: string
  name: string
  // ... 其他字段
  headers?: EndpointHeadersConfig | null  // 改为 union 类型
}
```

**文件**: `frontend/src/api/endpoints/endpoints.ts`

**修改内容**:

```typescript
import type { EndpointHeadersConfig } from './types'

// 创建和更新接口的 headers 字段类型
export interface CreateEndpointRequest {
  // ... 其他字段
  headers?: EndpointHeadersConfig | null
}

export interface UpdateEndpointRequest {
  // ... 其他字段
  headers?: EndpointHeadersConfig | null
}
```

**重要提示**:
- 更新接口若要"清空" headers（包括规则），应显式发 `headers: null`
- 发送 `undefined` 不会覆盖旧值（因为 Pydantic 使用 `exclude_unset=True`）

---

### 阶段 4: 测试（强烈建议）

**新建文件**: `tests/core/test_header_rules.py`

```python
import pytest
from src.core.header_rules import apply_header_rules, HeaderRules, validate_header_rules

class TestApplyHeaderRules:
    """测试 header 规则应用"""

    def test_old_format_compatibility(self):
        """测试旧格式自动转换为 add 规则"""
        headers = {"Content-Type": "application/json"}
        old_rules = {"X-Custom": "value"}
        result = apply_header_rules(headers, old_rules)
        assert result["X-Custom"] == "value"
        assert result["Content-Type"] == "application/json"

    def test_remove_rule(self):
        """测试删除规则"""
        headers = {"User-Agent": "bot", "Authorization": "Bearer token"}
        rules = {"remove": ["user-agent"]}  # 大小写不敏感
        result = apply_header_rules(headers, rules)
        assert "User-Agent" not in result
        assert "Authorization" in result

    def test_replace_name_rule(self):
        """测试重命名规则"""
        headers = {"X-Old-Name": "value"}
        rules = {"replace_name": {"X-Old-Name": "X-New-Name"}}
        result = apply_header_rules(headers, rules)
        assert "X-Old-Name" not in result
        assert result["X-New-Name"] == "value"

    def test_replace_value_string(self):
        """测试字符串替换"""
        headers = {"Authorization": "Bearer old_token"}
        rules = {
            "replace_value": {
                "Authorization": {
                    "search": "old_token",
                    "replace": "new_token",
                    "regex": False
                }
            }
        }
        result = apply_header_rules(headers, rules)
        assert result["Authorization"] == "Bearer new_token"

    def test_replace_value_regex(self):
        """测试正则替换"""
        headers = {"User-Agent": "MyApp/1.0.0"}
        rules = {
            "replace_value": {
                "User-Agent": {
                    "search": r"MyApp/\d+\.\d+\.\d+",
                    "replace": "MyApp/2.0.0",
                    "regex": True
                }
            }
        }
        result = apply_header_rules(headers, rules)
        assert result["User-Agent"] == "MyApp/2.0.0"

    def test_execution_order(self):
        """测试规则执行顺序：remove → replace_name → replace_value → add"""
        headers = {
            "X-Remove-Me": "gone",
            "X-Old-Name": "value1",
            "X-Replace-Value": "old"
        }
        rules = {
            "remove": ["X-Remove-Me"],
            "replace_name": {"X-Old-Name": "X-New-Name"},
            "replace_value": {
                "X-Replace-Value": {"search": "old", "replace": "new", "regex": False}
            },
            "add": {"X-New-Header": "added"}
        }
        result = apply_header_rules(headers, rules)

        assert "X-Remove-Me" not in result
        assert "X-Old-Name" not in result
        assert result["X-New-Name"] == "value1"
        assert result["X-Replace-Value"] == "new"
        assert result["X-New-Header"] == "added"

    def test_case_insensitive_matching(self):
        """测试大小写不敏感匹配"""
        headers = {"User-Agent": "bot"}
        rules = {"remove": ["user-agent"]}  # 小写
        result = apply_header_rules(headers, rules)
        assert "User-Agent" not in result

    def test_invalid_regex_fallback(self):
        """测试无效正则的降级行为"""
        headers = {"X-Test": "value"}
        rules = {
            "replace_value": {
                "X-Test": {
                    "search": "[invalid(regex",  # 无效正则
                    "replace": "new",
                    "regex": True
                }
            }
        }
        result = apply_header_rules(headers, rules)
        # 正则失败时应返回原值
        assert result["X-Test"] == "value"

    def test_add_does_not_override(self):
        """测试 add 规则不覆盖已存在的 header（大小写敏感）"""
        headers = {"authorization": "existing"}
        rules = {"add": {"Authorization": "new"}}
        result = apply_header_rules(headers, rules)
        # 大小写不同，被视为不同 key
        assert result["authorization"] == "existing"
        assert result["Authorization"] == "new"


class TestValidateHeaderRules:
    """测试规则验证"""

    def test_valid_rules(self):
        """测试有效规则"""
        rules = {
            "add": {"X-Custom": "value"},
            "remove": ["User-Agent"],
            "replace_name": {"X-Old": "X-New"},
            "replace_value": {
                "Auth": {"search": "a", "replace": "b", "regex": False}
            }
        }
        assert validate_header_rules(rules) is True

    def test_invalid_rules(self):
        """测试无效规则"""
        rules = {"invalid_key": "value"}
        assert validate_header_rules(rules) is False
```

---

## 数据库迁移（可选）

### 检查数据库字段类型

如果上游项目的 `headers` 字段不是 JSON 类型，需要进行迁移：

```sql
-- PostgreSQL 示例
ALTER TABLE provider_endpoints
ALTER COLUMN headers TYPE JSONB USING headers::JSONB;

-- MySQL 示例
ALTER TABLE provider_endpoints
MODIFY COLUMN headers JSON;
```

### 数据迁移脚本（如果需要）

如果数据库中已有旧格式的 headers 数据，确保它们能继续正常工作：
- 旧格式会自动被 `apply_header_rules` 识别并转换为 `add` 规则
- 无需手动迁移数据

---

## 潜在问题和解决方案

### 问题 1: 保留字冲突

**场景**: 用户想配置名为 `add`、`remove` 等的 header

**影响**: 会被误判为规则对象，导致解析失败

**解决方案**:
- 在迁移说明中明确约束：顶层只允许规则键
- 如果确实需要配置这些 header，可以通过 `add` 规则添加（但由于规则键检测，会有限制）
- 考虑未来版本使用更明确的规则标识（如 `$rules` 包装）

### 问题 2: 规则键与普通键混用

**场景**: `{"add": {"X-A": "1"}, "X-B": "2"}`

**影响**: `X-B` 会被 Pydantic 的 `extra=ignore` 丢弃

**解决方案**:
- 明确规定：所有普通 headers 必须放在 `add` 里
- 正确写法：`{"add": {"X-A": "1", "X-B": "2"}}`

### 问题 3: 大小写敏感的"不覆盖"逻辑

**场景**: `headers` 中同时存在 `Authorization` 和 `authorization`

**影响**: `add` 规则的"不覆盖"是大小写敏感的，可能导致重复键

**解决方案**:
- 大多数 HTTP 库会规范化 header 名称，实际影响较小
- 可以在 `apply_header_rules` 中增加规范化逻辑（可选）

### 问题 4: 前端类型不匹配

**场景**: API 返回的 headers 是规则对象，但 TypeScript 类型仍定义为 `Record<string, string>`

**影响**: 类型检查报错，或运行时访问不存在的属性

**解决方案**:
- 必须更新 TypeScript 类型定义为 `EndpointHeadersConfig`（union 类型）
- 在所有使用 headers 的地方添加类型守卫（如果需要）

---

## 验收清单

迁移完成后，请验证以下功能点：

### 后端验证

- [ ] `header_rules.py` 文件存在且无语法错误
- [ ] `header_rule_examples.py` 文件存在
- [ ] 所有相关文件的 `headers` 字段类型已改为 `Dict[str, Any]`
- [ ] `request_builder.py` 正确调用 `apply_header_rules`
- [ ] `transport.py` 正确调用 `apply_header_rules`
- [ ] `endpoint_checker.py` 正确调用 `apply_header_rules`
- [ ] 旧格式 headers 仍能正常工作（向后兼容）

### 前端验证

- [ ] `HeadersRulesEditor.vue` 组件存在且可正常使用
- [ ] `EndpointFormDialog.vue` 集成了规则编辑器
- [ ] TypeScript 类型定义已更新为 `EndpointHeadersConfig`
- [ ] 旧数据能正确转换为新格式显示
- [ ] 新规则能正确保存到后端
- [ ] 规则编辑器 UI 交互正常

### 功能验证

- [ ] 创建 endpoint 时能配置规则
- [ ] 更新 endpoint 时能修改规则
- [ ] 规则正确应用到实际 HTTP 请求
- [ ] 四种规则类型都能正常工作
- [ ] 规则执行顺序正确
- [ ] 大小写不敏感匹配正常
- [ ] 正则替换功能正常
- [ ] 无效正则时降级处理正常

---

## 相关文件清单

### 后端文件

**新增**:
- `src/core/header_rules.py` (237 行)
- `src/core/header_rule_examples.py` (336 行)

**修改**:
- `src/models/endpoint_models.py` (修改 headers 字段类型)
- `src/api/handlers/base/request_builder.py` (添加规则应用逻辑)
- `src/services/provider/transport.py` (添加规则应用逻辑)
- `src/api/handlers/base/endpoint_checker.py` (添加规则应用逻辑)

### 前端文件

**新增**:
- `frontend/src/components/ui/dialog/index.ts` (6 行)
- `frontend/src/features/providers/components/HeadersRulesEditor.vue` (532 行)

**修改**:
- `frontend/src/features/providers/components/EndpointFormDialog.vue` (集成规则编辑器)
- `frontend/src/api/endpoints/types.ts` (更新类型定义)
- `frontend/src/api/endpoints/endpoints.ts` (更新类型定义)

### 测试文件（建议）

**新增**:
- `tests/core/test_header_rules.py` (约 150 行建议)

---

## 版本兼容性

### 后端
- Python 3.8+
- Pydantic v2
- SQLAlchemy（ORM 层）
- JSON/JSONB 数据库字段类型

### 前端
- Vue 3
- TypeScript 4+
- UI 组件库（Button、Dialog、Input、Label、Badge、Switch）
- lucide-vue-next（或其他图标库）

---

## 回滚方案

如果迁移后出现问题，可以：

1. **保留代码，禁用功能**: 在 API 层拦截规则对象，返回错误提示
2. **部分回滚**: 保留 `apply_header_rules`，但移除前端 UI
3. **完全回滚**: 恢复所有文件到迁移前状态，数据库无需回滚（向后兼容）

---

## 后续优化建议

1. **增加规则测试覆盖**: 补充单元测试和集成测试
2. **规则预览功能**: 在前端展示规则应用后的效果
3. **规则模板**: 提供常见场景的预设规则模板
4. **规则验证增强**: 前端实时验证规则格式
5. **规则导入导出**: 支持 JSON 格式的规则导入导出
6. **规则版本管理**: 支持规则的版本历史和回滚

---

## 联系方式

如有迁移问题，请参考以下资源：

- 原始提交: `git show edb3710`
- 核心实现: `src/core/header_rules.py`
- 迁移包文档: 包含在本迁移包中

---

## 附录：Docker 数据卷配置迁移（可选）

### 背景

提交 `4fff85e` 更新了 Docker Compose 配置，将命名卷（named volumes）改为本地目录挂载。这一改动主要是为了方便整体迁移数据。

### 修改内容

**文件**: `docker-compose.yml`

**修改前**:
```yaml
volumes:
  postgres_data:
  redis_data:

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    volumes:
      - redis_data:/data

  nginx:
    volumes:
      - ./logs:/app/logs
```

**修改后**:
```yaml
# 移除 volumes 声明

services:
  postgres:
    volumes:
      - ./site/pgsql:/var/lib/postgresql/data

  redis:
    volumes:
      - ./site/redis:/data

  nginx:
    volumes:
      - ./:/app
      - ./frontend/dist:/usr/share/nginx/html
```

### 是否需要迁移？

**不需要迁移的情况**:
- 如果上游项目的 Docker 配置已经满足需求
- 如果不使用 Docker 部署

**需要迁移的情况**:
- 如果希望数据更容易备份和迁移
- 如果需要直接访问数据库文件

### 迁移步骤

1. **备份数据**:
```bash
# 备份 PostgreSQL 数据
docker exec aether-postgres pg_dump -U postgres > backup.sql

# 备份 Redis 数据
docker exec aether-redis redis-cli --rdb /data/backup.rdb
```

2. **停止服务**:
```bash
docker-compose down
```

3. **创建目录**:
```bash
mkdir -p site/pgsql site/redis
```

4. **迁移数据**:
```bash
# 从命名卷迁移到目录
docker run --rm -v aether_postgres_data:/source -v $(pwd)/site/pgsql:/target alpine \
  sh -c "cp -a /source/. /target/"

docker run --rm -v aether_redis_data:/source -v $(pwd)/site/redis:/target alpine \
  sh -c "cp -a /source/. /target/"
```

5. **更新 docker-compose.yml**:
按照上面的"修改后"配置更新

6. **重启服务**:
```bash
docker-compose up -d
```

7. **验证数据**:
```bash
# 检查 PostgreSQL
docker exec -it aether-postgres psql -U postgres -c "\l"

# 检查 Redis
docker exec -it aether-redis redis-cli INFO
```

### 回滚方案

如果需要回滚到命名卷：

1. 停止服务
2. 恢复 docker-compose.yml 的 volumes 配置
3. 从目录迁移数据回命名卷
4. 重启服务

---

---

**最后更新**: 2026-01-10
**版本**: 1.0
**作者**: Claude Code + Codex 协作
