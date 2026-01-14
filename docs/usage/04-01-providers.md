# 提供商管理（Provider / Endpoint / Key / 模型检测 / Headers 规则）

本文覆盖“管理后台 → 提供商管理”页面的所有功能点与具体操作方法。

页面截图：`docs/screenshots/providers.png`

![提供商管理](../screenshots/providers.png)

## 0. 你在这里会做什么

一条完整链路通常由 4 个层级组成：

1. **Provider（提供商）**：一个上游供应方（OpenAI/Claude/Gemini 或兼容服务）。
2. **Endpoint（端点）**：某个 API 格式对应的 `base_url` / `custom_path` / `headers` 等连接参数。
3. **Key（密钥）**：上游鉴权凭证 + 调度控制（优先级、RPM、自适应、能力标签、模型白名单等）。
4. **Provider Model（提供商模型支持）**：该 Provider 对哪些 GlobalModel 提供支持，以及上游模型名 `provider_model_name`。

## 1. Provider 列表页（提供商管理）

路径：**管理后台 → 提供商管理**

### 1.1 常用操作

1. **搜索**：右上角搜索框输入 Provider 名称。
2. **新增 Provider**：点击右上角“+”按钮。
3. **打开详情抽屉**：点击行或“眼睛”图标。
4. **编辑/启停/删除**：在行右侧操作按钮中完成（删除为不可逆操作）。

### 1.2 创建/编辑 Provider（计费、超时、代理）

入口：列表页右上角“新增提供商”，或行右侧“编辑提供商”。

常用字段（以 UI 为准）：

1. **基本信息**：名称、官网链接、描述。
2. **计费与限流**
   - `billing_type`：
     - `pay_as_you_go`：按量付费（不做 Provider 级配额限制）
     - `monthly_quota`：月卡额度（需要配置周期与额度）
     - `free_tier`：免费套餐（通常用于成本核算为 0 或策略标识）
   - `provider_priority`：Provider 优先级（数值越小越优先；会参与全局路由策略）
3. **月卡配置（billing_type = monthly_quota 时显示）**
   - `monthly_quota_usd`：周期额度（美元）
   - `quota_reset_day`：重置周期（天数，例如 7=每周、30=每月）
   - `quota_last_reset_at`：周期开始时间（必填）
   - `quota_expires_at`：过期时间（可选）
4. **请求配置**
   - `timeout`：超时时间（秒）
   - `max_retries`：最大重试次数
5. **代理配置（Proxy）**
   - 启用后可配置 `proxy_url`（支持 `http://`、`socks5://` 等，具体以实现为准）
   - 可选用户名/密码

注意（时间与时区）：

- Provider 表单中的“周期开始时间/过期时间”是 `datetime-local` 输入；如果后端收到的时间没有时区信息，会按 UTC 解释。
- 如果你的运维时区不是 UTC，建议在设置月卡周期时统一按 UTC 计算，避免“周期开始时间偏移”导致额度同步不符合预期。

### 1.2 调度模式与优先级策略（全局）

入口：列表右上角“调度:”按钮（会显示当前策略标签）。

你通常会看到两类全局策略（名称以 UI 为准，但含义固定）：

1. **优先级策略**
   - `提供商优先`：先按 Provider 的优先级，再按该 Provider 内 Key 的优先级选路。
   - `全局 Key 优先`：忽略 Provider 层级，所有 Key（跨 Provider）按全局优先级统一排序。
2. **调度模式**
   - `固定顺序`：严格按排序选择。
   - `负载均衡`：同优先级下做分散。
   - `缓存亲和`：同一用户（或亲和键）尽量稳定命中同一路径，减少抖动（配合缓存监控排障）。

## 2. Provider 详情抽屉（核心工作区）

在 Provider 列表点击某行后，会打开 Provider 抽屉。你会在这里管理 Endpoint、Key、模型支持、模型映射。

