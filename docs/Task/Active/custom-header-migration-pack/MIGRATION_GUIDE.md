# Custom Headers 功能迁移指南

## 概述

本分支（`custom-header`）实现了一套完整的 **自定义 Headers 规则系统**，允许用户对 Provider Endpoint 的请求头进行精细化控制。该功能包含后端规则处理引擎、前端可视化编辑器、以及自动获取模型列表的能力。

---

## 一、核心功能说明

### 1.1 Headers 规则系统

支持四种操作类型的 Headers 规则：

| 操作类型 | 功能描述 | 示例 |
|---------|---------|------|
| `add` | 新增请求头（不会覆盖已存在的 header） | `{"add": {"X-Custom": "value"}}` |
| `remove` | 删除指定的请求头（大小写不敏感） | `{"remove": ["User-Agent"]}` |
| `replace_name` | 重命名请求头 | `{"replace_name": {"X-Old": "X-New"}}` |
| `replace_value` | 替换请求头的值（支持正则） | `{"replace_value": {"UA": {"search": "old", "replace": "new", "regex": true}}}` |

### 1.2 兼容性设计

- **向后兼容**：旧的直接 headers 格式（`{"X-Header": "value"}`）自动转换为 `add` 规则
- **安全规则**：自定义 headers 不能覆盖敏感头部（Authorization、X-API-Key 等）
- **认证保护**：系统自动设置的认证头始终优先

### 1.3 自动获取模型

新增 `auto_fetch_models` 功能，可自动从上游 API 获取可用模型列表并更新 Key 的 allowed_models。

---

## 二、后端修改清单

### 2.1 新增文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/header_rules.py` | Headers 规则处理核心引擎 |
| `src/core/header_rule_examples.py` | 规则配置示例和工具函数 |
| `src/services/model/fetch_scheduler.py` | 模型自动获取调度器 |

### 2.2 修改文件详情

#### 2.2.1 数据模型 (`src/models/endpoint_models.py`)

**修改内容**：将 `headers` 字段类型从 `Dict[str, str]` 改为 `Dict[str, Any]`

```python
# 修改前
headers: Optional[Dict[str, str]] = Field(default=None, description="自定义请求头")

# 修改后
headers: Optional[Dict[str, Any]] = Field(default=None, description="自定义请求头（支持规则格式）")
```

**添加验证器**：
```python
@field_validator("headers")
@classmethod
def validate_headers(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """验证 headers 字段中的 header name 是否符合 HTTP 规范"""
    if v is None:
        return v

    # 检查是否是旧格式（直接的 headers 字典）
    if not any(key in v for key in ["add", "remove", "replace_name", "replace_value"]):
        from src.core.header_rules import validate_header_names_in_dict
        validate_header_names_in_dict(v, "headers")
    else:
        from src.core.header_rules import HeaderRules
        try:
            HeaderRules(**v)
        except Exception as e:
            raise ValueError(f"Headers 配置无效: {e}")

    return v
```

**需要修改的类**：
- `ProviderEndpointCreate`
- `ProviderEndpointUpdate`
- `ProviderEndpointResponse`

#### 2.2.2 ProviderAPIKey 模型 (`src/models/endpoint_models.py`)

**新增字段**：
```python
# 自动获取模型
auto_fetch_models: bool = Field(
    default=False, description="是否启用自动获取模型"
)

# 锁定的模型列表
locked_models: Optional[List[str]] = Field(
    default=None, description="被锁定的模型列表（刷新时不会被删除）"
)

# 最后获取时间
last_models_fetch_at: Optional[datetime] = Field(None, description="最后获取模型时间")

# 最后获取错误
last_models_fetch_error: Optional[str] = Field(None, description="最后获取模型错误信息")
```

**需要修改的类**：
- `EndpointAPIKeyCreate`
- `EndpointAPIKeyUpdate`
- `EndpointAPIKeyResponse`

#### 2.2.3 请求构建器 (`src/api/handlers/base/request_builder.py`)

**修改内容**：统一使用 `transport.build_provider_headers` 处理请求头

```python
# 修改前（约 40 行独立的头部处理逻辑）
def passthrough_headers(self, ...) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    # ... 各种头部处理逻辑
    return headers

# 修改后
def passthrough_headers(self, ...) -> Dict[str, str]:
    from src.services.provider.transport import build_provider_headers
    return build_provider_headers(
        endpoint=endpoint,
        key=key,
        original_headers=original_headers,
        extra_headers=extra_headers,
    )
```

#### 2.2.4 传输层 (`src/services/provider/transport.py`)

