# 高级 Header 规则处理功能 - 迁移任务计划

## 任务概述

**任务名称**: 高级 Header 规则处理功能迁移
**创建时间**: 2026-01-11
**创建人**: Claude + Codex
**状态**: ✅ 已完成 (完成时间: 2026-01-11)

## 背景和目标

### 背景
当前项目的 Header 处理功能较为简单，仅支持固定的 `Dict[str, str]` 格式。需要迁移高级 Header 规则处理功能，支持更灵活的 Header 操作：

- **add**: 添加新的 Header
- **remove**: 删除指定 Header
- **replace_name**: 重命名 Header
- **replace_value**: 替换 Header 的值

### 目标
1. 实现完整的 Header 规则引擎（后端）
2. 提供可视化的规则编辑器（前��）
3. 保持向后兼容性（旧格式自动转换）
4. 确保不影响现有功能

## 需求分析（Codex 协作完成）

### 环境检查 ✅
- **后端**: Python 3.9+, Pydantic v2 ✅
- **前端**: Vue 3.5, TypeScript 5.8.3, lucide-vue-next ✅
- **数据库**: 需确认 `provider_endpoints.headers` 为 JSON/JSONB 类型

### 项目结构分析
- **后端核心目录**: `src/core/` (当前无 header 规则相关文件)
- **前端组件目录**: `frontend/src/features/providers/components/`
- **后端需要修改的文件**:
  - `src/models/endpoint_models.py` (headers 类型定义)
  - `src/api/handlers/base/request_builder.py` (请求构建)
  - `src/services/provider/transport.py` (Header 合并)
  - `src/api/handlers/base/endpoint_checker.py` (安全过滤)

- **前端需要修改的文件**:
  - `frontend/src/features/providers/components/EndpointFormDialog.vue` (表单集成)
  - `frontend/src/api/endpoints/types.ts` (类型定义)

### 风险评估

| 风险项 | 影响 | 缓解措施 |
|--------|------|----------|
| 类型放宽可能影响现有逻辑 | 中 | 确认所有依赖 headers 的代码能处理新格式 |
| 规则执行顺序错误 | 高 | 严格按照 remove → rename → replace → add 顺序执行 |
| 前端类型不匹配 | 中 | 统一更新类型定义和接口调用 |
| 组件导出冲突 | 低 | 检查 index.ts 是否需要更新聚合导出 |
| 旧数据兼容性 | 中 | 实现自动转换逻辑，确保旧格式正常工作 |

## 任务分解

### 阶段 1: 后端核心逻辑迁移 ⏳

#### 1.1 新增核心文件
- [ ] 复制 `header_rules.py` → `src/core/header_rules.py`
  - 核心函数: `apply_header_rules()`, `validate_header_rules()`
  - 数据模型: `HeaderRule`, `HeaderRules`
- [ ] 复制 `header_rule_examples.py` → `src/core/header_rule_examples.py`
  - 示例规则和工具函数

#### 1.2 修改数据模型
**文件**: `src/models/endpoint_models.py`

**修改位置**:
- 第 24 行: `EndpointHeadersConfig` 定义
- 第 63 行: `ProviderEndpointCreate.headers`
- 第 96 行: `ProviderEndpointUpdate.headers`

**修改内容**:
```python
# 从:
headers: Dict[str, str] = Field(default_factory=dict)

# 改为:
headers: Dict[str, Any] = Field(default_factory=dict)
```

同时添加 `Any` 导入: `from typing import Any, Dict`

#### 1.3 集成规则引擎到请求构建
**文件**: `src/api/handlers/base/request_builder.py`

**修改位置**: 第 130-181 行 `build_headers` 方法

**修改内容**:
- 导入 `apply_header_rules`
- 检测 headers 中是否包含规则键 (`add/remove/replace_name/replace_value`)
- 如果包含规则，使用 `apply_header_rules()` 处理
- 保留旧格式兼容逻辑

#### 1.4 集成到传输层
**文件**: `src/services/provider/transport.py`

**修改位置**: 第 22-72 行 Header 合并逻辑

**修改内容**:
- 在合并 endpoint 和 original headers 时应用规则
- 确保规则执行顺序正确

#### 1.5 更新安全过滤
**文件**: `src/api/handlers/base/endpoint_checker.py`

**修改位置**: 第 59-74 行

**修改内容**:
- 支持规则格式的同时尊重受保护键
- 确保敏感头不被规则覆盖

#### 1.6 数据库验证
- [ ] 确认 `provider_endpoints.headers` 字段为 JSON/JSONB 类型
- [ ] 如不是，执行数据库迁移

---

### 阶段 2: 前端 UI 组件迁移 ⏳

#### 2.1 新增前端文件
- [ ] 复制 `HeadersRulesEditor.vue` → `frontend/src/features/providers/components/HeadersRulesEditor.vue`
  - 可视化规则编辑器组件
- [ ] 复制 `dialog_index.ts` → `frontend/src/components/ui/dialog/index.ts`
  - Dialog 组件统一导出

#### 2.2 集成到表单组件
**文件**: `frontend/src/features/providers/components/EndpointFormDialog.vue`

**修改内容**:
1. **导入组件和类型**:
   ```vue
   import HeadersRulesEditor from './HeadersRulesEditor.vue'
   import type { HeaderRules, EndpointHeadersConfig } from '@/api/endpoints/types'
   ```

2. **添加表单字段**:
   ```ts
   headers_rules: ref<HeaderRules>({ add: [], remove: [], replace_name: [], replace_value: [] })
   ```

