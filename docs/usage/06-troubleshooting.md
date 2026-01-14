# 常见问题与排障

## 1. “模型测试失败 / 无可用端点或密钥”

排查顺序：

1. Provider 是否启用、Endpoint 是否启用。
2. Key 是否启用、是否支持该 Endpoint 的 API 格式。
3. Key 的 `allowed_models` 是否允许该模型（如配置了白名单）。
4. Endpoint 的 `base_url/custom_path` 是否正确。
5. 是否配置了必要的代理/自定义 headers。

## 2. “此规则暂无匹配的 Key 白名单”

含义：在“模型详情抽屉 → 模型映射/别名规则”里，你的正则规则没有匹配到任何 Provider Key 的 `allowed_models`（Key 白名单）里的模型名。

常见原因：

1. 相关 Provider Key 没配置模型白名单（`allowed_models` 为 `null` 表示不限制，因此不会出现在“白名单匹配预览”里）。
2. 别名正则写错或与白名单模型名不匹配（例如白名单里是 `gpt-4o-mini`，你写成了 `gpt4o.*`）。
3. 你以为是在配置“模型映射”，但其实是在配置“别名规则预览”（该区域只做匹配预览，不会自动生成白名单）。

解决：

1. 到 Provider 抽屉 → 密钥管理 → Key 行右侧“盾牌”按钮“模型权限”中配置 `allowed_models`。
2. 回到模型详情抽屉 → 刷新预览（必要时刷新页面）。

补充：如果对话框里只有“两个列表”看起来不能手动输入，正确的手动添加方式是：

1. 在顶部搜索框输入模型名。
2. 点击出现的“添加自定义模型”。

## 3. 自定义 Headers 不生效

优先检查：

1. 是否触发“最高安全规则”（敏感/协议头不可注入或覆盖，例如 `Authorization`/`x-api-key`/`Host` 等）。
2. 是否写成规则格式但实际上需要 `add/remove/replace_*` 的组合（例如你想“覆盖”某 header，但 `add` 不会覆盖已存在值）。
3. 是否把 header 加在了错误的位置（客户端入站 headers vs Aether 出站 headers）。

建议做法：

1. 先在 Endpoint 的“Headers配置”里保存规则。
2. 再用 Provider 抽屉里的“模型检测（Test Model）”验证是否生效。
3. 最后在“使用记录 → 请求详情”里对比出站 headers（管理员可见）。

## 4. 频繁 429 / 限速

排查顺序：

1. 查看使用记录与响应头中的限速提示（如有）。
2. 调整 Key 的 rpm_limit 或启用自适应模式。
3. 扩充 Key 数量或增加 Provider 冗余。

## 5. 修改配置后页面预览未更新

尝试：

1. 刷新页面。
2. 管理后台 → 缓存监控 → 清理相关缓存键。

## 6. Claude 调用返回 400/401（anthropic-version）

现象：调用 `POST /v1/messages` 返回类似“缺少 anthropic-version”或鉴权失败。

检查：

1. 客户端请求头是否包含 `anthropic-version`。
2. 客户端是否使用了 `x-api-key: <YOUR_AETHER_API_KEY>`（而不是 Provider Key）。
3. 若你需要“固定某个版本”或“补充上游必须 header”，在 Endpoint 的“Headers配置”里添加 `anthropic-version`（并用模型检测验证）。

## 7. 导入导出失败（系统设置）

优先检查：

1. 文件大小是否超过 10MB。
2. config 文件版本是否为 `2.0`。
3. users 文件是否包含管理员用户数据（管理员导入会被跳过并计入 errors）。
4. config 导入的 Key 是否声明了不存在的 `api_formats`（需要先创建对应 Endpoint）。
5. 是否需要保留“查看完整 key”能力（`ENCRYPTION_KEY` 不同会影响解密 `key_encrypted`）。

详细说明见：`docs/usage/system-import-export.md`