**修改内容**：在 `build_provider_headers` 函数中集成规则处理

```python
# 在文件顶部添加导入
from src.core.header_rules import apply_header_rules

# 在 build_provider_headers 函数中，合并完所有 headers 后添加：
if endpoint.headers:
    headers = apply_header_rules(headers, endpoint.headers)
    # 保护认证头不被规则覆盖
    if saved_auth_header is not None:
        headers[auth_header] = saved_auth_header

# 安全规则：自定义 headers 不能覆盖敏感头部
excluded_headers = {
    "host", "authorization", "x-api-key", "x-goog-api-key",
    "content-length", "transfer-encoding", "connection", "accept-encoding",
}
for name in list(headers.keys()):
    if name.lower() in excluded_headers:
        headers.pop(name, None)
if saved_auth_header is not None:
    headers[auth_header] = saved_auth_header
```

#### 2.2.5 应用启动 (`src/main.py`)

**修改内容**：添加模型自动获取调度器

```python
# 在导入区域添加
from src.services.model.fetch_scheduler import get_model_fetch_scheduler

# 在 lifespan 函数中，启动阶段添加
model_fetch_scheduler = get_model_fetch_scheduler()

# 启动调度器
model_fetch_scheduler_active = await task_coordinator.acquire("model_fetch_scheduler")
if model_fetch_scheduler_active:
    logger.info("启动模型自动获取调度器...")
    await model_fetch_scheduler.start()
else:
    logger.info("检测到其他 worker 已运行模型获取调度器，本实例跳过")
    model_fetch_scheduler = None

# 在关闭阶段添加
if model_fetch_scheduler:
    logger.info("停止模型自动获取调度器...")
    await model_fetch_scheduler.stop()
    await task_coordinator.release("model_fetch_scheduler")
```

#### 2.2.6 数据库迁移

需要添加数据库迁移文件，新增以下字段到 `provider_api_keys` 表：
- `auto_fetch_models` (BOOLEAN, DEFAULT FALSE)
- `locked_models` (JSONB, DEFAULT NULL)
- `last_models_fetch_at` (TIMESTAMP, DEFAULT NULL)
- `last_models_fetch_error` (VARCHAR, DEFAULT NULL)

---

## 三、前端修改清单

### 3.1 新增组件

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/features/providers/components/EndpointHeadersDialog.vue` | Endpoint Headers 配置对话框 |
| `frontend/src/features/providers/components/HeadersRulesEditor.vue` | Headers 规则可视化编辑器 |
| `frontend/src/features/providers/utils/headerKeys.ts` | Headers 工具函数 |
| `frontend/src/features/providers/utils/__tests__/headerKeys.spec.ts` | 工具函数单元测试 |

### 3.2 修改组件详情

#### 3.2.1 EndpointFormDialog.vue

**修改内容**：添加"配置 Headers"按钮

```vue
<!-- 在 Endpoint 表单中添加按钮 -->
<Button
  variant="outline"
  size="sm"
  @click="openHeadersDialog(endpoint)"
>
  <Settings class="mr-2 h-4 w-4" />
  配置 Headers
</Button>

<!-- 添加对话框 -->
<EndpointHeadersDialog
  v-model:open="headersDialogOpen"
  :endpoint="currentEndpoint"
  @saved="handleHeadersSaved"
/>
```

#### 3.2.2 ProviderDetailDrawer.vue

**修改内容**：
1. 添加自动获取模型状态显示
2. 修复 `quota_reset_day` 显示文案（从"每月X号"改为"每X天"）
3. 重构模型映射预览为独立组件 `ModelMappingTab.vue`

```vue
<!-- 在 Key 列表中添加状态显示 -->
<template v-if="key.auto_fetch_models">
  <span class="text-muted-foreground/40">|</span>
  <span
    class="cursor-help"
    :class="key.last_models_fetch_error ? 'text-amber-600 dark:text-amber-400' : ''"
    :title="getAutoFetchStatusTitle(key)"
  >
    {{ key.last_models_fetch_error ? '同步失败' : '自动同步' }}
  </span>
</template>
```

#### 3.2.3 KeyFormDialog.vue

**修改内容**：添加 `auto_fetch_models` 和 `locked_models` 字段编辑

```vue
<!-- 在表单中添加 -->
<div class="space-y-2">
  <div class="flex items-center space-x-2">
    <Switch id="auto-fetch" v-model="form.auto_fetch_models" />
    <Label for="auto-fetch" class="cursor-pointer">
      启用自动获取模型
    </Label>
  </div>
  <p class="text-xs text-muted-foreground">
    启用后系统将定期从上游 API 获取可用模型列表
  </p>
