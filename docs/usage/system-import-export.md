# 系统设置：配置 / 用户数据 导入导出（Import & Export）

本手册说明“管理后台 → 系统设置”里的两类导入导出能力，并解释导出文件的 JSON 结构、冲突策略（`merge_mode`）和常见错误排查。

你会用到两类文件：

1. **配置文件（config）**：Provider / Endpoint / Provider Keys / GlobalModel / Model（关联模型）等
2. **用户数据文件（users）**：普通用户与其 API Keys + 独立余额 Keys（Standalone Keys）

📎 参考：
- 前端入口与 10MB 限制：`frontend/src/views/admin/SystemSettings.vue:1097`
- 配置导出/导入：`src/api/admin/system.py:364`、`src/api/admin/system.py:685`
- 用户导出/导入：`src/api/admin/system.py:378`、`src/api/admin/system.py:1254`

---

## 1. 入口与权限

入口：**管理后台 → 系统设置**（`/admin/settings`）

权限：导入/导出为管理员功能（需要管理员登录与权限）。

---

## 2. 配置（config）导出/导入

### 2.1 导出配置（下载 JSON）

用途：

- 备份当前 Provider + 模型配置
- 环境迁移（测试 → 生产）
- 快速复制同一套 Provider/模型到另一套部署

操作：

1. 进入 **系统设置**
2. 点击 **导出配置**
3. 浏览器会下载 `aether-config-YYYY-MM-DD.json`

重要安全提示：

- config 导出会包含 **Provider Key 的明文**（用于可迁移性）。
- 不要把导出文件提交到 Git；不要通过不安全渠道传输；建议离线保存或自行二次加密。

📎 参考：`src/api/admin/system.py:685`

### 2.2 导入配置（选择文件 → 预览 → 选择 merge_mode）

操作：

1. 点击 **导入配置**
2. 选择 `aether-config-*.json`（最大 10MB）
3. 系统会做基本校验并展示预览（包含 `version`）
4. 选择冲突处理策略 `merge_mode`：`skip` / `overwrite` / `error`
5. 确认导入，查看导入结果统计（created/updated/skipped/errors）

版本要求：

- 前端仅接受 `version = "2.0"` 的 config 文件

📎 参考：`frontend/src/views/admin/SystemSettings.vue:1147`

### 2.3 merge_mode 是什么？冲突怎么判定？

`merge_mode` 只影响“目标库里已存在同名/同键记录”时的处理方式：

- `skip`：跳过已存在对象（仍会继续尝试导入其子项；例如 Provider 已存在时仍会导入其 Endpoints/Models/Keys）
- `overwrite`：更新已存在对象的字段
- `error`：遇到已存在对象直接报错并终止导入

配置导入的“匹配键”（也就是判定“已存在”的依据）：

- GlobalModel：`name`
- Provider：`name`
- Endpoint：`(provider_id, api_format)`（同一 Provider 下同一格式只能有一个 Endpoint）
- Model（关联模型）：`(provider_id, provider_model_name)`

Provider Keys 的特殊点（与其他对象不同）：

- 去重依据是 **明文 api_key 值** 是否已存在于该 Provider 下（通过解密现有 key 对比）。
- 去重时不区分 `merge_mode`：重复 key 会直接跳过，不会覆盖更新。

📎 参考：`src/api/admin/system.py:874`、`src/api/admin/system.py:1048`、`src/api/admin/system.py:1073`

### 2.4 导入时的关键校验（常见 “errors” 来源）

1. **Key 的 `api_formats` 必须在该 Provider 下存在对应 Endpoint**
   - 若 Key 声明了某个格式，但 Provider 里没有该格式 Endpoint，该格式会被跳过并记入 `errors`
   - 如果一个 Key 的全部格式都被判定为缺失，则该 Key 整体跳过

2. **Model 必须能找到对应 GlobalModel**
   - 若 `global_model_name` 不存在，会跳过该 Model 并记入 `errors`

3. **导出时无法解密 Provider Key**
   - config 导出会尝试解密 Provider Key；解密失败会导出 `api_key=""`
   - 导入时会把空 key 视为无效并跳过

📎 参考：`src/api/admin/system.py:724`、`src/api/admin/system.py:1068`

### 2.5 config 文件结构（示例）

下面是“结构示意”，字段以实际导出为准（省略部分可选字段）：

```json
{
  "version": "2.0",
  "exported_at": "2026-01-14T00:00:00+00:00",
  "global_models": [
    {
      "name": "gpt-4o-mini",
      "display_name": "GPT-4o mini",
      "default_tiered_pricing": { "tiers": [] },
      "supported_capabilities": ["chat", "streaming"],
      "is_active": true
    }
  ],
  "providers": [
    {
      "name": "OpenAI",
      "billing_type": "pay_as_you_go",
      "quota_reset_day": 30,
      "is_active": true,
      "endpoints": [
        {
          "api_format": "OPENAI",
          "base_url": "https://api.openai.com",
          "headers": null,
          "is_active": true
        }
      ],
      "api_keys": [
        {
          "name": "main-key",
          "api_key": "sk-REDACTED-PLAINTEXT",
          "api_formats": ["OPENAI"],
          "internal_priority": 10,
          "is_active": true
        }
      ],
      "models": [
        {
          "global_model_name": "gpt-4o-mini",
          "provider_model_name": "gpt-4o-mini",
          "is_active": true
        }
      ]
    }
  ]
}
```

