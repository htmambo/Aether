# Custom Headers 功能迁移包

本迁移包包含 `custom-header` 分支的所有修改文件，用于将自定义 Headers 规则功能迁移到上游项目。

## 目录结构

```
custom-header-migration-pack/
├── README.md                           # 本文件
├── MIGRATION_GUIDE.md                  # 详细迁移说明（同 docs/Task/Active/CUSTOM_HEADER_MIGRATION_GUIDE.md）
├── backend/                            # 后端文件
│   ├── core/
│   │   ├── header_rules.py             # [新增] Headers 规则处理核心引擎
│   │   └── header_rule_examples.py     # [新增] 规则配置示例和工具函数
│   ├── models/
│   │   └── endpoint_models.py          # [修改] headers 字段类型变更 + 新增 auto_fetch_models 字段
│   ├── services/
│   │   ├── model/
│   │   │   └── fetch_scheduler.py      # [新增] 模型自动获取调度器
│   │   └── provider/
│   │       └── transport.py            # [修改] 集成 headers 规则处理
│   ├── api/
│   │   ├── handlers/base/
│   │   │   └── request_builder.py      # [修改] 统一使用 build_provider_headers
│   │   └── admin/
│   │       └── keys.py                 # [修改] 支持 locked_models 字段
│   └── main.py                         # [修改] 添加调度器启动/停止
└── frontend/                           # 前端文件
    └── src/
        ├── features/providers/
        │   ├── components/
        │   │   ├── EndpointHeadersDialog.vue    # [新增] Headers 配置对话框
        │   │   ├── HeadersRulesEditor.vue       # [新增] 规则编辑器组件
        │   │   ├── ProviderDetailDrawer.vue     # [修改] 添加自动获取状态显示
        │   │   ├── EndpointFormDialog.vue       # [修改] 添加配置 Headers 按钮
        │   │   ├── KeyFormDialog.vue            # [修改] 添加 auto_fetch_models 编辑
        │   │   ├── KeyAllowedModelsEditDialog.vue # [修改] 支持模型锁定
        │   │   └── provider-tabs/
        │   │       └── ModelMappingTab.vue      # [新增] 模型映射标签页
        │   └── utils/
        │       ├── headerKeys.ts                # [新增] Headers 工具函数
        │       └── __tests__/
        │           └── headerKeys.spec.ts       # [新增] 单元测试
        └── api/endpoints/
            └── types.ts                         # [修改] 类型定义扩展
```

## 快速开始

1. 阅读 `MIGRATION_GUIDE.md` 了解详细的迁移步骤和修改说明
2. 按照指南逐步将文件复制到目标项目
3. 执行数据库迁移
4. 测试验证

## 核心功能

### Headers 规则系统

支持四种操作类型：
- `add`: 新增请求头
- `remove`: 删除请求头
- `replace_name`: 重命名请求头
- `replace_value`: 替换请求头值（支持正则）

### 自动获取模型

- 定时从上游 API 获取可用模型列表
- 支持模型锁定（不会被刷新删除）
- 记录获取状态和错误信息

## 兼容性

- 向后兼容旧格式的 headers 配置
- 自动转换旧格式为新规则格式
- 安全保护：不能覆盖敏感头部