如果该 Provider 使用 `monthly_quota` 计费类型，抽屉上方会显示“订阅配额”进度条，用于快速观察本周期使用量（仅展示，不一定提供重置按钮）。

### 2.1 Endpoint（端点）管理

入口：抽屉顶部会以“标签”的形式展示已配置的 API 格式端点；点击标签可编辑。也可点末尾“编辑”进入端点管理对话框。

**新增 Endpoint**

1. 打开“端点管理”对话框。
2. 选择 API 格式（如 OpenAI/Claude/Gemini 及 CLI 变体）。
3. 填写 `Base URL`（例如 `https://api.openai.com` / `https://api.anthropic.com` / `https://generativelanguage.googleapis.com` 或你的兼容地址）。
4. 可选填写 `自定义路径 (custom_path)`：覆盖该格式默认路径（除非你非常确定，否则建议留空）。
5. 点击“添加”。

**编辑 / 启停 / 删除 Endpoint**

- 编辑：端点行右侧“铅笔”图标，修改 `Base URL`/`custom_path` 后保存。
- 启停：端点行右侧“电源”图标。
- 删除：端点行右侧“垃圾桶”图标（会同时删除该端点下的 Keys）。

### 2.2 Endpoint 自定义 Headers（规则模式）

入口：端点行右侧“Headers配置”（齿轮）按钮。

Headers 支持两种写法（UI 内会自动互转）：

1. **旧格式（字典）**：`{"X-Foo": "bar"}`（语义等价于 `rules.add`）
2. **规则格式（推荐）**
   - `add`：新增 header（若已存在则不覆盖）
   - `remove`：删除 header（大小写不敏感）
   - `replace_name`：重命名 header
   - `replace_value`：替换 header 值（可选 regex、大小写敏感）

**安全规则（最高级，不可被自定义规则破坏）**

- 自定义规则不能注入/覆盖系统敏感或协议相关 header（例如 `Authorization`、`x-api-key`、`x-goog-api-key`、`Host`、`Content-Length` 等）。
- 上游认证 header 由系统根据 Provider Key 生成并注入；即使你在规则里写了同名 header，也会被拦截或被系统值覆盖。

**示例（常见用途）**

- Claude 上游固定版本：`add` 增加 `anthropic-version: 2023-06-01`
- OpenAI 上游组织：`add` 增加 `OpenAI-Organization: org_xxx`

更完整的“请求头来源与优先级”说明见：`docs/usage/request-detail-headers.md`

## 3. Key（密钥）管理（上游鉴权 + 调度控制）

入口：Provider 抽屉中的“密钥”区域（若无 Key 会提示先添加 Endpoint）。

### 3.1 新增/编辑 Key（字段含义）

入口：点击“添加密钥”或 Key 行的“编辑”按钮。

必填/常用字段（以 UI 字段名为准）：

1. **密钥名称**：仅用于管理侧识别（例如“主 Key / 备用 Key 1”）。
2. **API 密钥**：上游真实密钥；编辑时留空表示不修改。
3. **支持的 API 格式**：Key 可以“声明”自己能用于哪些格式；只有同时满足 Endpoint 格式 + Key 支持格式，才会进入路由候选。
4. **成本倍率（×）**：每个 API 格式右侧的倍率输入（用于成本核算/策略）。
5. **优先级**：数值越小越优先（同 Provider 内）。
6. **RPM 限制**：留空为“自适应”；填写数字为固定 RPM 上限。
7. **缓存 TTL（分钟）**：0 表示禁用；>0 表示允许缓存并设置 TTL。
8. **熔断探测（分钟）**：熔断后探测间隔（范围 2–32 分钟）。
9. **能力标签**：给 Key 打标签（如 `cache_1h` 等），供路由过滤/偏好使用。
10. **自动获取模型**：开启后会定时从上游拉取可用模型并更新该 Key 的模型白名单（见下一节）。

### 3.2 模型权限（`allowed_models` / “Key 白名单”）是什么？

