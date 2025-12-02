# 微信小程序订阅消息服务端 - Python 实现

## 技术栈

- **Flask**: Web 框架
- **APScheduler**: 定时任务调度
- **Requests**: HTTP 请求库
- **SQLAlchemy**: 数据库 ORM（可选，当前使用内存存储）

## 快速开始

### 1. 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

创建 `.env` 文件并填写配置：

```env
WX_APPID=你的小程序AppID
WX_APPSECRET=你的小程序AppSecret
WX_TEMPLATE_ID=_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w
```

**注意**：如果未配置 `.env` 文件，代码中已设置默认模板ID为 `_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w`

### 3. 运行服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

## API 接口

### 1. 创建提醒

**POST** `/api/reminder`

请求体：
```json
{
    "openid": "用户openid",
    "title": "提醒内容",
    "time": "明天 10:00",
    "reminderTime": 1704067200000,
    "enableSubscribe": true
}
```

响应：
```json
{
    "errcode": 0,
    "errmsg": "success",
    "data": {
        "id": 1704067200000
    }
}
```

### 2. 获取提醒列表

**GET** `/api/reminders?openid=用户openid`

响应：
```json
{
    "errcode": 0,
    "errmsg": "success",
    "data": [
        {
            "id": 1704067200000,
            "openid": "用户openid",
            "title": "提醒内容",
            "time": "明天 10:00",
            "reminderTime": 1704067200000,
            "enableSubscribe": true,
            "createTime": "2024-01-01T10:00:00",
            "status": "pending"
        }
    ]
}
```

### 3. 删除提醒

**DELETE** `/api/reminder/<reminder_id>`

响应：
```json
{
    "errcode": 0,
    "errmsg": "success"
}
```

### 4. 健康检查

**GET** `/api/health`

## 小程序端调用示例

在 `pages/add/add.js` 的 `saveReminder` 方法中添加：

```javascript
// 如果开启了订阅且有提醒时间，调用服务端API
if (this.data.enableSubscribe && this.data.reminderTime) {
  // 获取用户 openid（需要先调用 wx.login）
  wx.login({
    success: (res) => {
      if (res.code) {
        // 调用服务端API创建提醒
        wx.request({
          url: 'https://your-server.com/api/reminder',
          method: 'POST',
          data: {
            openid: '用户openid', // 需要通过 code 换取 openid
            title: title,
            time: this.data.selectedTime,
            reminderTime: this.data.reminderTime,
            enableSubscribe: true
          },
          success: (res) => {
            if (res.data.errcode === 0) {
              console.log('提醒已保存到服务端')
            }
          }
        })
      }
    }
  })
}
```

## 生产环境部署

### 1. 使用 Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. 使用数据库（推荐）

当前使用内存存储，生产环境建议使用数据库：

```python
# 使用 SQLAlchemy 连接数据库
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(BigInteger, primary_key=True)
    openid = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    time = Column(String(100))
    reminder_time = Column(BigInteger, nullable=False)
    enable_subscribe = Column(Boolean, default=False)
    status = Column(String(20), default='pending')
    create_time = Column(DateTime, default=datetime.now)
```

### 3. 使用 Redis 缓存 access_token

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_access_token():
    # 从 Redis 获取 token
    token = redis_client.get('wx_access_token')
    if token:
        return token.decode('utf-8')
    
    # 获取新 token 并缓存
    # ...
```

## 注意事项

1. **access_token 管理**: access_token 有效期 2 小时，需要缓存并提前刷新
2. **定时任务持久化**: 当前使用内存存储，服务重启会丢失。生产环境应使用数据库
3. **错误处理**: 发送订阅消息失败时，应记录日志并重试
4. **安全性**: 生产环境需要验证请求来源，防止未授权访问
5. **日志**: 建议使用专业的日志系统（如 ELK）记录日志

## 扩展功能

- [ ] 使用数据库持久化存储
- [ ] 实现重试机制
- [ ] 添加用户认证
- [ ] 实现消息队列（RabbitMQ/Kafka）
- [ ] 添加监控和告警
- [ ] 实现分布式部署

