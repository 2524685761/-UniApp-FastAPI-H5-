#!/bin/bash

echo "========================================"
echo "启动情感伴学系统后端服务"
echo "========================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.8+"
    exit 1
fi

echo "[1/3] 检查依赖..."
if [ ! -f "backend/requirements.txt" ]; then
    echo "[错误] 未找到 backend/requirements.txt"
    exit 1
fi

echo "[2/3] 安装/更新依赖包..."
pip3 install -r backend/requirements.txt

echo "[3/3] 启动后端服务..."
echo ""
echo "服务将在 http://127.0.0.1:8000 启动"
echo "API 文档地址: http://127.0.0.1:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

