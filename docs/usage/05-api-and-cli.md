# API 与 CLI 接入（OpenAI / Claude / Gemini / Management Token）

本文说明如何从客户端调用 Aether 的对外 API（OpenAI/Claude/Gemini 兼容），以及如何用 CLI 或管理令牌接入。

## 1. 通用说明

1. Aether 对外提供统一 HTTP 入口，并兼容多种 API 形态：
   - OpenAI：`/v1/chat/completions`、`/v1/responses` 等
   - Claude：`/v1/messages`、`/v1/messages/count_tokens`
   - Gemini：`/v1beta/models/{model}:generateContent` 等
2. **客户端使用的是“你的 Aether API Key”**（用户 Key 或独立余额 Key），Aether 再使用 Provider Key 向上游发起请求。
3. 同一个 `GET /v1/models` 会根据你使用的认证 header 自动返回对应格式的模型列表（详见第 5 节）。

## 2. OpenAI 兼容调用（Chat Completions）

### 2.1 非流式

```bash
curl -sS \
  -H "Authorization: Bearer <YOUR_AETHER_API_KEY>" \
  -H "Content-Type: application/json" \
  http://<host>:<port>/v1/chat/completions \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role":"user","content":"hello"}]
  }'
```

### 2.2 流式（SSE）

```bash
curl -N -sS \
  -H "Authorization: Bearer <YOUR_AETHER_API_KEY>" \
  -H "Content-Type: application/json" \
  http://<host>:<port>/v1/chat/completions \
  -d '{
    "model": "gpt-4o-mini",
    "stream": true,
    "messages": [{"role":"user","content":"hello"}]
  }'
```

📎 参考：`src/api/public/openai.py:25`

## 3. Claude 调用（Messages）

Claude 兼容接口需要：

1. `x-api-key: <YOUR_AETHER_API_KEY>`
2. `anthropic-version: 2023-06-01`（或你使用的版本）

```bash
curl -sS \
  -H "x-api-key: <YOUR_AETHER_API_KEY>" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  http://<host>:<port>/v1/messages \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 64,
    "messages": [{"role":"user","content":"hello"}]
  }'
```

Token 计数接口：

```bash
curl -sS \
  -H "x-api-key: <YOUR_AETHER_API_KEY>" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  http://<host>:<port>/v1/messages/count_tokens \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role":"user","content":"hello"}]
  }'
```

📎 参考：`src/api/public/claude.py:24`

## 4. Gemini 调用（generateContent）

Gemini 的模型名在 URL 路径中（不是请求体中的 `model` 字段）。

### 4.1 非流式

```bash
curl -sS \
  -H "x-goog-api-key: <YOUR_AETHER_API_KEY>" \
  -H "Content-Type: application/json" \
  "http://<host>:<port>/v1beta/models/gemini-2.0-flash:generateContent" \
  -d '{
    "contents": [{"parts": [{"text": "hello"}]}]
  }'
```

### 4.2 流式

```bash
curl -N -sS \
  -H "x-goog-api-key: <YOUR_AETHER_API_KEY>" \
  -H "Content-Type: application/json" \
  "http://<host>:<port>/v1beta/models/gemini-2.0-flash:streamGenerateContent" \
  -d '{
    "contents": [{"parts": [{"text": "hello"}]}]
  }'
```

📎 参考：`src/api/public/gemini.py:66`

## 5. Models API（统一模型列表：/v1/models）

`GET /v1/models` 会根据你的认证方式返回对应格式的模型列表：

1. `x-api-key` + `anthropic-version` → Claude 格式
2. `x-goog-api-key` 或 `?key=` → Gemini 格式
3. `Authorization: Bearer` → OpenAI 格式（默认）

示例（OpenAI 格式）：

```bash
curl -sS \
  -H "Authorization: Bearer <YOUR_AETHER_API_KEY>" \
  http://<host>:<port>/v1/models
```

📎 参考：`src/api/public/models.py:1`

## 6. CLI 接入（Claude CLI / OpenAI CLI / Gemini CLI）

思路一致：

1. 将 CLI 的 `base_url` 指向 Aether（例如 `http://<host>:<port>`）。
2. 将 CLI 的 API Key 指向你在 Aether 创建的用户 API Key。
3. Aether 会根据 `x-app` 或 `user-agent` 等信号在必要时切换到对应 CLI adapter（系统会在请求详情/日志里体现）。

OpenAI CLI（Responses API）通常使用：

- `POST /v1/responses`

📎 参考：`src/api/public/openai.py:54`

## 7. 管理令牌（Management Token）怎么用

管理令牌用于访问“管理类 API”（例如批量导入导出、管理端点等），与“用于模型调用的 API Key”不同。

1. 在用户侧或管理端创建 Management Token（以 `ae_` 前缀开头）。
2. 访问管理 API 时使用：
   - `Authorization: Bearer <YOUR_MANAGEMENT_TOKEN>`

提示：

- 管理端点通常要求管理员角色；非管理员即使拿到 Management Token 也会返回 403。

📎 参考：`src/api/base/pipeline.py:181`
