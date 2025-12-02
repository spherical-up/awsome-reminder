# 排查 jobs 为空的问题

## 问题现象

`/api/debug/jobs` 返回空数组，说明没有定时任务。

## 可能的原因

### 1. 前端未成功调用 API

**检查方法：**

在小程序开发者工具中：
1. 打开"调试器" -> "Network"（网络）
2. 创建提醒时，查看是否有请求发送到 `/api/reminder`
3. 查看请求的 URL、请求体、响应

**常见问题：**
- API 地址配置错误（生产环境 vs 开发环境）
- 网络请求被拦截
- CORS 问题

### 2. API 地址配置错误

**检查 `utils/api.js`：**

```javascript
// 开发环境应该使用：
const API_BASE_URL = 'http://127.0.0.1:5000/api'
// 或
const API_BASE_URL = 'http://localhost:5000/api'

// 生产环境使用：
const API_BASE_URL = 'https://www.6ht6.com/api'
```

**如果使用本地测试：**
- 确保使用 `http://127.0.0.1:5000/api` 或 `http://localhost:5000/api`
- 在微信开发者工具中，可能需要使用本地 IP 地址（如 `http://192.168.x.x:5000/api`）

### 3. 创建提醒时未开启订阅

**检查：**
- 创建提醒时是否开启了"订阅提醒"开关
- 是否选择了提醒时间

**代码逻辑：**
```javascript
// 只有同时满足以下条件才会创建定时任务：
if (reminder['enableSubscribe'] && reminder['reminderTime']) {
    schedule_reminder(reminder)
}
```

### 4. 提醒时间已过

**检查：**
- 如果创建提醒时，选择的提醒时间已经过了，任务不会创建
- 查看服务端日志中的"提醒时间已过"提示

## 排查步骤

### 步骤 1：检查前端是否调用 API

在小程序开发者工具中：
1. 打开"调试器" -> "Console"（控制台）
2. 创建提醒
3. 查看是否有错误信息
4. 查看是否有"提醒已保存到服务端"的日志

### 步骤 2：检查服务端是否收到请求

```bash
# 实时查看服务端日志
docker logs reminder-server -f

# 创建提醒时，应该看到：
# INFO:收到创建提醒请求: {...}
# INFO:✅ 创建提醒成功: ID=xxx
```

如果没有看到这些日志，说明请求没有到达服务端。

### 步骤 3：检查 API 地址配置

**修改 `utils/api.js`：**

```javascript
// 开发环境（本地测试）
const API_BASE_URL = 'http://127.0.0.1:5000/api'

// 如果需要使用本地 IP（微信开发者工具可能需要）
// 先获取本机 IP：ifconfig | grep "inet " | grep -v 127.0.0.1
// const API_BASE_URL = 'http://192.168.x.x:5000/api'
```

### 步骤 4：手动测试 API

```bash
# 测试创建提醒接口
curl -X POST http://127.0.0.1:5000/api/reminder \
  -H "Content-Type: application/json" \
  -d '{
    "openid": "test_openid_123",
    "title": "测试提醒",
    "time": "2024-12-02 23:55:00",
    "reminderTime": 1733156100000,
    "enableSubscribe": true
  }'

# 然后检查定时任务
curl http://127.0.0.1:5000/api/debug/jobs
```

**注意：** `reminderTime` 是毫秒时间戳，需要是未来的时间。

### 步骤 5：检查小程序网络配置

在微信开发者工具中：
1. 点击右上角"详情"
2. 勾选"不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书"
3. 重新测试

## 快速诊断命令

```bash
# 1. 检查服务健康
curl http://127.0.0.1:5000/api/health

# 2. 查看服务端日志
docker logs reminder-server --tail 50

# 3. 手动测试创建提醒
curl -X POST http://127.0.0.1:5000/api/reminder \
  -H "Content-Type: application/json" \
  -d '{
    "openid": "test_123",
    "title": "测试",
    "time": "2024-12-02 23:55:00",
    "reminderTime": 1733156100000,
    "enableSubscribe": true
  }'

# 4. 检查定时任务
curl http://127.0.0.1:5000/api/debug/jobs

# 5. 检查提醒记录
curl http://127.0.0.1:5000/api/debug/reminders
```

## 常见错误

### 错误 1：网络请求失败

**现象：** 小程序控制台显示网络错误

**解决：**
- 检查 API 地址是否正确
- 检查服务是否运行：`curl http://127.0.0.1:5000/api/health`
- 在微信开发者工具中关闭域名校验

### 错误 2：缺少 openid

**现象：** 服务端返回"缺少必要字段: openid"

**解决：**
- 检查 `getUserOpenid()` 是否成功
- 检查 `/api/auth/login` 接口是否正常
- 查看小程序控制台的错误信息

### 错误 3：提醒时间已过

**现象：** 服务端日志显示"提醒时间已过"

**解决：**
- 选择未来的时间
- 检查时区设置

## 下一步

1. **在小程序中创建提醒**，同时：
   - 打开小程序开发者工具的"调试器" -> "Console"
   - 打开"调试器" -> "Network"
   - 查看是否有请求和错误

2. **查看服务端日志**：
   ```bash
   docker logs reminder-server -f
   ```

3. **如果还是没有请求**，检查 API 地址配置，确保使用本地地址

