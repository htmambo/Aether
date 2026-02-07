# aether-proxy

Aether 正向代理节点，部署在海外 VPS 上，为墙内的 Aether 实例中转 API 流量。

## 下载预编译二进制

在 [GitHub Releases](../../releases) 页面下载对应平台的预编译文件，无需安装 Rust 环境。

| 平台 | 文件 |
|------|------|
| Linux x86_64 | `aether-proxy-linux-amd64.tar.gz` |
| Linux ARM64 | `aether-proxy-linux-arm64.tar.gz` |
| macOS Intel | `aether-proxy-macos-amd64.tar.gz` |
| macOS Apple Silicon | `aether-proxy-macos-arm64.tar.gz` |
| Windows x86_64 | `aether-proxy-windows-amd64.zip` |

```bash
# 下载 & 解压 (以 Linux amd64 为例)
tar xzf aether-proxy-linux-amd64.tar.gz
chmod +x aether-proxy
```

## 发布新版本

推送 `proxy-v*` 格式的 tag，GitHub Actions 会自动编译所有平台并发布到 Releases：

```bash
git tag proxy-v0.1.0
git push origin proxy-v0.1.0
```

也可以在 GitHub → Actions → **Build aether-proxy Binaries** → Run workflow 手动触发编译（不会创建 Release，但可以在 Artifacts 中下载）。

## 从源码编译

```bash
# 需要 Rust 工具链
cargo build --release
# 产物: target/release/aether-proxy
```

## Docker 部署

```bash
docker build -t aether-proxy .

docker run -d \
  --name aether-proxy \
  -p 18080:18080 \
  --env-file .env \
  --restart unless-stopped \
  aether-proxy
```

## 配置

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
```

### 必填

| 变量 | 说明 |
|------|------|
| `AETHER_PROXY_AETHER_URL` | Aether 服务器地址，如 `https://aether.example.com` |
| `AETHER_PROXY_MANAGEMENT_TOKEN` | 管理员 Token（`ae_xxx` 格式，必须属于 ADMIN 用户） |
| `AETHER_PROXY_HMAC_KEY` | HMAC 密钥，**必须与 Aether 端的 `PROXY_HMAC_KEY` 一致** |

### 可选

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_PROXY_LISTEN_PORT` | `18080` | 监听端口 |
| `AETHER_PROXY_PUBLIC_IP` | 自动检测 | 公网 IP，留空则自动获取 |
| `AETHER_PROXY_NODE_NAME` | `proxy-01` | 节点名称标识 |
| `AETHER_PROXY_NODE_REGION` | - | 地区标识，如 `ap-northeast-1` |
| `AETHER_PROXY_HEARTBEAT_INTERVAL` | `30` | 心跳间隔（秒） |
| `AETHER_PROXY_ALLOWED_PORTS` | `80,443,8080,8443` | 允许代理的目标端口 |
| `AETHER_PROXY_TIMESTAMP_TOLERANCE` | `300` | HMAC 时间戳容差（秒） |
| `AETHER_PROXY_LOG_LEVEL` | `info` | 日志级别：trace/debug/info/warn/error |
| `AETHER_PROXY_LOG_JSON` | `false` | 是否输出 JSON 格式日志 |

## 运行

直接运行二进制即可，支持环境变量或 CLI 参数：

```bash
# 使用 .env 文件 (需要先 export)
export $(grep -v '^#' .env | xargs)
./aether-proxy

# 或直接传参
./aether-proxy \
  --aether-url https://aether.example.com \
  --management-token ae_xxx \
  --hmac-key your-hmac-key
```

### 后台运行

**方式一：systemd（推荐，开机自启 + 自动重启）**

创建 `/etc/systemd/system/aether-proxy.service`：

```ini
[Unit]
Description=Aether Proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/aether-proxy
EnvironmentFile=/opt/aether-proxy/.env
ExecStart=/opt/aether-proxy/aether-proxy
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 把二进制和 .env 放到 /opt/aether-proxy/
sudo mkdir -p /opt/aether-proxy
sudo cp aether-proxy .env /opt/aether-proxy/

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable --now aether-proxy

# 常用命令
sudo systemctl status aether-proxy    # 查看状态
sudo systemctl restart aether-proxy   # 重启
sudo journalctl -u aether-proxy -f    # 查看日志
```

**方式二：nohup（简单快速）**

```bash
export $(grep -v '^#' .env | xargs)
nohup ./aether-proxy > aether-proxy.log 2>&1 &

# 查看日志
tail -f aether-proxy.log

# 停止
kill $(pgrep aether-proxy)
```

**方式三：screen / tmux**

```bash
screen -S aether-proxy
export $(grep -v '^#' .env | xargs)
./aether-proxy
# Ctrl+A D 脱离会话

screen -r aether-proxy   # 重新连接
```

## 工作流程

1. **启动** → 自动检测公网 IP（如未配置）
2. **注册** → 向 Aether 发送注册请求 (`POST /api/admin/proxy-nodes/register`)
3. **心跳** → 定时上报节点状态（默认 30 秒）
4. **代理** → 监听端口，接收并转发 Aether 发来的请求
5. **关闭** → 收到 SIGTERM/SIGINT 后优雅退出，向 Aether 发送注销请求

## 安全特性

- **HMAC-SHA256 认证**：所有代理请求必须携带合法签名
- **时间戳防重放**：默认 5 分钟窗口
- **私有 IP 拦截**：阻止访问内网地址（10.x、172.16.x、192.168.x、127.x 等）
- **端口白名单**：仅允许配置的目标端口
- **DNS rebinding 防护**：解析后的 IP 也会检查是否为内网地址