**含义**：`allowed_models` 是 Key 的“允许访问模型列表”。当你调用某个模型时，路由会跳过不允许该模型的 Key。

入口：Key 行右侧“盾牌”按钮（模型权限）。

重要语义（与后端一致）：

- `allowed_models = null`：不限制（允许所有模型）
- `allowed_models = []`：会被规范化为 `null`（UI 里表现为“未选择 = 全部模型”）
- 历史/导入数据可能是“按格式字典模式”：`{"OPENAI": [...], "CLAUDE": [...]}`。UI 会提示“编辑后会转换为统一列表模式”，确认后再保存。

### 3.3 如何配置 Key 白名单（含“两个列表/不能手填”的情况）

在“模型权限”对话框中，你会看到按分组展示的模型列表（例如“提供商模型 / 上游模型 / 自定义模型”）。

**选择已有模型**

1. 在列表中点击模型行（或勾选框）即可选中/取消。
2. 右上角会显示“已选 N 个”。

**添加自定义模型（手动输入）**

1. 在顶部搜索框输入模型名（例如 `gpt-4o-mini`）。
2. 若该名称不在任何列表中，会出现“添加自定义模型”提示。
3. 点击该提示后，自定义模型会进入“自定义模型”分组并可被选中。

**白名单示例**

- 简单白名单（列表）：`["gpt-4o-mini", "gpt-4.1-mini", "claude-3-5-sonnet-20241022"]`
- 按格式白名单（字典，较少在 UI 中手动维护）：`{"OPENAI": ["gpt-4o-mini"], "CLAUDE": ["claude-3-5-sonnet-20241022"]}`

### 3.4 自动获取模型（`auto_fetch_models`）与锁定模型

开启“自动获取模型”后：

1. 系统会定期从上游拉取模型列表，并写入该 Key 的 `allowed_models`。
2. 为避免“上游短暂不返回模型名导致白名单被清空”，你可以在白名单对话框中对模型进行“锁定”（锁定后刷新不会删除该模型）。

## 4. 模型列表与模型检测（Provider → 模型支持）

入口：Provider 抽屉中的“模型列表”卡片。

### 4.1 关联/移除模型（Provider 支持哪些 GlobalModel）

1. 点击“关联模型”，在对话框中批量选择全局模型。
2. 关联后，在模型行里配置 `provider_model_name`（上游真实模型名）。
3. 若不再支持，点击“删除”仅移除该 Provider 对该 GlobalModel 的支持（不会删除全局模型本身）。

### 4.2 模型检测（Test Model）

入口：模型行“播放/测试”按钮（当一个 Provider 同时有多种可用 API 格式时，会弹出格式选择）。

用途：

- 验证该 `provider_model_name` 在当前 Endpoint + Key 下是否可用。
- 快速定位：鉴权失败、路径错误、headers 缺失、上游限速/熔断等。

排障建议：

1. 优先确保 Endpoint 与 Key 均为“活跃”。
2. 再检查 Key 的 `allowed_models` 是否允许该模型。
3. 若需要额外上游 headers（例如 Claude 的 `anthropic-version`），在 Endpoint Headers 里用规则添加。

## 5. Provider 侧模型映射（Model Mapping）

入口：Provider 抽屉底部“模型映射”卡片。

用途：在“同一个 GlobalModel”下维护多个候选的上游模型名，并通过优先级与作用域（API 格式）控制选择策略。

常用操作：

1. 点击“添加映射”创建一个映射组（按模型 + 作用域分组）。
2. 在组内添加多条映射名称与优先级（数字越小越优先）。
3. 用“测试映射”按钮验证某条映射在当前配置下是否可用。

如果你看到“正则/Key 数量”等预览信息，表示该页面还会结合 Key 白名单与全局模型别名规则做“匹配预览”，用于帮助你确认规则覆盖范围。

📎 参考

- Provider Key 白名单与别名预览：`src/api/admin/providers/routes.py:45`
- Key allowed_models 语义与规范化：`src/core/model_permissions.py:29`
