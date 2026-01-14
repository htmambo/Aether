# 管理员控制台总览

本文按管理后台菜单说明“每个功能点是什么、怎么操作”，并给出与其他模块的关联关系。

页面截图：`docs/screenshots/users.png`、`docs/screenshots/settings.png`

![用户管理](../screenshots/users.png)

## 1. 用户管理（Users）

路径：**管理后台 → 用户管理**

常用操作：

1. 创建/编辑用户（邮箱、用户名、角色、状态、配额）。
2. 配置用户访问限制（允许的 Provider / API 格式 / 模型）。
3. 停用用户（立即阻止其登录与调用）。

更详细的操作要点：

- 搜索与筛选：支持按用户名/邮箱搜索，并按角色/状态筛选。
- 访问限制（如页面提供）：通常以“多选列表”方式配置 `allowed_providers` / `allowed_api_formats` / `allowed_models`（为空通常表示不限制）。
- 配额：用户配额不足时会直接拒绝请求（可在使用记录中观察配额耗尽现象）。

📎 参考：`frontend/src/views/admin/Users.vue:1`

## 2. Standalone API Keys（ApiKeys）

路径：**管理后台 → API Keys**

用途：创建“独立余额 Key”（给非注册用户使用或给外部系统发放）。

常用操作：

1. 创建 Key：设置初始余额、有效期、速率限制与访问范围。
2. 充值/扣费：对 Key 的余额做增减（用于运营发放或补款）。
3. 绑定访问限制（模型/Provider/格式），并在需要时停用/删除 Key。

字段理解（常见）：

- 余额：`已用/总额`（总额为“无限”时表示不受余额限制，具体以 UI 展示为准）。
- 速率：`rate_limit`（按分钟限制或类似口径，具体以 UI 文案为准）。
- 访问限制：`allowed_providers / allowed_api_formats / allowed_models`（为空通常表示不限制）。
- 有效期：`expires_at`；系统设置里可配置“过期后自动删除/仅禁用”策略。

📎 参考：`frontend/src/views/admin/ApiKeys.vue:1`

## 3. 模型管理（ModelManagement）

路径：**管理后台 → 模型管理**

包含：

- 模型目录（catalog）导入/同步
- GlobalModel 管理（名称、显示名、能力、价格、别名）
- 关联 Provider 与路由预览

详见：`docs/usage/04-02-models.md`

## 4. 提供商管理（ProviderManagement）

路径：**管理后台 → 提供商管理**

包含：

- Provider/Endpoint/Key 管理
- 模型支持列表、模型检测
- 模型映射与别名匹配预览
- Endpoint 自定义 Headers 规则

详见：`docs/usage/04-01-providers.md`

## 5. 系统设置（SystemSettings）

路径：**管理后台 → 系统设置**

常用操作：

1. 导出/导入 Provider + Model 配置（用于迁移/备份/恢复）。
2. 导出/导入用户数据（用于迁移普通用户与其 API Keys；若要保留“查看完整 Key/正常显示 Key 预览”的能力，建议目标环境 `ENCRYPTION_KEY` 与导出环境一致）。
3. 配置用户注册策略、默认配额、请求速率限制等系统参数。
4. 配置请求日志记录级别、脱敏字段、日志清理策略（保留天数/分级压缩/自动清理）。

配置导入/导出（操作步骤）：

1. 导出配置：点击“导出配置”，浏览器会下载一个 JSON 文件（包含提供商、端点、Provider Keys、全局模型等）。
2. 导入配置：点击“导入配置”，选择 JSON 文件后，会出现“冲突处理模式”（跳过/覆盖/报错等）预览；确认后执行导入。
3. 导出用户数据：点击“导出用户数据”（不含管理员）。
4. 导入用户数据：选择用户数据 JSON 文件并确认导入；若目标环境 `ENCRYPTION_KEY` 不同，keys 仍可基于 `key_hash` 验证使用，但 `key_encrypted` 将无法解密（查看完整 key/预览显示可能受影响）。

更完整的 JSON 结构、`merge_mode` 冲突策略与排障说明见：`docs/usage/system-import-export.md`

📎 参考：`frontend/src/views/admin/SystemSettings.vue:1`

## 5.1 公告（Announcements）

路径：**公告**（管理端与用户端共用入口）

用途：

- 向用户发布系统通知（维护窗口、规则变更等）。

管理端常用操作（管理员可见）：

1. 新建公告：设置类型、标题、内容。
2. 置顶/启用：列表中可直接开关置顶与启用状态。
3. 编辑/删除：行右侧操作按钮。

用户侧行为：

- 点击公告会打开详情，并将未读标记为已读（以 UI 行为为准）。

📎 参考：`frontend/src/views/user/Announcements.vue:1`

## 5.2 仪表盘 / 健康监控 / 使用记录 / 链路追踪

路径：侧边栏对应入口（共享页面）

- 仪表盘：全局统计概览
- 健康监控：Provider/Endpoint/Key 健康与熔断
- 使用记录：明细/聚合统计与请求详情
- 链路追踪：定位单次请求的路由/重试/错误

## 6. 安全（IPSecurity / EmailSettings / AuditLogs）

路径：

- **IP 安全**：管理后台 → IP 安全（IP 白名单/黑名单）
- **邮箱设置**：管理后台 → 邮箱设置（允许注册后缀白/黑名单）
- **审计日志**：管理后台 → 审计日志（管理员操作记录）

详见：`docs/usage/04-03-security.md`

## 7. LDAP 设置（LdapSettings）

路径：**管理后台 → LDAP 设置**

用途：企业内统一账号体系接入（启用/配置参数/映射规则等）。

## 8. 缓存监控（CacheMonitoring）

路径：**管理后台 → 缓存监控**

用途：

- 查看缓存命中/键数量/热点
- 清理模型映射/Provider 等缓存（排障常用）

详见：`docs/usage/04-04-monitoring.md`

## 9. 建议的管理员操作顺序（从 0 到稳定）

1. 先完成基础部署与管理员登录：`docs/usage/01-deployment.md`
2. 配好 Provider/Endpoint/Key 并跑通“模型检测”：`docs/usage/04-01-providers.md`
3. 创建 GlobalModel 并关联 Provider：`docs/usage/04-02-models.md`
4. 在“使用记录/链路追踪/健康监控”观察一段时间：`docs/usage/04-04-monitoring.md`
5. 再逐步开启安全策略（IP/邮件/LDAP/审计）：`docs/usage/04-03-security.md`
