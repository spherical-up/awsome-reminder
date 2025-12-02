"""
微信小程序订阅消息服务端 - Flask 实现
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import requests
import json
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import logging

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 配置 CORS，允许所有来源（开发环境）
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 微信小程序配置（从环境变量读取）
APPID = os.getenv('WX_APPID', 'your-appid')
APPSECRET = os.getenv('WX_APPSECRET', 'your-appsecret')
TEMPLATE_ID = os.getenv('WX_TEMPLATE_ID', '_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w')

# 存储 access_token
access_token = None
token_expires_at = None

# 存储提醒任务（实际项目中应使用数据库）
reminders_db = []

# 初始化调度器
scheduler = BackgroundScheduler()
scheduler.start()


def get_access_token():
    """
    获取微信 access_token
    有效期 2 小时，需要缓存
    """
    global access_token, token_expires_at
    
    # 如果 token 未过期，直接返回
    if access_token and token_expires_at and datetime.now() < token_expires_at:
        return access_token
    
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}'
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'access_token' in data:
            access_token = data['access_token']
            # 提前 5 分钟刷新 token
            expires_in = data.get('expires_in', 7200) - 300
            token_expires_at = datetime.now().timestamp() + expires_in
            
            logger.info('获取 access_token 成功')
            return access_token
        else:
            logger.error(f'获取 access_token 失败: {data}')
            return None
    except Exception as e:
        logger.error(f'获取 access_token 异常: {str(e)}')
        return None


def send_subscribe_message(openid, template_id, page, data):
    """
    发送订阅消息
    
    Args:
        openid: 用户 openid
        template_id: 模板ID
        page: 点击消息跳转的页面
        data: 模板数据
    
    Returns:
        dict: 发送结果
    """
    token = get_access_token()
    if not token:
        return {'errcode': -1, 'errmsg': '获取 access_token 失败'}
    
    url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}'
    
    payload = {
        'touser': openid,
        'template_id': template_id,
        'page': page,
        'data': data
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info(f'发送订阅消息成功: {openid}')
        else:
            logger.error(f'发送订阅消息失败: {result}')
        
        return result
    except Exception as e:
        logger.error(f'发送订阅消息异常: {str(e)}')
        return {'errcode': -1, 'errmsg': str(e)}


def schedule_reminder(reminder):
    """
    安排提醒任务
    
    Args:
        reminder: 提醒信息字典
    """
    reminder_time = datetime.fromtimestamp(reminder['reminderTime'] / 1000)
    
    # 如果提醒时间已过，不安排任务
    if reminder_time <= datetime.now():
        logger.warning(f'提醒时间已过: {reminder_time}')
        return
    
    def send_reminder():
        """发送提醒的函数"""
        try:
            # 构建模板数据
            template_data = {
                'thing1': {'value': reminder['title'][:20]},  # 提醒内容，最多20字
                'time2': {'value': reminder['time']}  # 提醒时间
            }
            
            # 发送订阅消息
            result = send_subscribe_message(
                openid=reminder['openid'],
                template_id=TEMPLATE_ID,
                page='pages/index/index',
                data=template_data
            )
            
            if result.get('errcode') == 0:
                logger.info(f'提醒发送成功: {reminder["id"]}')
            else:
                logger.error(f'提醒发送失败: {result}')
        except Exception as e:
            logger.error(f'发送提醒异常: {str(e)}')
    
    # 添加定时任务
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_time),
        id=f"reminder_{reminder['id']}",
        replace_existing=True
    )
    
    logger.info(f'已安排提醒任务: {reminder["id"]}, 时间: {reminder_time}')


@app.route('/api/reminder', methods=['POST'])
def create_reminder():
    """
    创建提醒接口
    
    请求体:
    {
        "openid": "用户openid",
        "title": "提醒内容",
        "time": "提醒时间显示",
        "reminderTime": 时间戳(毫秒),
        "enableSubscribe": true/false
    }
    """
    try:
        data = request.json
        
        # 验证必要字段
        required_fields = ['openid', 'title', 'reminderTime']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'errcode': 400,
                    'errmsg': f'缺少必要字段: {field}'
                }), 400
        
        # 创建提醒记录
        reminder = {
            'id': int(datetime.now().timestamp() * 1000),
            'openid': data['openid'],
            'title': data['title'],
            'time': data.get('time', ''),
            'reminderTime': data['reminderTime'],
            'enableSubscribe': data.get('enableSubscribe', False),
            'createTime': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # 保存到数据库（这里简化处理，实际应使用数据库）
        reminders_db.append(reminder)
        
        # 如果开启了订阅，安排定时任务
        if reminder['enableSubscribe'] and reminder['reminderTime']:
            schedule_reminder(reminder)
        
        logger.info(f'创建提醒成功: {reminder["id"]}')
        
        return jsonify({
            'errcode': 0,
            'errmsg': 'success',
            'data': {
                'id': reminder['id']
            }
        })
        
    except Exception as e:
        logger.error(f'创建提醒异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminder/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    """
    删除提醒接口
    """
    try:
        # 查找并删除提醒
        global reminders_db
        reminders_db = [r for r in reminders_db if r['id'] != reminder_id]
        
        # 取消定时任务
        try:
            scheduler.remove_job(f"reminder_{reminder_id}")
        except:
            pass
        
        logger.info(f'删除提醒成功: {reminder_id}')
        
        return jsonify({
            'errcode': 0,
            'errmsg': 'success'
        })
        
    except Exception as e:
        logger.error(f'删除提醒异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """
    获取用户的提醒列表
    """
    try:
        openid = request.args.get('openid')
        if not openid:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少 openid 参数'
            }), 400
        
        # 筛选用户的提醒
        user_reminders = [r for r in reminders_db if r['openid'] == openid]
        
        return jsonify({
            'errcode': 0,
            'errmsg': 'success',
            'data': user_reminders
        })
        
    except Exception as e:
        logger.error(f'获取提醒列表异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    通过 code 换取 openid
    
    请求体:
    {
        "code": "微信登录code"
    }
    """
    try:
        data = request.json
        code = data.get('code')
        
        if not code:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少 code 参数'
            }), 400
        
        # 调用微信接口换取 openid
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': APPID,
            'secret': APPSECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'openid' in result:
            logger.info(f'用户登录成功: {result["openid"]}')
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': {
                    'openid': result['openid'],
                    'session_key': result.get('session_key')
                }
            })
        else:
            logger.error(f'换取 openid 失败: {result}')
            return jsonify({
                'errcode': result.get('errcode', -1),
                'errmsg': result.get('errmsg', '换取 openid 失败')
            }), 400
            
    except Exception as e:
        logger.error(f'登录异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'errcode': 0,
        'errmsg': 'success',
        'status': 'healthy'
    })


if __name__ == '__main__':
    logger.info('启动 Flask 服务...')
    logger.info(f'APPID: {APPID}')
    logger.info(f'模板ID: {TEMPLATE_ID}')
    
    # 开发环境运行
    app.run(host='0.0.0.0', port=5000, debug=True)

