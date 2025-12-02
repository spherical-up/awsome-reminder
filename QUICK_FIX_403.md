# 快速解决 403 Forbidden 错误

## 问题现象

```
POST http://localhost:5000/api/auth/login 403 (Forbidden)
```

## 解决方案（按顺序尝试）

### 方案1：关闭微信开发者工具的域名校验（必须）

1. **在微信开发者工具中：**
   - 点击右上角 **"详情"** 按钮
   - 选择 **"本地设置"** 标签
   - **勾选** **"不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书"**
   - 关闭详情窗口

2. **重新编译小程序：**
   - 点击工具栏的 **"编译"** 按钮
   - 或按 `Ctrl+S` (Windows) / `Cmd+S` (Mac)

3. **清除缓存（可选）：**
   - 点击 **"清缓存"** -> **"清除数据缓存"**

### 方案2：使用局域网IP代替 localhost

如果方案1不行，使用局域网IP：

1. **获取电脑IP地址：**
   ```bash
   # macOS
   ifconfig | grep "inet " | grep -v 127.0.0.1
   # 或
   ipconfig getifaddr en0
   
   # Windows
   ipconfig
   # 找到 IPv4 地址，例如：192.168.1.100
   ```

2. **修改 `utils/api.js`：**
   ```javascript
   // 改为局域网IP
   const API_BASE_URL = 'http://192.168.1.100:5000/api'  // 替换为你的IP
   ```

3. **确保服务端监听所有接口：**
   ```python
   # 如果直接运行 app.py，确保使用：
   app.run(host='0.0.0.0', port=5000)  # 不是 127.0.0.1
   ```

### 方案3：检查服务端是否正常运行

1. **测试服务端：**
   ```bash
   curl http://localhost:5000/api/health
   ```
   
   应该返回：
   ```json
   {"errcode": 0, "errmsg": "success", "status": "healthy"}
   ```

2. **如果服务端未启动：**
   ```bash
   cd server
   python app.py
   ```

3. **检查端口是否被占用：**
   ```bash
   # macOS/Linux
   lsof -i :5000
   
   # Windows
   netstat -ano | findstr :5000
   ```

### 方案4：检查防火墙

确保防火墙允许 5000 端口：

```bash
# macOS
# 系统设置 -> 安全性与隐私 -> 防火墙

# Linux
sudo ufw allow 5000
```

## 验证步骤

1. ✅ 已勾选"不校验合法域名"
2. ✅ 已重新编译小程序
3. ✅ 服务端已启动（`python app.py`）
4. ✅ 服务端健康检查通过（`curl http://localhost:5000/api/health`）
5. ✅ 在控制台重新执行测试代码

## 测试代码

在微信开发者工具的控制台执行：

```javascript
// 测试登录接口
wx.login({
  success: (res) => {
    if (res.code) {
      console.log('获取到 code:', res.code)
      wx.request({
        url: 'http://localhost:5000/api/auth/login',
        method: 'POST',
        data: {
          code: res.code
        },
        success: (result) => {
          console.log('✅ 登录成功:', result.data)
        },
        fail: (err) => {
          console.error('❌ 请求失败:', err)
        }
      })
    }
  }
})
```

## 如果仍然报错

1. **查看服务端日志：**
   ```bash
   # 查看是否有请求到达服务端
   # 如果服务端没有收到请求，说明是微信开发者工具的问题
   ```

2. **查看网络请求：**
   - 打开"调试器" -> "Network"
   - 查看请求的详细信息
   - 检查请求头、响应头

3. **尝试重启：**
   - 重启微信开发者工具
   - 重启服务端
   - 重启电脑（最后手段）

## 常见错误原因

| 错误 | 原因 | 解决 |
|------|------|------|
| 403 Forbidden | 域名校验未关闭 | 勾选"不校验合法域名" |
| request:fail | 服务端未启动 | 启动服务端 |
| 连接超时 | 防火墙阻止 | 检查防火墙设置 |
| 404 Not Found | 接口路径错误 | 检查 API_BASE_URL |

## 生产环境注意事项

⚠️ **重要：** 以上方法仅用于开发环境！

生产环境必须：
- 配置合法的服务器域名
- 使用 HTTPS
- 在微信公众平台配置服务器域名
- 不能关闭域名校验