3. **转换逻辑**:
   - 旧 headers → add 规则
   - 规则 → 提交格式

4. **模板集成**:
   - 添加规则编辑器 UI 块

#### 2.3 检查组件导出
- [ ] 确认 `frontend/src/components/ui/index.ts` 是否需要更新
- [ ] 确保 Dialog 组件可正确导入

---

### 阶段 3: 前端类型定义更新 ⏳

#### 3.1 更新类型定义
**文件**: `frontend/src/api/endpoints/types.ts`

**修改内容**:
1. 添加新类型:
   ```ts
   export interface HeaderReplaceValueRule {
     pattern: string
     search: string
     replace: string
     ignore_case?: boolean
   }

   export interface HeaderRules {
     add: Record<string, string>
     remove: string[]
     replace_name: Record<string, string>
     replace_value: HeaderReplaceValueRule[]
   }

   export type EndpointHeadersConfig = Record<string, string> | HeaderRules
   ```

2. 更新 `ProviderEndpoint` 类型:
   ```ts
   headers: EndpointHeadersConfig
   ```

#### 3.2 更新 API 调用
**文件**: `frontend/src/api/endpoints/endpoints.ts`

**修改内容**:
- create/update 方法接受 `EndpointHeadersConfig` 类型

#### 3.3 类型检查
- [ ] 运行 `npm run type-check` 或 `npx tsc --noEmit`
- [ ] 修复所有类型错误

---

### 阶段 4: 测试与验证 ⏳

#### 4.1 后端单元测试
- [ ] 为 `apply_header_rules()` 添加测试
  - 覆盖 remove/rename/replace/add
  - 测试大小写处理
  - 测试旧格式回退
- [ ] 为 `build_headers()`/`build_provider_headers()` 添加集成测试
  - 敏感头过滤 + 规则应用
- [ ] 运行 `pytest tests`

#### 4.2 前端单元测试
- [ ] 为 `HeadersRulesEditor.vue` 添加测试
  - 规则键识别
  - 旧 headers → add 规则转换
  - 提交 payload 格式
- [ ] 为表单转换逻辑添加测试
- [ ] 运行 `npm test`

#### 4.3 手动验收测试
使用 `MIGRATION_GUIDE.md` 中的验收清单:

- [ ] 创建新 endpoint，使用规则格式
- [ ] 更新已有 endpoint，验证规则生效
- [ ] 测试旧格式兼容性（直接使用 headers dict）
- [ ] 验证规则执行顺序（remove → rename → replace → add）
- [ ] 测试敏感头保护（规则不能覆盖认证头）
- [ ] 测试大小写不敏感匹配
- [ ] 验证 UI 正常显示和编辑规则

#### 4.4 接口测试
- [ ] 抓包验证请求头按规则生成
- [ ] 测试各种规则组合

---

## 验收标准

### 功能验收
- [x] 后端能接受/存储/返回包含规则对象的 headers
- [ ] 旧格式依然可正常透传（向后兼容）
- [ ] `apply_header_rules` 在正确顺序下行为正确
- [ ] 敏感头不被规则覆盖
- [ ] 前端表单可查看/编辑/保存规则
- [ ] 旧 endpoint 数据转换后 UI 不报错

### 技术验收
- [ ] 所有单元测试通过
- [ ] 无 TypeScript 类型错误
- [ ] 无 Pydantic 验证错误
- [ ] 代码符合项目规范

---

## 参考资料

### 迁移包文件
- 📄 `docs/migration/migration-package/README.md` - 使用说明
- 📄 `docs/migration/migration-package/MIGRATION_GUIDE.md` - 详细迁移指南
- 📄 `docs/migration/migration-package/QUICK_REFERENCE.md` - 快速参考
- 📄 `docs/migration/migration-package/FILE_LIST.md` - 文件清单
- 📄 `docs/migration/migration-package/backend_diffs.txt` - 后端 diff
- 📄 `docs/migration/migration-package/frontend_diffs.txt` - 前端 diff

### 核心源文件
- 📄 `docs/migration/migration-package/header_rules.py` - 规则引擎
- 📄 `docs/migration/migration-package/header_rule_examples.py` - 示例
- 📄 `docs/migration/migration-package/HeadersRulesEditor.vue` - 编辑器
- 📄 `docs/migration/migration-package/dialog_index.ts` - Dialog 导出

### 原始提交
- `git show edb3710` - 高级 Header 规则处理功能原始提交

---

## Codex 分析总结

**✅ 环境检查通过**:
- Python 3.9+, Pydantic v2 ✅
- Vue 3.5, TypeScript 5.8.3 ✅
- 已有 lucide-vue-next ✅

**⚠️ 关键风险**:
1. 类型放宽可能影响现有逻辑 - 需确认所有依赖 headers 的代码
2. 规则执行顺序必须严格 - remove → rename → replace → add
3. 前端类型需统一更新 - 避免 TS 报错或请求体格式不符

**📋 实施建议**:
- 按阶段顺序执行，每阶段完成后测试
- 重点关注向后兼容性
- 测试时覆盖各种规则组合

---

## 备注

- 执行前请确保数据库备份
- 建议在开发分支进行迁移
- 完成后进行完整的回归测试
- 如遇问题参考 `MIGRATION_GUIDE.md` 的"潜在问题"章节

---

**更新记录**:
- 2026-01-11: 创建任务计划，完成需求分析
