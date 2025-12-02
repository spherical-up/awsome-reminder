# 订阅消息未收到 - 问题排查指南

## 问题现象

提醒时间到了，但没有收到订阅消息。

## 排查步骤

### 1. 检查定时任务是否创建

**查看所有定时任务：**

```bash
curl http://localhost:5000/api/debug/jobs
```

**预期响应：**
```json
{
    "errcode": 0,
    "data": {
        "total": 1,
        "jobs": [
            {
                "id": "reminder_1764689115406",
                "next_run_time": "2024-01-01 10:30:00",
                "trigger": "date[2024-01-01 10:30:00 CST]"
            }
        ],
        "scheduler_running": true
    }
}
```

**如果 `total: 0`：**
- 定时任务没有创建
- 检查创建提醒时的日志

**如果 `scheduler_running: false`：**
- 调度器未启动
- 检查服务启动日志

### 2. 检查提醒记录

**查看所有提醒：**

```bash
curl http://localhost:5000/api/debug/reminders
```

**检查要点：**
- `enableSubscribe` 是否为 `true`
- `reminderTime` 是否正确
- `status` 状态（pending/sent/failed）

### 3. 手动测试发送

**手动触发发送（用于测试）：**

```bash
curl -X POST http://localhost:5000/api/debug/reminder/1764689115406/send
```

**如果手动发送成功：**
- 说明订阅消息功能正常
- 问题可能在定时任务执行

**如果手动发送失败：**
- 查看返回的错误信息
- 检查常见错误码

### 4. 查看服务端日志

**关键日志信息：**

```bash
# 查看日志
tail -f /var/log/reminder-server/access.log
tail -f /var/log/reminder-server/error.log

# 或如果直接运行
# 查看控制台输出
```

**需要检查的日志：**

1. **创建提醒时：**
   ```
   安排提醒任务: ID=xxx, 提醒时间=xxx, 当前时间=xxx
   ✅ 已安排提醒任务: ID=xxx, 任务ID=reminder_xxx
   ```

2. **到达提醒时间时：**
   ```
   开始发送提醒: ID=xxx, openid=xxx
   准备发送订阅消息: openid=xxx, template_id=xxx
   微信API响应: {...}
   ```

3. **发送结果：**
   ```
   ✅ 提醒发送成功: ID=xxx
   或
   ❌ 提醒发送失败: errcode=xxx, errmsg=xxx
   ```

### 5. 常见错误码

| 错误码 | 说明 | 解决方法 |
|--------|------|----------|
| 40001 | access_token 无效 | 检查 AppID 和 AppSecret |
| 40003 | openid 无效 | 检查 openid 是否正确 |
| 43101 | 用户拒绝接受消息 | 用户需要重新授权订阅 |
| 47003 | 模板参数不正确 | 检查模板数据格式 |
| 41030 | page 路径不正确 | 检查 page 参数 |
| 40037 | 模板ID无效 | 检查模板ID是否正确 |

### 6. 检查时间戳

**问题：** 时间戳可能不正确

**验证：**

```python
# 在 Python 中
from datetime import datetime
timestamp = 1764689115406  # 你的时间戳
dt = datetime.fromtimestamp(timestamp / 1000)
print(f"时间戳对应的时间: {dt}")
print(f"当前时间: {datetime.now()}")
```

**如果时间已过：**
- 定时任务不会执行
- 日志会显示"提醒时间已过"

### 7. 检查订阅授权

**重要：** 用户必须授权订阅消息才能收到

**检查方法：**
1. 在小程序中重新开启订阅开关
2. 确认授权弹窗点击"允许"
3. 检查授权状态

### 8. 验证模板数据格式

**模板数据格式：**

```python
{
    'thing1': {'value': '提醒内容'},  # 最多20字
    'time2': {'value': '2024-01-01 10:30:00'}
}
```

**检查：**
- `thing1` 的值不能超过20字
- `time2` 的格式要符合模板要求
- 字段名要与模板配置一致

## 快速诊断命令

```bash
# 1. 检查定时任务
curl http://localhost:5000/api/debug/jobs

# 2. 查看所有提醒
curl http://localhost:5000/api/debug/reminders

# 3. 手动发送测试（替换 reminder_id）
curl -X POST http://localhost:5000/api/debug/reminder/1764689115406/send

# 4. 检查服务健康
curl http://localhost:5000/api/health
```

## 解决方案

### 方案1：定时任务未执行

**可能原因：**
- 服务重启，定时任务丢失（使用内存存储）
- 时间已过，任务被跳过

**解决：**
- 使用数据库持久化存储
- 服务启动时重新加载未完成的提醒

### 方案2：订阅消息发送失败

**检查日志中的错误码：**

```bash
# 查看错误日志
grep "发送订阅消息失败" /var/log/reminder-server/error.log
```

**根据错误码处理：**
- 40001: 重新获取 access_token
- 43101: 用户需要重新授权
- 47003: 检查模板数据格式

### 方案3：用户未授权

**解决：**
1. 在小程序中重新开启订阅
2. 确保点击"允许"授权
3. 检查授权状态

## 预防措施

1. **使用数据库存储**：避免服务重启丢失任务
2. **添加重试机制**：发送失败时自动重试
3. **定期检查任务**：监控定时任务状态
4. **记录详细日志**：便于问题排查

## 测试流程

1. 创建提醒（设置未来1-2分钟）
2. 检查定时任务：`/api/debug/jobs`
3. 等待到提醒时间
4. 查看日志确认是否执行
5. 如果未执行，手动发送测试：`/api/debug/reminder/{id}/send`
6. 根据错误信息处理

