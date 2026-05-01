#!/bin/bash
# Office Agent v2 - One-Click Start
# Usage: bash start.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🤖 Office Agent v2  启动中...    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Check Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python 未安装，请先安装 Python 3.10+"
    exit 1
fi

echo "✅ Python: $($PYTHON --version)"

# Check & install deps
echo ""
echo "📦 检查依赖..."
missing=0
for pkg in fastapi uvicorn streamlit pandas openpyxl python-docx pdfplumber plotly httpx; do
    if ! $PYTHON -c "import $pkg" 2>/dev/null; then
        missing=1
    fi
done

if [ "$missing" -eq 1 ]; then
    echo "  安装缺失依赖..."
    pip install --break-system-packages -r requirements.txt 2>&1 | tail -3 || pip install -r requirements.txt 2>&1 | tail -3
    echo "✅ 依赖安装完成"
else
    echo "✅ 所有依赖已就绪"
fi

echo ""

# Kill any existing processes on our ports
for port in 8000 8501; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
        echo "🔫 释放端口 $port"
    fi
done

# Start API backend
echo "🚀 启动后端 API (port 8000)..."
$PYTHON -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload --log-level warning &
API_PID=$!

# Wait for API
echo "  等待后端启动..."
for i in $(seq 1 15); do
    if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        echo "✅ 后端已就绪"
        break
    fi
    sleep 1
done

# Start Streamlit UI
echo "🚀 启动前端 UI (port 8501)..."
$PYTHON -m streamlit run ui/app.py --server.port 8501 --server.headless true &
UI_PID=$!

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║                                      ║"
echo "  ║   🎉 Office Agent v2 已启动!       ║"
echo "  ║                                      ║"
echo "  ║   后端: http://127.0.0.1:8000       ║"
echo "  ║   前端: http://127.0.0.1:8501       ║"
echo "  ║                                      ║"
echo "  ║   按 Ctrl+C 停止所有服务            ║"
echo "  ║                                      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

trap "echo ''; echo '🛑 正在停止...'; kill $API_PID $UI_PID 2>/dev/null; wait $API_PID $UI_PID 2>/dev/null; echo '✅ 已停止'; exit" INT TERM
wait
