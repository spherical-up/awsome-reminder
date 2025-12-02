# 解决 403 Forbidden 错误

## 错误信息

```
POST http://localhost:5000/api/reminder 403 (Forbidden)
```

## 原因

微信开发者工具对 `localhost` 域名有限制，会导致 403 错误。

## 解决方案

### 方案 1：使用 127.0.0.1（推荐）

已修改 `utils/api.js`，将 `localhost` 改为 `127.0.0.1`：

```javascript
const API_BASE_URL = 'http://127.0.0.1:5000/api'
```

### 方案 2：使用本地 IP 地址

如果 `127.0.0.1` 也不行，使用本地 IP：

1. **获取本地 IP：**
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. **修改 `utils/api.js`：**
   ```javascript
   const API_BASE_URL = 'http://192.168.31.100:5000/api'  // 替换为你的本地 IP
   ```

### 方案 3：关闭域名校验（必须）

在微信开发者工具中：

1. 点击右上角"详情"
2. 勾选"不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书"
3. 重新编译小程序

## 验证

修改后：

1. **重新编译小程序**（在微信开发者工具中点击"编译"）
2. **创建提醒**，查看是否还有 403 错误
3. **查看服务端日志**：
   ```bash
   docker logs reminder-server -f
   ```

应该看到：
```
INFO:收到创建提醒请求: {...}
INFO:✅ 创建提醒成功: ID=xxx
```

## 如果还是不行

### 检查服务是否运行

```bash
curl http://127.0.0.1:5000/api/health
```

应该返回：
```json
{"errcode":0,"errmsg":"success","status":"healthy"}
```

### 检查 CORS 配置

服务端已配置允许所有来源：
```python
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        ...
    }
})
```

### 检查防火墙

确保 5000 端口没有被防火墙阻止。

### 使用 curl 测试

```bash
curl -X POST http://127.0.0.1:5000/api/reminder \
  -H "Content-Type: application/json" \
  -d '{
    "openid": "test_123",
    "title": "测试",
    "time": "2024-12-02 23:55:00",
    "reminderTime": 1733156100000,
    "enableSubscribe": true
  }'
```

如果 curl 可以，说明服务端正常，问题在前端配置。

## 常见问题

### Q: 为什么不能用 localhost？

A: 微信开发者工具对 `localhost` 有安全限制，会返回 403。使用 `127.0.0.1` 或本地 IP 可以解决。

### Q: 127.0.0.1 也不行怎么办？

A: 
1. 使用本地 IP（如 `192.168.31.100`）
2. 确保关闭了域名校验
3. 检查服务是否绑定到 `0.0.0.0`（已配置）

### Q: 生产环境怎么办？

A: 生产环境使用 HTTPS 域名，不会有这个问题。只需要在 `utils/api.js` 中切换配置即可。

