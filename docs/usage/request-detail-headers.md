# 请求详情：客户端请求头 vs 提供商请求头

本说明用于解释「使用记录 / 请求详情」页面里两个字段的含义、差异与来源：

- **客户端请求头**（`request_headers`）
- **提供商请求头**（`provider_request_headers`）

如果你想了解“请求详情抽屉”里每个 Tab 的字段含义与排障方法，见：`docs/usage/request-detail-drawer.md`

## 1. 客户端请求头（Client Request Headers）

**代表什么**  
调用方（你的客户端/SDK/CLI/浏览器）请求 Aether API 时，Aether **收到的入站请求头**。

**来源链路（简化）**

1. FastAPI 入站请求 `Request.headers` 被读出并保存到上下文 `original_headers`  
   参考：`src/api/base/context.py:105`
2. 业务处理过程中将 `original_headers` 作为 `request_headers` 传给用量记录逻辑  
   示例参考：`src/api/handlers/base/chat_handler_base.py:615`
3. 用量服务在满足日志等级配置时，将其写入数据库字段 `Usage.request_headers`（可能脱敏）  
   参考：`src/models/database.py:338`、`src/services/usage/service.py:256`

## 2. 提供商请求头（Provider Request Headers）

**代表什么**  
Aether 选中某个 Provider Endpoint 后，向上游提供商发起 HTTP 请求时，实际使用的**出站请求头**（最终形态）。

**来源链路（简化）**

1. Handler 使用 `RequestBuilder` 构建要发给 Provider 的 payload/headers  
   参考：`src/api/handlers/base/chat_handler_base.py:451`
2. 默认的 `PassthroughRequestBuilder.build_headers()` 会：
   - 注入上游 Provider 认证头（使用配置的 ProviderAPIKey）
   - 透传客户端的非敏感头（过滤敏感/协议相关 header）
   - 应用 endpoint 配置的 headers 规则（add/remove/replace_*）
   - 兜底补齐 `Content-Type`
   
   参考：`src/api/handlers/base/request_builder.py`、`src/services/provider/transport.py`
3. 构建得到的 `provider_headers` 会存入上下文/变量，并传给用量记录逻辑写库到 `Usage.provider_request_headers`（可能脱敏）  
   参考：`src/api/handlers/base/chat_handler_base.py:459`、`src/models/database.py:340`、`src/services/usage/service.py:266`

## 3. 两者的核心区别（为什么会不同）

即使同一次请求，两个 header 集合通常也会不同，常见原因：

1. **认证头不同**
   - 客户端 → Aether 的认证（例如 `Authorization`/`x-api-key`）用于 Aether 自己鉴权
   - Aether → Provider 的认证头由 Aether 基于 ProviderAPIKey **重新注入**，并且会过滤客户端侧敏感认证头，避免误透传  
   参考：`src/services/provider/transport.py`

2. **安全/协议相关头被清理**
   `host`、`content-length`、`accept-encoding` 等在出站时会被过滤或重建，以避免上游兼容性问题  
   参考：`src/api/handlers/base/endpoint_checker.py`

3. **端点 Header 规则会修改出站 headers**
   提供商管理里的 endpoint headers 配置（新格式规则 add/remove/replace_*）会在出站阶段应用，从而导致差异  
   参考：`src/core/header_rules.py`、`src/api/handlers/base/endpoint_checker.py`

## 3.1 “最高安全规则”：哪些 headers 永远不能被自定义规则覆盖？

出站 headers 会遵守系统内置的“最高安全规则”（优先级最高）：

1. **认证类 headers**：例如 `Authorization`、`x-api-key`、`x-goog-api-key`（由系统根据 Provider Key 注入并保护）。
2. **协议/连接类 headers**：例如 `Host`、`Content-Length`、`Accept-Encoding` 等（由 HTTP 客户端栈重建或过滤）。

因此，即使你在 Endpoint 的 headers 规则里添加了这些 headers，也可能被拦截或被系统值覆盖，这是预期行为。

## 4. 记录与脱敏：为什么有时为空/值看起来不完整

请求详情里的 headers 是否存在，以及是否被 `***` 脱敏，取决于系统设置里的日志等级与脱敏策略：

- headers 是否记录：由 `SystemConfigService.should_log_headers()` 决定  
  参考：`src/services/usage/service.py:256`
- 敏感 header 脱敏：通过 `SystemConfigService.mask_sensitive_headers()` 处理后再入库  
  参考：`src/services/usage/service.py:262`、`src/services/usage/service.py:269`

## 5. 页面展示说明

请求详情页会将两份 headers 做对比展示（Diff/并排），用于定位“哪些 headers 被添加/删除/改写”。  
参考：`frontend/src/features/usage/components/RequestDetailDrawer/RequestHeadersContent.vue:18`
