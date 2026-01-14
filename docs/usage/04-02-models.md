# 模型管理（GlobalModel / 能力与价格 / 链路预览 / 模型别名）

本文覆盖“管理后台 → 模型管理”页面的所有功能点与具体操作方法。

页面截图：`docs/screenshots/model-detail.png`、`docs/screenshots/model-providers.png`

![模型详情](../screenshots/model-detail.png)

## 0. 两个重要概念

1. **GlobalModel（全局模型）**：Aether 对外暴露的“统一模型名”（例如 `gpt-4o-mini`）。
2. **Provider Model（提供商模型）**：某个 Provider 对某个 GlobalModel 的支持记录，包含上游真实模型名 `provider_model_name`。

你在模型管理里做的事情，本质是：定义全局模型 → 配好能力/价格 → 关联 Provider → 用链路预览验证路由 → 用别名规则做“白名单匹配预览/辅助映射”。

## 1. 模型列表页（Catalog）

路径：**管理后台 → 模型管理**

### 1.1 常用操作

1. **搜索模型**：右上角搜索框支持按模型名检索。
2. **能力过滤**：右上角图标可快速筛选 Streaming / Vision / Tool Use / Extended Thinking / 图像生成等能力。
3. **创建模型**：点击“+ 创建模型”。
4. **查看详情抽屉**：点击行或“眼睛”图标。
5. **编辑/启停/删除**：在行右侧操作按钮中完成（删除为不可逆操作）。

### 1.2 创建 GlobalModel（推荐流程）

入口：模型列表右上角“创建模型”。

创建模式通常支持“从已有 Provider 模型候选中选择并生成统一模型”（具体交互以 UI 为准）：

1. 在左侧列表选择一个候选模型（按 Provider 分组）。
2. 右侧填写/确认：
   - **模型名称（name）**：全局唯一，建议直接使用对外希望暴露的模型名（例如 `gpt-4o-mini`）。
   - **显示名称（display_name）**：用于 UI 展示（例如 `GPT-4o Mini`）。
3. 配置能力开关与价格（见下文）。
4. 点击“创建”。

## 2. GlobalModel 详情抽屉（重点）

点击某个模型进入详情抽屉，通常包含 3 个 Tab（UI 文案可能略有差异）：

1. **基本信息**：能力、偏好标签、默认定价等。
2. **链路控制**：关联 Provider、链路预览、启停关联等。
3. **模型映射**：别名规则（用于 Key 白名单匹配预览）与其他映射能力（以系统版本为准）。

### 2.1 基本信息：能力、偏好、价格

**能力开关（Capabilities）**

- Streaming（流式）
- Vision（视觉理解）
- Tool Use / Function Calling（工具调用）
- Extended Thinking（深度思考）
- Image Generation（图像生成）

这些能力会在模型目录、路由预览和用户侧模型目录中展示，也常用于“能力偏好”的筛选。

**Key 能力支持（supported_capabilities）**

这是“路由侧的能力标签集合”。当你的 Key 也配置了相同能力标签时，系统可以在路由筛选/偏好时更准确地选择匹配的 Key。

**价格配置（Pricing）**

模型的价格用于成本核算与用量统计展示（并不等同于上游真实计费）。

1. **Token 计费**：按输入/输出 token 的 $/M 计价（可选阶梯计费）。
2. **缓存计费**：当模型支持缓存能力（例如 `cache_1h`）时可配置相应价格项。
3. **按次计费（$/次）**：可与 token 计费叠加，用于补充计价。

### 2.2 链路控制：关联 Provider 与路由预览

入口：详情抽屉的“链路控制/链路”Tab。

**关联 Provider**

1. 点击“关联提供商”按钮。
2. 选择要关联的 Provider（支持批量）。
3. 对每个关联项配置上游模型名 `provider_model_name`（以及可选的价格覆盖等字段）。

**路由预览（Routing Preview）怎么用**

路由预览会按 API 格式分组展示该 GlobalModel 的候选路径，并明确告诉你“为什么某条 Key/Provider 会被选中或被跳过”。

常见你需要关注的信息：

1. **全局策略**：标题处会显示当前 `scheduling_mode` 与 `priority_mode`。
2. **Key 状态**：是否活跃、是否熔断、健康度、是否命中白名单。
3. **恢复操作**：当 Key 熔断或健康度过低时，可在预览中点击“刷新健康状态/恢复”按钮（以 UI 按钮为准）。

如果预览显示“无可用 Key”，优先按如下顺序排查：

1. Provider/Endpoint/Key 是否启用
2. Key 是否支持该 API 格式
3. Key 的 `allowed_models`（Key 白名单）是否允许该模型
4. 模型关联项的 `provider_model_name` 是否正确

### 2.3 模型别名（Model Aliases）：Key 白名单匹配预览

入口：详情抽屉的“模型映射/映射”Tab（其中的“映射规则/别名规则”区域）。

**它的作用**

- 别名规则是“正则表达式列表”。
- 系统会拿每条规则去匹配各 Provider Key 的 `allowed_models`（Key 白名单）里的模型名，并在 UI 中展示“命中了哪些 Key 白名单项”。
- 它本质是一个“预览/辅助匹配工具”，用于帮助你写出覆盖范围正确的白名单模型名或映射规则。

**如何添加规则**

1. 点击“添加规则”。
2. 输入正则表达式（例如 `claude-3-5-sonnet-.*`）。
3. 点击“保存”。
4. 展开该规则，查看“匹配到哪些 Provider/Key/白名单模型”。

**为什么提示“此规则暂无匹配的 Key 白名单”**

含义：当前系统里，没有任何 Provider Key 的 `allowed_models` 命中该正则规则。

常见原因：

1. 你没有为任何 Provider Key 配置 `allowed_models`（未设置白名单通常表示“不限制”，因此也不会出现在“白名单匹配预览”里）。
2. 正则与白名单中的模型名不匹配（大小写/前后缀/命名空间不同）。

解决方法见：`docs/usage/06-troubleshooting.md`

**安全提示（ReDoS）**

- 别名规则支持正则，系统会对明显危险的表达式做校验（例如嵌套量词）。
- 建议优先写“有界”的正则（尽量避免 `(.*)+`、`(.+)+`、`(a+)+`、`{n,}` 等容易导致回溯爆炸的模式）。

## 3. 与 Provider / Key 的关系（建议顺序）

推荐配置顺序：

1. 先在“提供商管理”把 Provider/Endpoint/Key 配好（并至少跑通一次“模型检测”）。
2. 在“模型管理”创建 GlobalModel 并关联 Provider，填好 `provider_model_name`。
3. 若你需要“别名规则匹配预览”，再去为 Key 配置 `allowed_models`（Key 白名单）并回到本页刷新预览。

📎 参考

- GlobalModel 表单字段（能力/价格/偏好）：`frontend/src/features/models/components/GlobalModelFormDialog.vue:86`
- 路由预览 UI：`frontend/src/features/models/components/RoutingTab.vue:1`
- 别名规则 UI（提示“暂无匹配 Key 白名单”）：`frontend/src/features/models/components/ModelAliasesTab.vue:122`
