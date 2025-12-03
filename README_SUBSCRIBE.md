# 微信小程序订阅消息配置指南

## 一、订阅消息模板配置

### 1. 登录微信公众平台
1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 使用小程序账号登录

### 2. 申请订阅消息模板
1. 进入 **功能** -> **订阅消息**
2. 点击 **公共模板库** 或 **我的模板**
3. 选择合适的模板，例如：
   - 模板名称：提醒通知
   - 模板内容示例：
     ```
     提醒内容：{{thing1.DATA}}
     提醒时间：{{time2.DATA}}
     ```
4. 申请模板后，会获得 **模板ID**（tmplId）

### 3. 配置模板ID
在 `pages/add/add.js` 中，模板ID已配置为：

```javascript
const tmplIds = [
  'is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw'
]
```

**注意**：如果使用不同的模板ID，请修改此处的配置。

## 二、服务端实现（发送订阅消息）

订阅消息需要在服务端发送，小程序端只能请求用户授权。

### 1. Python 服务端实现

我们提供了完整的 Python Flask 实现，位于 `server/` 目录。

**快速开始：**

```bash
cd server
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件，填入你的 AppID、AppSecret 和模板ID
python app.py
```

**主要功能：**
- ✅ 获取和管理 access_token（自动刷新）
- ✅ 发送订阅消息
- ✅ 定时任务调度（使用 APScheduler）
- ✅ RESTful API 接口
- ✅ 错误处理和日志记录

详细文档请查看 `server/README.md`

### 2. 核心代码说明

**发送订阅消息：**

```python
def send_subscribe_message(openid, template_id, page, data):
    """发送订阅消息"""
    token = get_access_token()
    url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}'
    
    payload = {
        'touser': openid,
        'template_id': template_id,
        'page': page,
        'data': data
    }
    
    response = requests.post(url, json=payload)
    return response.json()
```

**定时任务实现：**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

scheduler = BackgroundScheduler()
scheduler.start()

def schedule_reminder(reminder):
    """安排提醒任务"""
    reminder_time = datetime.fromtimestamp(reminder['reminderTime'] / 1000)
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_time),
        id=f"reminder_{reminder['id']}"
    )
```

## 三、完整流程

1. **用户添加提醒**：在小程序中输入提醒内容和时间
2. **请求订阅授权**：调用 `wx.requestSubscribeMessage` 请求用户授权
3. **保存提醒到服务端**：将提醒信息（包括用户openid、提醒时间等）发送到服务端
4. **服务端创建定时任务**：服务端根据提醒时间创建定时任务
5. **定时发送消息**：到达提醒时间时，服务端调用微信API发送订阅消息

## 四、注意事项

1. **订阅消息有效期**：用户授权后，每个模板ID只能发送一次消息
2. **需要重新授权**：每次发送前都需要用户重新授权（可以通过按钮触发）
3. **服务端必需**：小程序无法直接发送订阅消息，必须通过服务端
4. **access_token**：服务端需要定期刷新access_token（有效期2小时）

## 五、测试

1. 在微信开发者工具中测试订阅消息授权
2. 真机调试测试完整的订阅流程
3. 检查服务端日志，确认消息发送状态

## 六、相关文档

- [微信小程序订阅消息文档](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/subscribe-message.html)
- [订阅消息API文档](https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/subscribe-message/subscribeMessage.send.html)

