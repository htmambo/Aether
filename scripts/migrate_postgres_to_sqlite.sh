#!/bin/bash
#
# PostgreSQL → SQLite 快捷迁移脚本
#
# 使用方法:
#   ./scripts/migrate_postgres_to_sqlite.sh
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
SQLITE_DB="${SQLITE_DB:-./data/aether.db}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-aether}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
BATCH_SIZE="${BATCH_SIZE:-1000}"

# 加载 .env 文件
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}    PostgreSQL → SQLite 数据迁移工具${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

# 检查 SQLite 目录
SQLITE_DIR=$(dirname "$SQLITE_DB")
if [ ! -d "$SQLITE_DIR" ]; then
    echo -e "${YELLOW}⚠️  创建目录: $SQLITE_DIR${NC}"
    mkdir -p "$SQLITE_DIR"
fi

echo -e "${YELLOW}📋 迁移配置:${NC}"
echo "  PostgreSQL 主机: $POSTGRES_HOST:$POSTGRES_PORT"
echo "  PostgreSQL 数据库: $POSTGRES_DB"
echo "  PostgreSQL 用户: $POSTGRES_USER"
echo "  SQLite 数据库: $SQLITE_DB"
echo "  批处理大小: $BATCH_SIZE"
echo ""

# 提示输入密码
if [ -z "$POSTGRES_PASSWORD" ]; then
    read -sp -p "请输入 PostgreSQL 密码: " POSTGRES_PASSWORD
    echo ""
    export POSTGRES_PASSWORD
fi

# 构建 PostgreSQL URL
POSTGRES_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# 确认信息
echo ""
echo -e "${YELLOW}⚠️  警告:${NC}"
echo "  SQLite 不适合高并发或大数据量场景"
echo "  建议仅用于开发/测试环境"
echo ""
echo -e "${YELLOW}⚠️  即将开始迁移，请确认:${NC}"
echo "  1. SQLite 数据库文件可创建"
echo "  2. PostgreSQL 数据库可访问"
echo "  3. 建议备份 PostgreSQL 数据库"
echo ""
read -p "确认开始迁移？(yes/no): " confirm

if [ "$confirm" != "yes" ] && [ "$confirm" != "y" ]; then
    echo "已取消迁移"
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 开始迁移...${NC}"
echo ""

# 执行迁移
python -m scripts.migration.postgres_to_sqlite \
    --postgres "$POSTGRES_URL" \
    --sqlite "sqlite:///${SQLITE_DB}" \
    --batch-size "$BATCH_SIZE"

# 检查返回值
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}✅ 迁移成功完成！${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "下一步:"
    echo "  1. 更新 .env 配置:"
    echo "     DATABASE_URL=sqlite:///${SQLITE_DB}"
    echo "  2. 重启应用:"
    echo "     systemctl restart aether"
    echo "  3. 验证功能正常"
    echo ""
    echo -e "${YELLOW}⚠️  注意:${NC}"
    echo "  SQLite 不适合生产环境使用"
    echo "  如需生产环境，请使用 PostgreSQL"
    echo ""
else
    echo ""
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ 迁移失败！${NC}"
    echo -e "${RED}============================================================${NC}"
    echo ""
    echo "请检查:"
    echo "  1. SQLite 文件路径是否可写"
    echo "  2. 数据库连接是否正确"
    echo "  3. 日志中的详细错误信息"
    echo ""
    exit 1
fi
