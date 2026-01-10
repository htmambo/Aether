# 高级 Header 规则处理功能 - 迁移包

## 包内容

本迁移包包含将"高级 Header 规则处理"功能迁移到上游项目所需的所有文件和文档。

### 文档文件

1. **README.md** (本文件) - 迁移包使用说明
2. **MIGRATION_GUIDE.md** (22 KB) - 详细迁移指南，包含完整的迁移步骤和说明
3. **QUICK_REFERENCE.md** (6.5 KB) - 快速参考手册，包含常见用例和调试技巧
4. **FILE_LIST.md** (3.5 KB) - 文件清单和修改说明

### 核心源文件

5. **header_rules.py** (7.3 KB) - Header 规则引擎核心实现
6. **header_rule_examples.py** (8.3 KB) - 规则示例和工具函数
7. **HeadersRulesEditor.vue** (16 KB) - Header 规则可视化编辑器
8. **dialog_index.ts** (364 B) - Dialog 组件统一导出

### 参考文件

9. **backend_diffs.txt** (7.5 KB) - 后端修改文件的 git diff
10. **frontend_diffs.txt** (5.1 KB) - 前端修改文件的 git diff
11. **git_diffs.sh** (1.2 KB) - Git diff 提取脚本

---

## 快速开始

### 1. 阅读迁移指南

首先阅读 `MIGRATION_GUIDE.md`，了解：
- 功能概述和核心能力
- 规则类型和执行顺序
- 详细的迁移步骤
- 潜在问题和解决方案
- 验收清单

### 2. 按阶段迁移

按照迁移指南的阶段顺序执行：

**阶段 1: 后端核心逻辑**（必须）
- 复制 `header_rules.py` 到 `src/core/`
- 复制 `header_rule_examples.py` 到 `src/core/`
- 修改 4 个后端文件（参考 backend_diffs.txt）

**阶段 2: 前端 UI 组件**（必须）
- 复制 `HeadersRulesEditor.vue` 到前端组件目录
- 复制 `dialog_index.ts` 到 `frontend/src/components/ui/dialog/`
- 修改 `EndpointFormDialog.vue`（参考 frontend_diffs.txt）

**阶段 3: 前端类型定义**（强烈建议）
- 更新 TypeScript 类型定义

**阶段 4: 测试**（强烈建议）
- 添加单元测试

### 3. 验证功能

使用迁移指南中的验收清单验证所有功能点。

---

## 文件使用说明

### MIGRATION_GUIDE.md

**用途**: 主要的迁移文档，包含完整的迁移步骤

**阅读顺序**:
1. 概述 → 了解功能背景
2. 功能说明 → 理解规则类型和执行顺序
3. 迁移清单 → 按阶段执行迁移
4. 潜在问题 → 了解可能遇到的问题
5. 验收清单 → 验证迁移结果

### QUICK_REFERENCE.md

**用途**: 快速查找手册，包含常见用例

**适合场景**:
- 需要快速查看规则格式
- 查找代码示例
- 调试和错误处理
- 性能优化建议

### FILE_LIST.md

**用途**: 文件清单和修改说明

**包含内容**:
- 新增文件列表
- 修改文件列表
- 每个文件的具体修改内容

### backend_diffs.txt / frontend_diffs.txt

**用途**: Git diff 输出，展示具体的代码修改

**使用方法**:
- 对比迁移前后的代码差异
- 理解修改的具体位置和内容
- 作为代码审查的参考

### 核心源文件

**用途**: 直接复制到目标项目

**注意事项**:
- 复制前检查目标项目是否已有同名文件
- 可能需要调整导入路径
- 检查依赖的第三方库是否已安装

---

## 迁移前准备

### 环境检查

确保目标项目满足以下要求：

**后端**:
- [ ] Python 3.8+
- [ ] Pydantic v2
- [ ] SQLAlchemy（或类似 ORM）
- [ ] 数据库支持 JSON/JSONB 类型

**前端**:
- [ ] Vue 3
- [ ] TypeScript 4+
- [ ] UI 组件库（Button、Dialog、Input、Label、Badge、Switch）
- [ ] 图标库（lucide-vue-next 或其他）

### 依赖检查

**后端无新增依赖**，仅使用标准库和已有的 Pydantic

**前端可能需要**:
- `lucide-vue-next`（或其他图标库）
- 现有的 UI 组件库

### 数据库检查

确认 `provider_endpoints` 表的 `headers` 字段类型：

```sql
-- PostgreSQL
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'provider_endpoints' AND column_name = 'headers';
-- 期望结果: jsonb

-- MySQL
SHOW COLUMNS FROM provider_endpoints LIKE 'headers';
-- 期望结果: json
```

如果不是 JSON 类型，需要进行迁移（参考 MIGRATION_GUIDE.md）

---

## 迁移步骤概览

### 第一步: 后端核心（1-2小时）

1. 复制新增文件
2. 修改数据模型（5 分钟）
3. 集成规则引擎（30 分钟）
4. 测试向后兼容性（15 分钟）

### 第二步: 前端 UI（2-3小时）

1. 复制新增文件
2. 调整 UI 组件依赖（如有需要）
3. 集成到表单（1 小时）
4. 测试 UI 交互（30 分钟）

### 第三步: 类型定义（30 分钟）

1. 更新 TypeScript 类型
2. 检查类型错误
3. 添加类型守卫（如需要）

### 第四步: 测试（1-2小时）

1. 编写单元测试
2. 功能测试
3. 兼容性测试

**总计**: 约 4-8 小时（取决于项目复杂度）

---

## 常见问题

### Q1: 迁移后旧数据还能用吗？

**A**: 可以。规则引擎会自动识别旧格式（`Dict[str, str]`）并转换为 `add` 规则，无需手动迁移数据。

### Q2: 是否必须使用 HeadersRulesEditor.vue？

**A**: 不是必须的。规则引擎是后端实现，前端可以用任何方式编辑规则，只要产出符合 `HeaderRules` 格式的对象即可。

### Q3: 如果目标项目没有所需的 UI 组件怎么办？

**A**: 有两个选择：
1. 调整 `HeadersRulesEditor.vue` 使用目标项目的 UI 组件
2. 仅迁移后端，前端用简单的 JSON 编辑器

### Q4: 规则会影响性能吗？

**A**: 影响很小。规则执行是 O(n) 复杂度，建议单个 endpoint 不超过 20 条规则。

### Q5: 如何回滚？

**A**: 参考 MIGRATION_GUIDE.md 中的"回滚方案"章节。

---

## 技术支持

### 遇到问题？

1. **检查日志**: 查看后端日志中的 `headers` 相关输出
2. **验证规则**: 使用 `validate_header_rules()` 函数
3. **查看 diff**: 对比 backend_diffs.txt 和 frontend_diffs.txt
4. **运行测试**: 执行单元测试（如果有）

### 获取更多信息

- 原始提交: `git show edb3710`
- 核心实现: `header_rules.py` 文件中的详细注释
- 示例代码: `header_rule_examples.py`

---

## 版本信息

- **迁移包版本**: 1.0
- **创建日期**: 2026-01-10
- **来源提交**: `edb3710` (高级 Header 规则处理)
- **适用项目**: Aether 及类似的 API 网关项目

---

## 许可

请遵循原项目的许可证条款。

---

## 更新日志

### v1.0 (2026-01-10)
- 初始版本
- 包含完整的迁移文档和源文件
- 支持四种规则类型：add、remove、replace_name、replace_value
- 提供前端可视化编辑器
- 向后兼容旧格式

---

**祝你迁移顺利！** 🚀
