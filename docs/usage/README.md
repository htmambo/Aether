# Aether 使用手册（目录）

## 0. 读前须知

- 本手册以“管理后台 UI 操作”为主，必要时给出 API/cURL 示例。
- 文中术语：
  - **Provider（提供商）**：上游供应方（Claude/OpenAI/Gemini 或兼容服务）。
  - **Endpoint（端点）**：某 Provider 下某个 API 格式的 base_url/custom_path/headers/代理等配置。
  - **Key（密钥）**：Provider 的 API Key（用于向上游鉴权），可配置优先级、RPM、模型白名单、能力标签等。
  - **GlobalModel（全局模型）**：Aether 对外暴露的“统一模型名”，可关联多个 Provider Model。
  - **Model（关联模型）**：GlobalModel 与 Provider 的关联记录（包含 provider_model_name、映射、优先级等）。

## 1. 使用手册导航

1. 部署与启动：`docs/usage/01-deployment.md`
2. 快速上手：`docs/usage/02-quickstart.md`
3. 用户侧指南：`docs/usage/03-user-guide.md`
4. 管理员总览：`docs/usage/04-admin-guide.md`
5. 提供商管理：`docs/usage/04-01-providers.md`
6. 模型管理：`docs/usage/04-02-models.md`
7. 安全与合规：`docs/usage/04-03-security.md`
8. 监控与运维：`docs/usage/04-04-monitoring.md`
9. API 与 CLI 接入：`docs/usage/05-api-and-cli.md`
10. 常见问题与排障：`docs/usage/06-troubleshooting.md`

## 2. 常见上手路径（建议顺序）

1. 管理员完成基础部署与登录（`docs/usage/01-deployment.md`）
2. 添加 Provider → Endpoint → Key（`docs/usage/04-01-providers.md`）
3. 从模型目录导入/创建 GlobalModel，并关联 Provider（`docs/usage/04-02-models.md`）
4. 使用“模型检测”验证链路（`docs/usage/04-01-providers.md`）
5. 创建用户 API Key 或让用户自助创建（`docs/usage/03-user-guide.md`）
6. 客户端按 OpenAI/Claude/Gemini 方式调用（`docs/usage/05-api-and-cli.md`）

## 3. 专题手册（按需阅读）

1. 使用记录 / 请求详情抽屉（字段含义与排障）：`docs/usage/request-detail-drawer.md`
2. 使用记录 / 请求详情：客户端请求头 vs 提供商请求头：`docs/usage/request-detail-headers.md`
3. 系统设置：配置/用户数据 导入导出：`docs/usage/system-import-export.md`