📎 参考：`src/api/admin/system.py:685`

---

## 3. 用户数据（users）导出/导入

### 3.1 导出用户数据（下载 JSON）

用途：

- 迁移普通用户数据（不包含管理员用户）
- 迁移普通用户的 API Keys（不包含独立余额 Key）
- 迁移独立余额 Keys（Standalone Keys，单独导出在 `standalone_keys`）

操作：

1. 进入 **系统设置**
2. 点击 **导出用户数据**
3. 浏览器会下载 `aether-users-YYYY-MM-DD.json`

导出内容说明：

- `users`：仅导出 `role != admin` 且未删除的用户
- `api_keys`：导出用户的非独立 key（`is_standalone=false`）
- `standalone_keys`：独立余额 key（`is_standalone=true`）单独导出
- key 不导出明文，只导出 `key_hash` 和（可选）`key_encrypted`

📎 参考：`src/api/admin/system.py:1254`

### 3.2 导入用户数据（选择文件 → 预览 → 选择 merge_mode）

操作：

1. 点击 **导入用户数据**
2. 选择 `aether-users-*.json`（最大 10MB）
3. 选择 `merge_mode`：`skip` / `overwrite` / `error`
4. 确认导入并查看统计

用户导入的“匹配键”（判定已存在）：

- User：`email`
- ApiKey：`key_hash`（系统用 `key_hash` 判定重复，重复直接跳过）

管理员与 Standalone Keys：

- 导入时会跳过 `role=admin` 的用户数据，并写入 `errors`
- `standalone_keys` 需要系统里存在至少一个管理员用户作为 owner；否则会记录错误并跳过导入

📎 参考：`src/api/admin/system.py:1360`、`src/api/admin/system.py:1494`

### 3.3 ENCRYPTION_KEY 一致性：必须吗？

用户导出文件里包含：

- `key_hash`：用于验证调用方提交的明文 key（认证依赖它）
- `key_encrypted`：用于“查看完整 key / 显示脱敏 key”（展示依赖它）

因此：

- **不要求**两边 `ENCRYPTION_KEY` 相同才能“继续使用这些 keys 调用”（因为验证基于 `key_hash`）。
- **如果希望**在新环境仍能“查看完整 key / 正常显示 key 预览”，需要确保导入的 `key_encrypted` 能被解密（通常意味着两边 `ENCRYPTION_KEY` 一致）。

📎 参考：`src/services/user/apikey.py:56`、`src/services/user/apikey.py:97`、`src/models/database.py:245`、`src/api/user_me/routes.py:563`

### 3.4 users 文件结构（示例）

```json
{
  "version": "1.1",
  "exported_at": "2026-01-14T00:00:00+00:00",
  "users": [
    {
      "email": "alice@example.com",
      "username": "alice",
      "role": "user",
      "is_active": true,
      "quota_usd": 50,
      "api_keys": [
        {
          "name": "alice-key",
          "key_hash": "sha256-hex",
          "key_encrypted": "encrypted-string",
          "is_standalone": false,
          "is_active": true,
          "expires_at": null
        }
      ]
    }
  ],
  "standalone_keys": [
    {
      "name": "promo-key-001",
      "key_hash": "sha256-hex",
      "key_encrypted": "encrypted-string",
      "is_active": true
    }
  ]
}
```

📎 参考：`src/api/admin/system.py:1254`

---

## 4. API 方式（可选）

如果你需要自动化迁移/备份，可直接调用管理员 API：

```bash
# 导出配置
curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "<BASE_URL>/api/admin/system/config/export" > aether-config.json

# 导入配置（merge_mode: skip|overwrite|error）
curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @aether-config.json \
  "<BASE_URL>/api/admin/system/config/import"

# 导出用户
curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "<BASE_URL>/api/admin/system/users/export" > aether-users.json

# 导入用户（merge_mode: skip|overwrite|error）
curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @aether-users.json \
  "<BASE_URL>/api/admin/system/users/import"
```

📎 参考：`src/api/admin/system.py:364`

---

## 5. 常见问题与排障

### 5.1 “文件大小不能超过 10MB”

- 前端与后端都限制为 10MB
- 建议先拆分导入（例如只导入 config，或分批导入 users）

📎 参考：`src/api/admin/system.py:825`、`frontend/src/views/admin/SystemSettings.vue:1125`

### 5.2 “不支持的配置版本: X”

- config 导入只接受 `version="2.0"`（前端也会校验）

📎 参考：`src/api/admin/system.py:846`

### 5.3 “Key 的 api_formats 未配置对应 Endpoint”

- 先在目标环境保证该 Provider 下存在对应格式的 Endpoint
- 再导入 keys；或修改导入文件里 Key 的 `api_formats`

📎 参考：`src/api/admin/system.py:1101`

### 5.4 导入后预览/路由未立即更新

- config 导入成功后会清理缓存（短时间内页面可能需要刷新）

📎 参考：`src/api/admin/system.py:1239`
