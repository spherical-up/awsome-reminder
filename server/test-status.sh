#!/bin/bash

echo "=========================================="
echo "提醒服务状态检查"
echo "=========================================="
echo ""

echo "1. 服务健康检查..."
curl -s http://127.0.0.1:5000/api/health | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:5000/api/health
echo ""
echo ""

echo "2. 提醒记录列表..."
REMINDERS=$(curl -s http://127.0.0.1:5000/api/debug/reminders)
echo "$REMINDERS" | python3 -m json.tool 2>/dev/null || echo "$REMINDERS"
echo ""

# 提取提醒ID（如果有）
REMINDER_IDS=$(echo "$REMINDERS" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(r['id']) for r in data.get('data', [])]" 2>/dev/null)

echo "3. 定时任务列表..."
JOBS=$(curl -s http://127.0.0.1:5000/api/debug/jobs)
echo "$JOBS" | python3 -m json.tool 2>/dev/null || echo "$JOBS"
echo ""

echo "4. 最近的服务日志（相关关键词）..."
docker logs reminder-server --tail 30 2>&1 | grep -E "(创建提醒|安排提醒|定时任务|发送提醒|订阅消息)" | tail -10 || echo "暂无相关日志"
echo ""

if [ ! -z "$REMINDER_IDS" ]; then
    echo "=========================================="
    echo "发现提醒记录，可以手动测试发送："
    echo "=========================================="
    for id in $REMINDER_IDS; do
        echo ""
        echo "手动发送提醒 ID: $id"
        echo "命令: curl -X POST http://127.0.0.1:5000/api/debug/reminder/$id/send"
    done
    echo ""
fi

echo "=========================================="
echo "检查完成"
echo "=========================================="

