#!/bin/bash
# 本地开发启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载 .env 文件
set -a
source .env
set +a

# 数据库类型选择（默认 sqlite，可选 postgres）
DB_TYPE="${USE_DATABASE:-sqlite}"

# 构建 DATABASE_URL 和 REDIS_URL
if [ "$DB_TYPE" = "postgres" ]; then
    # 使用 PostgreSQL
    export DATABASE_URL="postgresql://${DB_USER:-postgres}:${DB_PASSWORD}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-aether}"
    DB_ICON="🐘"
    DB_NAME_DISPLAY="PostgreSQL"
else
    # 使用 SQLite（默认）
    export DATABASE_URL="sqlite:///./data/aether.db"
    DB_ICON="🗄️"
    DB_NAME_DISPLAY="SQLite"
fi

export REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}/0"

# PIDs 用于存储进程 ID
BACKEND_PID=""
FRONTEND_PID=""

# 清理函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."

    if [ -n "$BACKEND_PID" ]; then
        echo "  停止后端 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi

    if [ -n "$FRONTEND_PID" ]; then
        echo "  停止前端 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi

    # 等待进程结束
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null

    echo "✅ 所有服务已停止"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 清屏并显示欢迎信息
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Aether 本地开发服务器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 后端地址: http://localhost:8084"
echo "📍 前端地址: http://localhost:5173"
echo ""
echo "${DB_ICON} 数据库类型: ${DB_NAME_DISPLAY}"
echo "📊 数据库连接: ${DATABASE_URL}"
echo ""
echo "💡 提示: 按 Ctrl+C 停止所有服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 启动后端（在后台）
echo "🔧 正在启动后端服务..."
uv run uvicorn src.main:app --reload --port 8084 > /tmp/aether_backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 检查后端是否启动成功
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败，查看日志: /tmp/aether_backend.log"
    cat /tmp/aether_backend.log
    cleanup
fi

# 启动前端（在前台）
echo "🎨 正在启动前端服务..."
cd frontend

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo "📦 首次启动，正在安装前端依赖..."
    npm install
fi

# 启动前端开发服务器
npm run dev &
FRONTEND_PID=$!

# 回到项目根目录
cd "$SCRIPT_DIR"

# 等待前端启动
sleep 2

# 检查前端是否启动成功
if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
else
    echo "❌ 前端服务启动失败"
    cleanup
fi

echo ""
echo "🎉 所有服务已启动！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 后端日志: tail -f /tmp/aether_backend.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 保持脚本运行，等待信号
wait $FRONTEND_PID $BACKEND_PID
