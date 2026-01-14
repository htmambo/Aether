# 部署与启动

本文覆盖部署方式、初始化步骤、升级与常用运维命令。

## 1. 部署方式

### 1.1 Docker Compose（推荐：预构建镜像）

```bash
git clone https://github.com/fawney19/Aether.git
cd Aether
cp .env.example .env
python3 generate_keys.py
docker compose pull && docker compose up -d
```

### 1.2 Docker Compose（本地构建镜像）

```bash
git clone https://github.com/fawney19/Aether.git
cd Aether
cp .env.example .env
python3 generate_keys.py
./deploy.sh
```

### 1.3 本地开发

```bash
docker compose -f docker-compose.build.yml up -d postgres redis
uv sync
./dev.sh
cd frontend && npm install && npm run dev
```

## 2. 初始化与必需配置

1. 复制 `.env.example` 为 `.env`。
2. 执行 `python3 generate_keys.py` 生成 `JWT_SECRET_KEY` / `ENCRYPTION_KEY` 等密钥并写入 `.env`。
3. 启动后使用 `.env` 中的 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 登录管理后台。

### 2.1 必需环境变量（最小可运行集）

以 `.env.example` 为准，通常至少需要：

- 数据库：`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_NAME` / `DB_PASSWORD`
- Redis：`REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD`
- 安全密钥：`JWT_SECRET_KEY` / `ENCRYPTION_KEY`
- 初始管理员：`ADMIN_EMAIL` / `ADMIN_USERNAME` / `ADMIN_PASSWORD`

**重要提醒（不可忽略）**

- `ENCRYPTION_KEY` 用于加密 Provider API Key；更换后旧 Key 可能无法解密，需要重新录入。
- 建议尽早配置 HTTPS（反向代理或 LB），并限制管理后台访问来源（结合 IP 白名单）。

## 3. 升级/更新

**预构建镜像**

```bash
docker compose pull && docker compose up -d
```

**本地构建**

```bash
./deploy.sh
```

升级会自动执行数据库迁移（见 `deploy.sh`/`docker-compose.yml` 的启动流程）。

## 4. 常用运维命令

```bash
docker compose ps
docker compose logs -f --tail=200
docker compose restart
docker compose down
```

## 5. 端口与访问

- 默认应用端口：`.env` 中的 `APP_PORT`（示例为 8084）
- 典型访问：
  - 前端管理后台：`http://<host>:<APP_PORT>/`
  - API 入口：`http://<host>:<APP_PORT>/api/...`
