# 快速配置微信小程序消息推送 Token

## 一、生成 Token

### 方法 1：使用命令行（推荐）

```bash
# macOS/Linux
openssl rand -hex 16

# 或使用 Python
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 方法 2：手动设置

Token 要求：
- 长度：3-32 个字符
- 字符：只能包含字母、数字
- 示例：`my_token_123456`、`wx2024secret`

## 二、配置 Token

### 1. 在 `.env` 文件中添加

```env
WX_TOKEN=your_custom_token_123456
```

**注意**：将 `your_custom_token_123456` 替换为你生成的 Token。

### 2. 如果没有 `.env` 文件

创建 `.env` 文件：

```bash
cd server
cat > .env << EOF
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w
WX_TOKEN=your_custom_token_123456
EOF
```

## 三、在微信公众平台配置

### 1. 登录微信公众平台

访问 [微信公众平台](https://mp.weixin.qq.com/)

### 2. 进入服务器配置

1. **开发** -> **开发管理** -> **开发设置**
2. 找到 **消息推送** 部分
3. 点击 **配置**

### 3. 填写配置信息

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| **URL(服务器地址)** | 你的服务器地址 | `https://www.6ht6.com/api/wx/message` |
| **Token(令牌)** | 与 `.env` 中的 `WX_TOKEN` 一致 | `your_custom_token_123456` |
| **EncodingAESKey** | 消息加解密密钥（可选） | 点击"随机生成"或留空 |
| **消息加解密方式** | 选择加密方式 | 推荐"兼容模式" |

### 4. 提交验证

点击"提交"后，微信会向你的服务器发送验证请求。

**验证流程：**
1. 微信服务器发送 GET 请求到 `/api/wx/message`
2. 服务器验证签名
3. 返回 `echostr` 参数
4. 验证通过 ✅

## 四、验证服务器是否正常

### 1. 检查服务是否运行

```bash
# 检查服务健康
curl http://127.0.0.1:5000/api/health

# 应该返回：
# {"errcode":0,"errmsg":"success","status":"healthy"}
```

### 2. 查看服务日志

```bash
# 查看日志
docker logs reminder-server -f

# 验证请求时会看到：
# INFO:收到微信服务器验证请求: signature=xxx, timestamp=xxx, nonce=xxx
# INFO:✅ 微信服务器验证成功
```

## 五、接口说明

### 接口地址

```
GET/POST /api/wx/message
```

### GET 请求（验证服务器）

微信服务器会发送：
```
GET /api/wx/message?signature=xxx&timestamp=xxx&nonce=xxx&echostr=xxx
```

服务器会：
1. 验证签名
2. 返回 `echostr` 参数

### POST 请求（接收消息）

微信服务器会发送消息和事件到该接口。

## 六、常见问题

### Q1: 验证失败怎么办？

**检查清单：**
- ✅ Token 是否与微信公众平台配置一致
- ✅ URL 是否可访问（必须是 HTTPS，生产环境）
- ✅ 服务是否正常运行
- ✅ 查看服务日志是否有错误

### Q2: 必须使用 HTTPS 吗？

**开发环境：**
- 可以使用 HTTP
- 需要在微信开发者工具中关闭域名校验
- 可以使用内网穿透工具（如 ngrok）

**生产环境：**
- 必须使用 HTTPS
- 域名必须备案（国内服务器）

### Q3: Token 可以修改吗？

可以，但修改后需要：
1. 更新 `.env` 文件
2. 在微信公众平台重新配置
3. 重新验证服务器

### Q4: 如何测试消息接收？

1. 在微信公众平台配置服务器
2. 使用测试号或正式号发送消息
3. 查看服务日志确认是否收到

## 七、安全建议

1. **Token 要保密**：不要提交到代码仓库
2. **使用强 Token**：使用随机生成的字符串
3. **验证所有请求**：确保验证签名逻辑正确
4. **记录日志**：记录所有消息和事件
5. **错误处理**：实现完善的错误处理

## 八、下一步

配置完成后，你可以：
1. 接收用户消息
2. 处理各种事件（关注、取消关注等）
3. 实现自动回复功能
4. 处理其他业务逻辑

详细文档请查看 `WX_SERVER_CONFIG.md`

