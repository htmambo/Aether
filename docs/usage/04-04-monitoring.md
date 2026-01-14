# 监控与运维（Dashboard / Health / Usage / Trace / Cache）

本文覆盖 Aether 的观测与排障页面：仪表盘、健康监控、使用记录与请求详情、链路追踪，以及缓存监控（含模型映射缓存）。

页面截图：`docs/screenshots/dashboard.png`、`docs/screenshots/health.png`、`docs/screenshots/usage.png`、`docs/screenshots/tracing.png`

![使用记录](../screenshots/usage.png)

## 1. 仪表盘（Dashboard）

入口：

- 用户侧：`/dashboard`
- 管理员：`/admin/dashboard`

用途：

1. 查看请求量、成本、错误率等概览。
2. 快速观察模型/Provider/API 格式的使用分布（不同版本展示略有差异）。

建议用法：

1. 配置/变更 Provider 或 Key 后，先看仪表盘是否出现请求与错误的明显拐点。
2. 再进入“健康监控/使用记录/链路追踪”定位具体来源。

## 2. 健康监控（Health Monitor）

入口：

- 用户侧：`/dashboard/endpoint-status`
- 管理员：`/admin/health-monitor`

用途：

1. 按 API 格式聚合展示近期健康情况（成功率、波动）。
2. 管理员可看到“提供商数量/密钥数量”等更详细的聚合信息。

常用操作：

1. 调整“回溯时间”（1/6/12/24/48 小时）。
2. 点击刷新按钮重新拉取数据。
3. 当某个格式的成功率持续偏低时：
   - 先去 Provider 抽屉检查 Endpoint 是否启用、Key 是否熔断。
   - 再用“模型检测（Test Model）”验证链路（见 `docs/usage/04-01-providers.md`）。

📎 参考：`frontend/src/features/providers/components/HealthMonitorCard.vue:1`

## 3. 使用记录（Usage）与请求详情

入口：

- 用户侧：`/dashboard/usage`
- 管理员：`/admin/usage`

你能做什么：

1. **分析统计**：
   - 管理员：模型 + Provider + API 格式三类统计表
   - 普通用户：模型 + API 格式统计表
2. **请求明细**：
   - 选择时间范围
   - 按用户（管理员）、模型、Provider、状态筛选
   - 支持导出（管理员）
3. **活跃请求跟踪**：
   - 当存在 `pending/streaming` 请求时，页面会更频繁轮询刷新状态。

请求详情（管理员可见）：

1. 点击明细行打开“请求详情抽屉”。
2. 重点查看：
   - 选择了哪条路由（Provider/Key/Endpoint）
   - 重试与故障转移轨迹（如启用）
   - 客户端入站 headers vs Aether 出站 headers

字段含义与各 Tab 排障见：`docs/usage/request-detail-drawer.md`

关于 headers 对比的解释见：`docs/usage/request-detail-headers.md`

📎 参考：`frontend/src/views/shared/Usage.vue:1`

## 4. 链路追踪（Trace）

入口（管理员可见）：**使用记录 → 请求详情抽屉 → 请求链路追踪**

用途：把“一次请求的候选路径与重试过程”可视化，便于排查：

1. 路由选择（为何选中/跳过某些 Provider/Key）
2. 重试/故障转移（失败链路与回退链路）
3. 上游响应（状态码、错误类型、超时等）

使用方法（推荐顺序）：

1. 打开 **管理后台 → 使用记录**（`/admin/usage`）。
2. 点击一条请求明细，打开“请求详情抽屉”。
3. 在抽屉中找到“请求链路追踪”卡片：
   - 时间线节点按 Provider 分组展示；
   - 选中某个 Provider 后，可查看该 Provider 下多次尝试（重试/换 Key）的详情；
   - 若存在 `provider_website`，可直接点击跳转到上游官网。
4. 若你在排查失败：
   - 优先看每次尝试的 `status_code / error_type / error_message / latency_ms`；
   - 再结合“请求头对比”确认 headers 规则、鉴权头、路径是否符合预期。

常见字段含义（与后端一致）：

1. `status`：
   - `success`：候选路径被判定成功（流式场景即使客户端断开，也可能仍算 success）
   - `failed`：请求失败（通常伴随 status_code / error_message）
   - `skipped`：被跳过（会给出 skip_reason，例如白名单/能力不匹配等）
   - `pending/streaming`：请求进行中
2. `key_preview`：脱敏后的 Provider Key 预览（用于定位到底走了哪把 Key）。
3. `required_capabilities` vs `key_capabilities`：请求要求的能力标签与该 Key 声明的能力标签（用于解释“为什么被跳过”）。

截图参考：`docs/screenshots/tracing.png`

高级用法（API）：

- `GET /api/admin/monitoring/trace/{request_id}` 可直接获取该请求的 candidates 明细（需要管理员凭证）。
  参考：`src/api/admin/monitoring/trace.py:55`

## 5. 缓存监控（Cache Monitoring）

入口：**管理后台 → 缓存监控**

该页面通常包含两部分：

1. **缓存统计与亲和性列表（User Affinity）**
   - 查看缓存键数量、命中情况等概览
   - 支持按关键字搜索某个用户/亲和键的记录
   - 支持清除单条亲和性记录或清除全部（危险操作，会二次确认）
2. **TTL 分析**
   - 选择分析窗口（小时数）
   - 展开某个用户查看时间线与请求间隔分布（用于判断缓存亲和是否合理）

排障常见场景：

1. “缓存亲和导致总命中同一条故障 Key”
   - 在缓存监控里按用户搜索并清除该用户的亲和性记录
2. “路由/映射/白名单修改后预览不更新”
   - 优先刷新页面
   - 再在缓存监控中清理相关缓存键（按 UI 操作）

📎 参考：`frontend/src/views/admin/CacheMonitoring.vue:1`

## 6. 模型映射缓存（Model Mapping Cache）

缓存监控页面通常也会提供“模型映射缓存”的统计与清理入口，用于：

1. 映射规则变更后，立即让新规则生效（避免等待缓存过期）。
2. 排查“预览结果与实际路由不一致”的缓存因素。

如果你频繁修改模型映射/别名规则，建议将“清理模型映射缓存”作为排障常规步骤之一。
