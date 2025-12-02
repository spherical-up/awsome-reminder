#!/bin/bash

echo "正在重启服务..."

# 检查是否使用 Docker
if docker ps | grep -q reminder; then
    echo "检测到 Docker 容器，重启容器..."
    docker-compose restart
    echo "✅ Docker 容器已重启"
elif [ -f "/etc/supervisor/conf.d/reminder-server.conf" ] || supervisorctl status reminder-server 2>/dev/null | grep -q reminder-server; then
    echo "检测到 Supervisor，重启服务..."
    supervisorctl restart reminder-server
    echo "✅ Supervisor 服务已重启"
else
    echo "⚠️  未检测到 Docker 或 Supervisor"
    echo "如果服务是直接运行的，请："
    echo "1. 停止当前服务（Ctrl+C）"
    echo "2. 重新运行: cd server && python app.py"
    echo ""
    echo "或者手动查找并重启："
    echo "ps aux | grep app.py"
    echo "kill <PID>"
    echo "cd server && python app.py"
fi

echo ""
echo "等待 2 秒后测试接口..."
sleep 2

echo ""
echo "测试健康检查接口..."
curl -s http://127.0.0.1:5000/api/health

echo ""
echo ""
echo "测试调试接口..."
curl -s http://127.0.0.1:5000/api/debug/jobs

echo ""
echo ""
echo "✅ 完成！"

