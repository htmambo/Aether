# 快速上手（从 0 到可用）

目标：让 Aether 能成功把一次请求转发到上游（Provider）并在使用记录中可追踪。

## Step 1：管理员登录

1. 打开首页 → 点击登录/注册（如关闭注册则使用管理员账号）。
2. 使用 `.env` 中 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 登录。

## Step 2：添加 Provider / Endpoint / Key

路径：**管理后台 → 提供商管理**

1. 新建 Provider（名称、计费类型、优先级等）。
2. 在 Provider 抽屉中添加 Endpoint（选择 API 格式、填写 `base_url`，必要时填 `custom_path`）。
3. 在 Provider 抽屉中添加 Key（录入上游 API Key，配置优先级/RPM/倍率/能力标签）。

常用建议：

- 先只配置一个 Provider + 一个 Endpoint + 一个 Key，确认链路打通后再扩展。
- 如果上游需要额外 Header（例如企业代理/自定义标识），先不加；待请求成功后再添加（见 `docs/usage/04-01-providers.md`）。

## Step 3：让模型“可被路由”

路径：**管理后台 → 模型管理**

1. 创建/导入一个 GlobalModel（例如 `gpt-4o-mini`），设置显示名/能力/价格（可后补）。
2. 将该 GlobalModel 关联到你刚创建的 Provider，并填写 provider_model_name（上游实际模型名）。

## Step 4：模型检测（验证链路）

路径：**管理后台 → 提供商管理 → 打开 Provider 抽屉 → 模型查看**

1. 找到 provider_model_name 对应的模型行。
2. 点击“测试”按钮（可选择 API 格式）验证是否能成功返回。

## Step 5：创建用户 API Key 并调用

路径：**用户侧 → 我的 API Keys**

1. 创建一个 API Key（给自己或给调用方）。
2. 复制 API Key，在客户端按 OpenAI/Claude/Gemini 方式调用（见 `docs/usage/05-api-and-cli.md`）。

## Step 6：查看使用记录与请求详情

路径：**使用记录**

1. 在列表中找到刚才的请求。
2. 打开请求详情：
   - 对比客户端请求头与提供商请求头：`docs/usage/request-detail-headers.md`
   - 若开启追踪，可查看链路追踪与错误分类信息。