</div>

<div class="space-y-2">
  <Label>锁定模型</Label>
  <Textarea
    v-model="lockedModelsText"
    placeholder="每行一个模型名称，锁定的模型在刷新时不会被删除"
    class="min-h-[80px]"
  />
</div>
```

#### 3.2.4 API 类型定义 (`frontend/src/api/endpoints/types.ts`)

**修改内容**：扩展类型定义

```typescript
// ProviderEndpoint 类型
export interface ProviderEndpoint {
  // ... 现有字段
  headers?: Record<string, string> | HeaderRules  // 支持两种格式
}

// HeaderRules 类型
export interface HeaderRules {
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

// ProviderAPIKey 类型新增字段
export interface ProviderAPIKey {
  // ... 现有字段
  auto_fetch_models?: boolean
  locked_models?: string[]
  last_models_fetch_at?: string
  last_models_fetch_error?: string
}
```

---

## 四、迁移步骤

### 步骤 1：复制核心规则文件

```bash
# 复制核心规则引擎
cp src/core/header_rules.py <目标项目>/src/core/
cp src/core/header_rule_examples.py <目标项目>/src/core/
```

### 步骤 2：复制调度器

```bash
# 复制模型获取调度器
cp src/services/model/fetch_scheduler.py <目标项目>/src/services/model/
```

### 步骤 3：修改数据模型

在 `<目标项目>/src/models/endpoint_models.py` 中：

1. 修改 `headers` 字段类型为 `Dict[str, Any]`
2. 添加 `validate_headers` 验证器
3. 添加 `auto_fetch_models`、`locked_models` 等字段

### 步骤 4：修改请求处理

在 `<目标项目>/src/api/handlers/base/request_builder.py` 中：

将 `passthrough_headers` 方法改为调用 `build_provider_headers`

### 步骤 5：修改传输层

在 `<目标项目>/src/services/provider/transport.py` 中：

1. 添加 `from src.core.header_rules import apply_header_rules`
2. 在 `build_provider_headers` 函数中集成规则处理

### 步骤 6：修改应用启动

在 `<目标项目>/src/main.py` 中：

添加模型自动获取调度器的启动和关闭逻辑

### 步骤 7：数据库迁移

创建 Alembic 迁移文件添加新字段

### 步骤 8：前端组件迁移

```bash
# 复制前端组件
cp frontend/src/features/providers/components/EndpointHeadersDialog.vue <目标项目>/frontend/src/features/providers/components/
cp frontend/src/features/providers/components/HeadersRulesEditor.vue <目标项目>/frontend/src/features/providers/components/
cp frontend/src/features/providers/utils/headerKeys.ts <目标项目>/frontend/src/features/providers/utils/
cp frontend/src/features/providers/utils/__tests__/headerKeys.spec.ts <目标项目>/frontend/src/features/providers/utils/__tests__/
```

### 步骤 9：前端类型定义

更新 `<目标项目>/frontend/src/api/endpoints/types.ts` 中的类型定义

### 步骤 10：前端组件集成

在 `EndpointFormDialog.vue`、`ProviderDetailDrawer.vue`、`KeyFormDialog.vue` 中集成新功能

---

## 五、依赖关系图

```
header_rules.py (核心引擎)
    ├─> 被以下模块调用:
    │   ├─> endpoint_models.py (验证器)
    │   ├─> transport.py (应用规则)
    │   └─> request_builder.py (间接调用)
    │
header_rule_examples.py (示例和工具)
    └─> 可选，用于文档和测试

fetch_scheduler.py (自动获取)
    ├─> main.py (启动/停止)
    └─> adapter_base.py (fetch_models 接口)

前端组件:
    ├─> EndpointHeadersDialog.vue
    ├─> HeadersRulesEditor.vue
    └─> headerKeys.ts
```

---

## 六、测试验证

### 后端测试

1. 测试旧格式 headers 兼容性
2. 测试新格式四种规则类型
3. 测试敏感头部保护
4. 测试自动获取模型功能

### 前端测试

1. 测试规则编辑器各操作
2. 测试保存和加载
3. 测试错误验证
4. 测试状态显示

---

## 七、注意事项

1. **向后兼容**：旧格式的 headers 会自动转换，不会影响现有配置
2. **安全保护**：自定义 headers 永远不能覆盖认证头等敏感字段
3. **性能考虑**：规则处理在每次请求时执行，保持规则简单高效
4. **数据库迁移**：新增字段有默认值，现有数据不受影响
5. **调度器启动**：使用 task_coordinator 确保多 worker 环境下只启动一个实例
