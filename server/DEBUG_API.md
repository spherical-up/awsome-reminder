# 调试接口使用指南

## 问题：接口返回 404

如果访问调试接口返回 404，可能是：

1. **服务未重启**：新添加的接口需要重启服务才能生效
2. **路由路径错误**：检查 URL 是否正确

## 解决步骤

### 1. 重启服务

**如果使用 Supervisor：**
```bash
supervisorctl restart reminder-server
```

**如果直接运行：**
```bash
# 停止服务（Ctrl+C）
# 重新启动
cd server
python app.py
```

**如果使用 Docker：**
```bash
docker-compose restart
```

### 2. 验证服务已重启

```bash
# 检查健康接口
curl http://127.0.0.1:5000/api/health

# 应该返回：
# {"errcode": 0, "errmsg": "success", "status": "healthy"}
```

### 3. 测试调试接口

```bash
# 查看定时任务
curl http://127.0.0.1:5000/api/debug/jobs

# 查看所有提醒
curl http://127.0.0.1:5000/api/debug/reminders
```

## 所有调试接口

### 1. 查看定时任务

```bash
GET /api/debug/jobs
```

**响应示例：**
```json
{
    "errcode": 0,
    "errmsg": "success",
    "data": {
        "total": 1,
        "jobs": [
            {
                "id": "reminder_1764689115406",
                "name": null,
                "next_run_time": "2024-01-01 10:30:00",
                "trigger": "date[2024-01-01 10:30:00 CST]"
            }
        ],
        "scheduler_running": true
    }
}
```

### 2. 查看所有提醒

```bash
GET /api/debug/reminders
```

**响应示例：**
```json
{
    "errcode": 0,
    "errmsg": "success",
    "data": [
        {
            "id": 1764689115406,
            "openid": "xxx",
            "title": "测试提醒",
            "time": "2024-01-01 10:30:00",
            "reminderTime": 1704067200000,
            "enableSubscribe": true,
            "status": "pending"
        }
    ]
}
```

### 3. 手动发送提醒

```bash
POST /api/debug/reminder/{reminder_id}/send
```

**示例：**
```bash
curl -X POST http://127.0.0.1:5000/api/debug/reminder/1764689115406/send
```

**响应示例：**
```json
{
    "errcode": 0,
    "errmsg": "success",
    "data": {
        "result": {
            "errcode": 0,
            "errmsg": "ok"
        },
        "message": "提醒发送成功"
    }
}
```

## 排查未收到提醒的步骤

### 步骤1：检查定时任务

```bash
curl http://127.0.0.1:5000/api/debug/jobs
```

**如果 `total: 0`：**
- 定时任务没有创建
- 检查创建提醒时的日志

**如果 `scheduler_running: false`：**
- 调度器未启动
- 重启服务

### 步骤2：查看提醒记录

```bash
curl http://127.0.0.1:5000/api/debug/reminders
```

检查：
- `enableSubscribe` 是否为 `true`
- `reminderTime` 是否正确
- `status` 状态

### 步骤3：手动测试发送

```bash
# 替换为你的提醒ID
curl -X POST http://127.0.0.1:5000/api/debug/reminder/1764689115406/send
```

**如果成功：**
- 说明订阅消息功能正常
- 问题在定时任务执行

**如果失败：**
- 查看返回的错误信息
- 检查错误码

### 步骤4：查看日志

```bash
# 查看错误日志
tail -f /var/log/reminder-server/error.log

# 或查看控制台输出
```

查找关键日志：
- `安排提醒任务`
- `开始发送提醒`
- `发送订阅消息失败`

## 常见问题

### Q: 接口返回 404

**A:** 服务未重启，需要重启服务使新接口生效

### Q: 定时任务列表为空

**A:** 
- 检查创建提醒时是否开启了订阅
- 检查提醒时间是否已过
- 查看创建提醒时的日志

### Q: 手动发送失败

**A:** 查看返回的错误码：
- 43101: 用户未授权，需要重新授权
- 40037: 模板ID错误
- 47003: 模板数据格式错误

### Q: 定时任务存在但不执行

**A:**
- 检查 `next_run_time` 是否正确
- 检查服务时间是否准确
- 查看调度器是否运行

## 快速测试脚本

```bash
#!/bin/bash

echo "1. 检查服务健康..."
curl http://127.0.0.1:5000/api/health
echo ""

echo "2. 查看定时任务..."
curl http://127.0.0.1:5000/api/debug/jobs
echo ""

echo "3. 查看所有提醒..."
curl http://127.0.0.1:5000/api/debug/reminders
echo ""

echo "4. 手动发送测试（需要替换 reminder_id）..."
# curl -X POST http://127.0.0.1:5000/api/debug/reminder/1764689115406/send
```

