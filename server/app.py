"""
微信小程序订阅消息服务端 - Flask 实现
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import requests
import json
import os
import hashlib
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import logging
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import pymysql

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 配置 CORS，允许所有来源（开发环境）
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
}, supports_credentials=True)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 微信小程序配置（从环境变量读取）
APPID = os.getenv('WX_APPID', 'your-appid')
APPSECRET = os.getenv('WX_APPSECRET', 'your-appsecret')
TEMPLATE_ID = os.getenv('WX_TEMPLATE_ID', 'is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw')
# 消息推送 Token（用于验证消息来源）
WX_TOKEN = os.getenv('WX_TOKEN', 'your_custom_token_123456')

# 存储 access_token
access_token = None
token_expires_at = None

# 数据库配置
# 自动检测运行环境：如果在 Docker 容器中，使用 host.docker.internal；否则使用 localhost
def get_db_host():
    """自动检测数据库主机地址"""
    # 如果环境变量中已指定，直接使用（优先级最高）
    env_host = os.getenv('DB_HOST')
    if env_host:
        return env_host
    
    # 检测是否在 Docker 容器中运行
    is_docker = False
    
    # 方法1: 检查 /.dockerenv 文件（Docker 容器中通常存在）
    if os.path.exists('/.dockerenv'):
        is_docker = True
    
    # 方法2: 检查环境变量（Docker Compose 会设置）
    if os.getenv('DOCKER_CONTAINER') == 'true':
        is_docker = True
    
    # 方法3: 检查 cgroup（Linux 容器）
    try:
        with open('/proc/self/cgroup', 'r') as f:
            if 'docker' in f.read():
                is_docker = True
    except:
        pass
    
    if is_docker:
        # 在 Docker 容器中，优先尝试 host.docker.internal
        # 如果系统不支持（如某些 Linux 服务器），可以手动在 .env 中设置 DB_HOST=172.17.0.1
        return 'host.docker.internal'
    
    # 本地开发环境
    return 'localhost'

DB_HOST = get_db_host()
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'reminder_db')

# 自动创建数据库（如果不存在）
def ensure_database_exists():
    """确保数据库存在，如果不存在则创建"""
    try:
        # 连接到 MySQL 服务器（不指定数据库）
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        
        try:
            with connection.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
                result = cursor.fetchone()
                
                if not result:
                    # 数据库不存在，创建它
                    cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    connection.commit()
                    logger.info(f'✅ 数据库 {DB_NAME} 创建成功')
                else:
                    logger.info(f'✅ 数据库 {DB_NAME} 已存在')
        finally:
            connection.close()
    except Exception as e:
        logger.warning(f'检查/创建数据库时出错: {str(e)}，将尝试直接连接数据库')
        # 如果无法创建数据库（可能是权限问题），继续尝试连接

# 确保数据库存在
ensure_database_exists()

# 构建数据库连接字符串
DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

# 创建数据库引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, echo=False)
Base = declarative_base()
SessionLocal = scoped_session(sessionmaker(bind=engine))

# 数据库模型
class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(String(200), primary_key=True)  # 使用 openid + reminder_time 组合作为 ID
    openid = Column(String(100), nullable=False, index=True)  # 当前拥有者openid（可能是被分配的）
    owner_openid = Column(String(100), nullable=False, index=True)  # 提醒创建者openid
    title = Column(String(500), nullable=False)  # 兼容字段
    thing1 = Column(String(500), nullable=False)  # 事项主题
    thing4 = Column(Text)  # 事项描述
    time = Column(String(100))  # 事项时间显示
    reminder_time = Column(BigInteger, nullable=False)  # 提醒时间戳（毫秒）
    completed = Column(Boolean, default=False)  # 是否完成
    enable_subscribe = Column(Boolean, default=False)  # 是否开启订阅
    status = Column(String(20), default='pending')  # 状态：pending, sent, cancelled
    shared = Column(Boolean, default=False)  # 是否已分享
    create_time = Column(DateTime, default=datetime.now)  # 创建时间
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'openid': self.openid,
            'ownerOpenid': self.owner_openid,
            'title': self.title,
            'thing1': self.thing1,
            'thing4': self.thing4,
            'time': self.time,
            'reminderTime': self.reminder_time,
            'completed': self.completed,
            'enableSubscribe': self.enable_subscribe,
            'status': self.status,
            'shared': self.shared,
            'createTime': self.create_time.isoformat() if self.create_time else None
        }

# 提醒分配关系表
class ReminderAssignment(Base):
    __tablename__ = 'reminder_assignments'
    
    id = Column(String(200), primary_key=True)  # reminder_id_assigned_openid
    reminder_id = Column(String(200), nullable=False, index=True)  # 原提醒ID
    owner_openid = Column(String(100), nullable=False, index=True)  # 提醒创建者openid
    assigned_openid = Column(String(100), nullable=False, index=True)  # 被分配的好友openid
    status = Column(String(20), default='pending')  # 状态：pending, accepted, rejected
    create_time = Column(DateTime, default=datetime.now)  # 创建时间
    accept_time = Column(DateTime)  # 接受时间
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'reminderId': self.reminder_id,
            'ownerOpenid': self.owner_openid,
            'assignedOpenid': self.assigned_openid,
            'status': self.status,
            'createTime': self.create_time.isoformat() if self.create_time else None,
            'acceptTime': self.accept_time.isoformat() if self.accept_time else None
        }

# 创建表（如果不存在）
def ensure_tables_exist():
    """确保数据库表存在，如果不存在则创建"""
    try:
        Base.metadata.create_all(engine)
        logger.info('✅ 数据库表创建/检查成功')
    except Exception as e:
        logger.error(f'❌ 数据库表创建失败: {str(e)}')
        logger.error('请检查数据库配置和连接')
        raise

ensure_tables_exist()

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
        logger.info(f'准备发送订阅消息: openid={openid}, template_id={template_id}')
        logger.info(f'请求数据: {payload}')
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        logger.info(f'微信API响应: {result}')
        
        if result.get('errcode') == 0:
            logger.info(f'✅ 发送订阅消息成功: openid={openid}')
        else:
            error_code = result.get('errcode')
            error_msg = result.get('errmsg', '未知错误')
            logger.error(f'❌ 发送订阅消息失败: openid={openid}, errcode={error_code}, errmsg={error_msg}')
            
            # 常见错误码说明
            error_codes = {
                40001: 'access_token 无效，需要重新获取',
                40003: 'openid 无效',
                43101: '用户拒绝接受消息（需要重新授权）',
                47003: '模板参数不正确',
                41030: 'page 路径不正确',
                40037: '模板ID无效'
            }
            if error_code in error_codes:
                logger.error(f'错误说明: {error_codes[error_code]}')
        
        return result
    except Exception as e:
        logger.error(f'发送订阅消息异常: {str(e)}', exc_info=True)
        return {'errcode': -1, 'errmsg': str(e)}


def schedule_reminder(reminder):
    """
    安排提醒任务
    
    Args:
        reminder: 提醒信息字典
    """
    try:
        reminder_time = datetime.fromtimestamp(reminder['reminderTime'] / 1000)
        now = datetime.now()
        
        logger.info(f'安排提醒任务: ID={reminder["id"]}, 提醒时间={reminder_time}, 当前时间={now}')
        
        # 如果提醒时间已过，不安排任务
        if reminder_time <= now:
            logger.warning(f'提醒时间已过: {reminder_time}, 当前时间: {now}, 时间差: {(now - reminder_time).total_seconds()}秒')
            # 如果时间已过但不超过1分钟，仍然安排（可能是时间同步问题）
            if (now - reminder_time).total_seconds() > 60:
                return
            else:
                logger.info(f'提醒时间已过但不超过1分钟，仍然安排任务')
        
        def send_reminder():
            """发送提醒的函数"""
            try:
                logger.info(f'开始发送提醒: ID={reminder["id"]}, openid={reminder["openid"]}')
                
                # 构建模板数据
                # 模板字段：事项主题(thing1)、事项时间(time2)、事项描述(thing4)
                reminder_time = reminder.get('time', '')
                thing1 = reminder.get('thing1', reminder.get('title', ''))[:20]  # 事项主题，优先使用 thing1，否则使用 title
                thing4 = reminder.get('thing4', reminder.get('title', ''))[:20]  # 事项描述，优先使用 thing4，否则使用 title
                template_data = {
                    'thing1': {'value': thing1},  # 事项主题
                    'time2': {'value': reminder_time},  # 事项时间
                    'thing4': {'value': thing4}  # 事项描述
                }
                
                logger.info(f'模板数据: {template_data}')
                
                # 发送订阅消息
                result = send_subscribe_message(
                    openid=reminder['openid'],
                    template_id=TEMPLATE_ID,
                    page='pages/index/index',
                    data=template_data
                )
                
                logger.info(f'订阅消息发送结果: {result}')
                
                if result.get('errcode') == 0:
                    logger.info(f'✅ 提醒发送成功: ID={reminder["id"]}, openid={reminder["openid"]}')
                    # 更新提醒状态到数据库
                    db = SessionLocal()
                    try:
                        reminder_obj = db.query(Reminder).filter(Reminder.id == reminder['id']).first()
                        if reminder_obj:
                            reminder_obj.status = 'sent'
                            db.commit()
                    except Exception as e:
                        db.rollback()
                        logger.error(f'更新提醒状态失败: {str(e)}')
                    finally:
                        db.close()
                else:
                    error_code = result.get('errcode')
                    error_msg = result.get('errmsg', '未知错误')
                    logger.error(f'❌ 提醒发送失败: ID={reminder["id"]}, errcode={error_code}, errmsg={error_msg}')
                    # 更新提醒状态到数据库
                    db = SessionLocal()
                    try:
                        reminder_obj = db.query(Reminder).filter(Reminder.id == reminder['id']).first()
                        if reminder_obj:
                            reminder_obj.status = 'failed'
                            db.commit()
                    except Exception as e:
                        db.rollback()
                        logger.error(f'更新提醒状态失败: {str(e)}')
                    finally:
                        db.close()
            except Exception as e:
                logger.error(f'发送提醒异常: ID={reminder["id"]}, 错误: {str(e)}', exc_info=True)
        
        # 添加定时任务
        job_id = f"reminder_{reminder['id']}"
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            id=job_id,
            replace_existing=True
        )
        
        # 验证任务是否添加成功
        job = scheduler.get_job(job_id)
        if job:
            logger.info(f'✅ 已安排提醒任务: ID={reminder["id"]}, 任务ID={job_id}, 执行时间={reminder_time}, 当前时间={now}')
        else:
            logger.error(f'❌ 任务添加失败: ID={reminder["id"]}, 任务ID={job_id}')
            
    except Exception as e:
        logger.error(f'安排提醒任务异常: {str(e)}', exc_info=True)


@app.route('/api/reminder', methods=['POST'])
def create_reminder():
    """
    创建提醒接口
    
    请求体:
    {
        "openid": "用户openid",
        "title": "提醒内容（兼容字段）",
        "thing1": "事项主题（必填）",
        "thing4": "事项描述（必填）",
        "time": "事项时间显示（必填）",
        "reminderTime": 时间戳(毫秒)（必填）,
        "enableSubscribe": true/false
    }
    """
    try:
        data = request.json
        logger.info(f'收到创建提醒请求: {data}')
        
        # 验证必要字段
        required_fields = ['openid', 'reminderTime']
        for field in required_fields:
            if field not in data:
                logger.warning(f'缺少必要字段: {field}, 请求数据: {data}')
                return jsonify({
                    'errcode': 400,
                    'errmsg': f'缺少必要字段: {field}'
                }), 400
        
        # 验证事项相关字段（thing1, thing4, time 至少有一个）
        thing1 = data.get('thing1', data.get('title', ''))
        thing4 = data.get('thing4', '')
        time_str = data.get('time', '')
        
        if not thing1 or not thing4 or not time_str:
            logger.warning(f'缺少事项字段: thing1={thing1}, thing4={thing4}, time={time_str}, 请求数据: {data}')
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少必要字段: thing1（事项主题）、thing4（事项描述）、time（事项时间）均为必填'
            }), 400
        
        # 创建提醒记录
        # 使用 openid + reminder_time 组合作为唯一 ID
        reminder_id = f"{data['openid']}_{data['reminderTime']}"
        owner_openid = data['openid']  # 创建者就是当前用户
        db = SessionLocal()
        try:
            reminder = Reminder(
                id=reminder_id,
                openid=data['openid'],  # 当前拥有者
                owner_openid=owner_openid,  # 创建者
                title=thing1,  # 兼容字段，使用 thing1
                thing1=thing1,  # 事项主题
                thing4=thing4,  # 事项描述
                time=time_str,  # 事项时间
                reminder_time=data['reminderTime'],
                enable_subscribe=data.get('enableSubscribe', False),
                status='pending',
                completed=False,
                shared=False
            )
            db.add(reminder)
            db.commit()
            
            # 转换为字典用于后续处理
            reminder_dict = reminder.to_dict()
        except Exception as e:
            db.rollback()
            logger.error(f'保存提醒到数据库失败: {str(e)}')
            return jsonify({
                'errcode': 500,
                'errmsg': f'保存提醒失败: {str(e)}'
            }), 500
        finally:
            db.close()
        
        reminder = reminder_dict
        
        # 如果开启了订阅，安排定时任务
        if reminder['enableSubscribe'] and reminder['reminderTime']:
            logger.info(f'提醒开启了订阅，开始安排定时任务: ID={reminder["id"]}')
            schedule_reminder(reminder)
            # 开启订阅时，status 保持 pending，等待定时任务执行后更新
        else:
            # 未开启订阅时，根据提醒时间判断状态
            db = SessionLocal()
            try:
                reminder_obj = db.query(Reminder).filter(Reminder.id == reminder['id']).first()
                if reminder_obj:
                    reminder_time = datetime.fromtimestamp(reminder['reminderTime'] / 1000)
                    now = datetime.now()
                    if reminder_time <= now:
                        # 时间已过，设置为 expired
                        reminder_obj.status = 'expired'
                    else:
                        # 时间未到，设置为 no_subscribe（未开启订阅但时间未到）
                        reminder_obj.status = 'no_subscribe'
                    db.commit()
                    reminder_dict['status'] = reminder_obj.status
            except Exception as e:
                db.rollback()
                logger.error(f'更新提醒状态失败: {str(e)}')
            finally:
                db.close()
            
            logger.info(f'提醒未开启订阅或没有提醒时间: enableSubscribe={reminder.get("enableSubscribe")}, reminderTime={reminder.get("reminderTime")}, status={reminder_dict.get("status")}')
        
        logger.info(f'✅ 创建提醒成功: ID={reminder["id"]}, 标题={reminder["title"]}, 提醒时间={reminder.get("time")}')
        
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


@app.route('/api/reminder/<string:reminder_id>', methods=['GET', 'DELETE', 'PUT'])
def reminder_detail(reminder_id):
    """
    获取、更新或删除提醒接口
    """
    if request.method == 'GET':
        """获取提醒详情"""
        try:
            db = SessionLocal()
            try:
                # 查找提醒
                reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
                if not reminder:
                    return jsonify({
                        'errcode': 404,
                        'errmsg': '提醒不存在'
                    }), 404
                
                return jsonify({
                    'errcode': 0,
                    'errmsg': 'success',
                    'data': reminder.to_dict()
                })
            finally:
                db.close()
        except Exception as e:
            logger.error(f'获取提醒详情异常: {str(e)}')
            return jsonify({
                'errcode': 500,
                'errmsg': str(e)
            }), 500
    
    elif request.method == 'PUT':
        """更新提醒"""
        try:
            data = request.json
            logger.info(f'收到更新提醒请求: ID={reminder_id}, data={data}')
            
            db = SessionLocal()
            try:
                # 查找提醒
                reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
                if not reminder:
                    return jsonify({
                        'errcode': 404,
                        'errmsg': '提醒不存在'
                    }), 404
                
                # 更新字段
                if 'thing1' in data:
                    reminder.thing1 = data['thing1']
                    reminder.title = data['thing1']  # 同时更新兼容字段
                if 'thing4' in data:
                    reminder.thing4 = data['thing4']
                if 'time' in data:
                    reminder.time = data['time']
                if 'reminderTime' in data:
                    reminder.reminder_time = data['reminderTime']
                
                # 处理订阅状态变化
                enable_subscribe_changed = False
                if 'enableSubscribe' in data:
                    old_enable_subscribe = reminder.enable_subscribe
                    reminder.enable_subscribe = data['enableSubscribe']
                    enable_subscribe_changed = (old_enable_subscribe != data['enableSubscribe'])
                
                # 更新 status 逻辑
                if reminder.enable_subscribe and reminder.reminder_time:
                    # 如果开启了订阅，需要重新安排定时任务
                    # 先取消旧任务
                    try:
                        scheduler.remove_job(f"reminder_{reminder_id}")
                    except:
                        pass
                    
                    # 重新安排任务
                    reminder_dict = reminder.to_dict()
                    schedule_reminder(reminder_dict)
                    reminder.status = 'pending'  # 重置为 pending，等待发送
                else:
                    # 未开启订阅，根据时间判断状态
                    reminder_time = datetime.fromtimestamp(reminder.reminder_time / 1000)
                    now = datetime.now()
                    if reminder_time <= now:
                        reminder.status = 'expired'
                    else:
                        reminder.status = 'no_subscribe'
                
                db.commit()
                
                logger.info(f'更新提醒成功: ID={reminder_id}')
                
                return jsonify({
                    'errcode': 0,
                    'errmsg': 'success',
                    'data': reminder.to_dict()
                })
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
        except Exception as e:
            logger.error(f'更新提醒异常: {str(e)}')
            return jsonify({
                'errcode': 500,
                'errmsg': str(e)
            }), 500
    
    elif request.method == 'DELETE':
        """删除提醒"""
        return delete_reminder(reminder_id)


def delete_reminder(reminder_id):
    """
    删除提醒接口
    """
    try:
        db = SessionLocal()
        try:
            # 查找提醒
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                return jsonify({
                    'errcode': 404,
                    'errmsg': '提醒不存在'
                }), 404
            
            # 删除提醒
            db.delete(reminder)
            db.commit()
            
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
            db.rollback()
            raise e
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f'删除提醒异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminders', methods=['GET', 'OPTIONS'])
def get_reminders():
    """
    获取用户的提醒列表（包括自己创建的和被分配的）
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'errcode': 0})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    try:
        logger.info(f'收到获取提醒列表请求: {request.args}')
        openid = request.args.get('openid')
        if not openid:
            logger.warning('缺少 openid 参数')
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少 openid 参数'
            }), 400
        
        db = SessionLocal()
        try:
            # 查询用户拥有的提醒列表（openid匹配，包括自己创建的和被分配的）
            reminders = db.query(Reminder).filter(
                Reminder.openid == openid
            ).order_by(Reminder.create_time.desc()).all()
            
            # 转换为字典列表
            user_reminders = []
            for r in reminders:
                reminder_dict = r.to_dict()
                # 标记来自分享的提醒
                if r.owner_openid != r.openid:
                    reminder_dict['fromOwner'] = True
                user_reminders.append(reminder_dict)
            
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': user_reminders
            })
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f'获取提醒列表异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminder/<string:reminder_id>/complete', methods=['PUT'])
def update_reminder_complete(reminder_id):
    """
    更新提醒完成状态接口
    
    请求体:
    {
        "completed": true/false
    }
    """
    try:
        data = request.json
        completed = data.get('completed', False)
        
        db = SessionLocal()
        try:
            # 查找提醒
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                return jsonify({
                    'errcode': 404,
                    'errmsg': '提醒不存在'
                }), 404
            
            # 更新完成状态
            reminder.completed = completed
            db.commit()
            
            logger.info(f'更新提醒完成状态成功: ID={reminder_id}, completed={completed}')
            
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': reminder.to_dict()
            })
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f'更新提醒完成状态异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    """
    通过 code 换取 openid
    
    请求体:
    {
        "code": "微信登录code"
    }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'errcode': 0})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    try:
        logger.info(f'收到登录请求: {request.json}')
        data = request.json
        if not data:
            logger.warning('请求体为空')
            return jsonify({
                'errcode': 400,
                'errmsg': '请求体不能为空'
            }), 400
        
        code = data.get('code')
        
        if not code:
            logger.warning('缺少 code 参数')
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少 code 参数'
            }), 400
        
        # 验证 APPID 和 APPSECRET 是否配置
        if not APPID or APPID == 'your-appid':
            logger.error('APPID 未配置')
            return jsonify({
                'errcode': 500,
                'errmsg': '服务器配置错误：APPID 未配置'
            }), 500
        
        if not APPSECRET or APPSECRET == 'your-appsecret':
            logger.error('APPSECRET 未配置')
            return jsonify({
                'errcode': 500,
                'errmsg': '服务器配置错误：APPSECRET 未配置'
            }), 500
        
        # 调用微信接口换取 openid
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': APPID,
            'secret': APPSECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        logger.info(f'调用微信接口换取 openid: appid={APPID}, code={code[:10]}...')
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # 检查 HTTP 状态码
            result = response.json()
        except requests.exceptions.Timeout:
            logger.error('调用微信接口超时')
            return jsonify({
                'errcode': 500,
                'errmsg': '请求微信接口超时，请稍后重试'
            }), 500
        except requests.exceptions.RequestException as e:
            logger.error(f'调用微信接口失败: {str(e)}')
            return jsonify({
                'errcode': 500,
                'errmsg': f'请求微信接口失败: {str(e)}'
            }), 500
        
        logger.info(f'微信接口响应: {result}')
        
        if 'openid' in result:
            logger.info(f'用户登录成功: openid={result["openid"]}')
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': {
                    'openid': result['openid'],
                    'session_key': result.get('session_key')
                }
            })
        else:
            error_code = result.get('errcode', -1)
            error_msg = result.get('errmsg', '换取 openid 失败')
            logger.error(f'换取 openid 失败: errcode={error_code}, errmsg={error_msg}')
            return jsonify({
                'errcode': error_code,
                'errmsg': error_msg
            }), 400
            
    except Exception as e:
        logger.error(f'登录异常: {str(e)}', exc_info=True)
        return jsonify({
            'errcode': 500,
            'errmsg': f'服务器内部错误: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'errcode': 0,
        'errmsg': 'success',
        'status': 'healthy'
    })


@app.route('/api/debug/jobs', methods=['GET'])
def get_scheduled_jobs():
    """
    查看所有定时任务（调试用）
    """
    try:
        jobs = scheduler.get_jobs()
        job_list = []
        for job in jobs:
            job_list.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jsonify({
            'errcode': 0,
            'errmsg': 'success',
            'data': {
                'total': len(job_list),
                'jobs': job_list,
                'scheduler_running': scheduler.running
            }
        })
    except Exception as e:
        logger.error(f'获取定时任务列表异常: {str(e)}', exc_info=True)
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/debug/reminder/<string:reminder_id>/send', methods=['POST'])
def manual_send_reminder(reminder_id):
    """
    手动发送提醒（用于测试和调试）
    """
    try:
        db = SessionLocal()
        try:
            # 查找提醒
            reminder_obj = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            
            if not reminder_obj:
                return jsonify({
                    'errcode': 404,
                    'errmsg': '提醒不存在'
                }), 404
            
            if not reminder_obj.enable_subscribe:
                return jsonify({
                    'errcode': 400,
                    'errmsg': '该提醒未开启订阅'
                }), 400
            
            reminder = reminder_obj.to_dict()
            logger.info(f'手动发送提醒: ID={reminder_id}')
            
            # 构建模板数据
            # 模板字段：事项主题(thing1)、事项时间(time2)、事项描述(thing4)
            reminder_time = reminder.get('time', '')
            thing1 = reminder.get('thing1', reminder.get('title', ''))[:20]  # 事项主题，优先使用 thing1，否则使用 title
            thing4 = reminder.get('thing4', reminder.get('title', ''))[:20]  # 事项描述，优先使用 thing4，否则使用 title
            template_data = {
                'thing1': {'value': thing1},  # 事项主题
                'time2': {'value': reminder_time},  # 事项时间
                'thing4': {'value': thing4}  # 事项描述
            }
            
            logger.info(f'模板数据: {template_data}')
            
            # 发送订阅消息
            result = send_subscribe_message(
                openid=reminder['openid'],
                template_id=TEMPLATE_ID,
                page='pages/index/index',
                data=template_data
            )
            
            if result.get('errcode') == 0:
                # 更新状态
                reminder_obj.status = 'sent'
                db.commit()
                return jsonify({
                    'errcode': 0,
                    'errmsg': 'success',
                    'data': {
                        'result': result,
                        'message': '提醒发送成功'
                    }
                })
            else:
                reminder_obj.status = 'failed'
                db.commit()
                return jsonify({
                    'errcode': result.get('errcode', -1),
                    'errmsg': result.get('errmsg', '发送失败'),
                    'data': {
                        'result': result
                    }
                }), 400
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f'手动发送提醒异常: {str(e)}', exc_info=True)
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/debug/reminders', methods=['GET'])
def get_all_reminders():
    """
    获取所有提醒（调试用）
    """
    try:
        db = SessionLocal()
        try:
            reminders = db.query(Reminder).order_by(Reminder.create_time.desc()).all()
            reminders_list = [r.to_dict() for r in reminders]
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': reminders_list
            })
        finally:
            db.close()
    except Exception as e:
        logger.error(f'获取提醒列表异常: {str(e)}', exc_info=True)
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


def verify_signature(signature, timestamp, nonce, token):
    """
    验证微信消息签名
    
    Args:
        signature: 微信加密签名
        timestamp: 时间戳
        nonce: 随机数
        token: 令牌
    
    Returns:
        bool: 验证是否通过
    """
    # 将 token、timestamp、nonce 三个参数进行字典序排序
    tmp_arr = [token, timestamp, nonce]
    tmp_arr.sort()
    
    # 将三个参数字符串拼接成一个字符串进行 sha1 加密
    tmp_str = ''.join(tmp_arr)
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    
    # 将加密后的字符串与 signature 对比
    return tmp_str == signature


@app.route('/api/wx/message', methods=['GET', 'POST'])
def wx_message():
    """
    微信消息推送接口
    
    GET: 用于验证服务器（微信服务器会发送验证请求）
    POST: 用于接收消息和事件
    """
    if request.method == 'GET':
        # 验证服务器
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        logger.info(f'收到微信服务器验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}')
        
        # 验证签名
        if verify_signature(signature, timestamp, nonce, WX_TOKEN):
            logger.info('✅ 微信服务器验证成功')
            return echostr, 200
        else:
            logger.warning('❌ 微信服务器验证失败：签名不匹配')
            return '验证失败', 403
    
    elif request.method == 'POST':
        # 接收消息
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        
        # 验证签名
        if not verify_signature(signature, timestamp, nonce, WX_TOKEN):
            logger.warning('❌ 消息签名验证失败')
            return '签名验证失败', 403
        
        # 获取消息内容
        try:
            # 微信可能发送 XML 或 JSON 格式的消息
            if request.is_json:
                data = request.json
                logger.info(f'收到微信消息（JSON）: {data}')
            else:
                # XML 格式（需要解析）
                xml_data = request.data.decode('utf-8')
                logger.info(f'收到微信消息（XML）: {xml_data}')
                # 这里可以添加 XML 解析逻辑
                data = {'raw': xml_data}
            
            # 处理消息
            # 根据消息类型进行不同处理
            msg_type = data.get('MsgType', '')
            
            if msg_type == 'text':
                # 文本消息
                content = data.get('Content', '')
                from_user = data.get('FromUserName', '')
                logger.info(f'收到文本消息: 用户={from_user}, 内容={content}')
                # 这里可以添加自动回复逻辑
                
            elif msg_type == 'event':
                # 事件消息
                event = data.get('Event', '')
                logger.info(f'收到事件消息: 事件类型={event}')
                # 这里可以处理各种事件，如关注、取消关注等
            
            # 返回 success 表示接收成功
            return 'success', 200
            
        except Exception as e:
            logger.error(f'处理微信消息异常: {str(e)}', exc_info=True)
            return '处理失败', 500
    
    return 'Method not allowed', 405


@app.route('/api/reminder/<string:reminder_id>/share', methods=['POST'])
def share_reminder(reminder_id):
    """
    分享提醒接口
    
    请求体:
    {
        "owner_openid": "提醒创建者openid"
    }
    """
    try:
        data = request.json
        owner_openid = data.get('owner_openid')
        
        if not owner_openid:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少必要字段: owner_openid'
            }), 400
        
        db = SessionLocal()
        try:
            # 查找提醒
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                return jsonify({
                    'errcode': 404,
                    'errmsg': '提醒不存在'
                }), 404
            
            # 严格验证：只有提醒创建者可以分享
            if reminder.owner_openid != owner_openid:
                logger.warning(f'无权分享提醒: reminder_id={reminder_id}, owner={reminder.owner_openid}, requester={owner_openid}')
                return jsonify({
                    'errcode': 403,
                    'errmsg': '只有提醒创建者可以分享此提醒'
                }), 403
            
            # 额外验证：确保openid也匹配（双重验证）
            if reminder.openid != owner_openid and reminder.owner_openid != owner_openid:
                logger.warning(f'双重验证失败: reminder_id={reminder_id}, openid={reminder.openid}, owner={reminder.owner_openid}, requester={owner_openid}')
                return jsonify({
                    'errcode': 403,
                    'errmsg': '无权分享此提醒'
                }), 403
            
            # 标记为已分享（允许多次分享，此字段仅用于统计）
            reminder.shared = True
            db.commit()
            
            # 生成分享链接（每次分享都生成新的链接，支持多次分享）
            share_url = f"pages/index/index?reminder_id={reminder_id}&action=accept"
            
            logger.info(f'提醒分享成功: ID={reminder_id}, owner={owner_openid} (可多次分享)')
            
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': {
                    'shareUrl': share_url,
                    'reminderId': reminder_id
                }
            })
        except Exception as e:
            db.rollback()
            logger.error(f'分享提醒失败: {str(e)}')
            return jsonify({
                'errcode': 500,
                'errmsg': str(e)
            }), 500
        finally:
            db.close()
    except Exception as e:
        logger.error(f'分享提醒异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminder/<string:reminder_id>/accept', methods=['POST'])
def accept_reminder(reminder_id):
    """
    接受分享的提醒接口
    
    请求体:
    {
        "assigned_openid": "被分配的好友openid"
    }
    """
    try:
        data = request.json
        assigned_openid = data.get('assigned_openid')
        
        if not assigned_openid:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少必要字段: assigned_openid'
            }), 400
        
        db = SessionLocal()
        try:
            # 查找原提醒
            original_reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not original_reminder:
                return jsonify({
                    'errcode': 404,
                    'errmsg': '提醒不存在'
                }), 404
            
            # 防重复1：不能接受自己创建的提醒
            if original_reminder.owner_openid == assigned_openid:
                logger.warning(f'不能接受自己的提醒: reminder_id={reminder_id}, owner={original_reminder.owner_openid}, assigned={assigned_openid}')
                return jsonify({
                    'errcode': 400,
                    'errmsg': '不能接受自己创建的提醒'
                }), 400
            
            # 防重复2：检查是否已经存在提醒副本
            new_reminder_id = f"{assigned_openid}_{original_reminder.reminder_time}"
            existing_reminder = db.query(Reminder).filter(Reminder.id == new_reminder_id).first()
            
            if existing_reminder:
                logger.info(f'提醒已存在: reminder_id={reminder_id}, assigned={assigned_openid}, existing_id={new_reminder_id}')
                return jsonify({
                    'errcode': 400,
                    'errmsg': '您已经接受过此提醒',
                    'data': {
                        'reminder': existing_reminder.to_dict(),
                        'alreadyAccepted': True
                    }
                }), 400
            
            # 防重复3：检查分配记录
            assignment_id = f"{reminder_id}_{assigned_openid}"
            existing_assignment = db.query(ReminderAssignment).filter(
                ReminderAssignment.id == assignment_id
            ).first()
            
            if existing_assignment:
                if existing_assignment.status == 'accepted':
                    # 已经接受过，返回已存在的提醒
                    logger.info(f'分配记录已存在且已接受: assignment_id={assignment_id}')
                    if existing_reminder:
                        return jsonify({
                            'errcode': 400,
                            'errmsg': '您已经接受过此提醒',
                            'data': {
                                'reminder': existing_reminder.to_dict(),
                                'alreadyAccepted': True
                            }
                        }), 400
                    else:
                        # 记录存在但提醒不存在，可能是数据不一致，允许重新创建
                        logger.warning(f'分配记录存在但提醒不存在，允许重新创建: assignment_id={assignment_id}')
                elif existing_assignment.status == 'rejected':
                    # 之前拒绝过，允许重新接受
                    logger.info(f'之前拒绝过，允许重新接受: assignment_id={assignment_id}')
                # pending状态继续处理
            
            # 创建或更新分配记录
            if existing_assignment:
                assignment = existing_assignment
                assignment.status = 'accepted'
                assignment.accept_time = datetime.now()
            else:
                assignment = ReminderAssignment(
                    id=assignment_id,
                    reminder_id=reminder_id,
                    owner_openid=original_reminder.owner_openid,
                    assigned_openid=assigned_openid,
                    status='accepted',
                    accept_time=datetime.now()
                )
                db.add(assignment)
            
            # 再次检查提醒是否已存在（防止并发）
            final_check = db.query(Reminder).filter(Reminder.id == new_reminder_id).first()
            if final_check:
                db.commit()
                logger.info(f'并发检查：提醒已存在，返回现有提醒: reminder_id={new_reminder_id}')
                return jsonify({
                    'errcode': 0,
                    'errmsg': 'success',
                    'data': {
                        'reminder': final_check.to_dict(),
                        'message': '提醒已存在'
                    }
                })
            
            # 创建新提醒
            new_reminder = Reminder(
                id=new_reminder_id,
                openid=assigned_openid,  # 当前拥有者（被分配的好友）
                owner_openid=original_reminder.owner_openid,  # 原创建者
                title=original_reminder.title,
                thing1=original_reminder.thing1,
                thing4=original_reminder.thing4,
                time=original_reminder.time,
                reminder_time=original_reminder.reminder_time,
                enable_subscribe=original_reminder.enable_subscribe,
                status='pending',
                completed=False,
                shared=False
            )
            db.add(new_reminder)
            
            # 如果原提醒开启了订阅，也为新提醒安排定时任务
            if new_reminder.enable_subscribe and new_reminder.reminder_time:
                reminder_dict = new_reminder.to_dict()
                schedule_reminder(reminder_dict)
            
            db.commit()
            
            logger.info(f'接受提醒成功: 原提醒ID={reminder_id}, 新提醒ID={new_reminder_id}, 接受者={assigned_openid}')
            
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': {
                    'reminder': new_reminder.to_dict()
                }
            })
        except Exception as e:
            db.rollback()
            logger.error(f'接受提醒失败: {str(e)}', exc_info=True)
            return jsonify({
                'errcode': 500,
                'errmsg': str(e)
            }), 500
        finally:
            db.close()
    except Exception as e:
        logger.error(f'接受提醒异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


@app.route('/api/reminders/assigned', methods=['GET'])
def get_assigned_reminders():
    """
    获取分配给自己的提醒列表
    
    查询参数:
    openid: 用户openid
    """
    try:
        openid = request.args.get('openid')
        if not openid:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少必要参数: openid'
            }), 400
        
        db = SessionLocal()
        try:
            # 查找分配给该用户的提醒
            assignments = db.query(ReminderAssignment).filter(
                ReminderAssignment.assigned_openid == openid,
                ReminderAssignment.status == 'accepted'
            ).all()
            
            # 获取对应的提醒列表
            reminders = []
            for assignment in assignments:
                # 查找被分配者拥有的提醒（通过owner_openid和reminder_time匹配）
                reminder = db.query(Reminder).filter(
                    Reminder.owner_openid == assignment.owner_openid,
                    Reminder.openid == openid,
                    Reminder.reminder_time == db.query(Reminder).filter(
                        Reminder.id == assignment.reminder_id
                    ).first().reminder_time
                ).first()
                
                if reminder:
                    reminder_dict = reminder.to_dict()
                    reminder_dict['fromOwner'] = True  # 标记为来自分享
                    reminders.append(reminder_dict)
            
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': reminders
            })
        finally:
            db.close()
    except Exception as e:
        logger.error(f'获取分配的提醒列表异常: {str(e)}')
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


if __name__ == '__main__':
    logger.info('启动 Flask 服务...')
    logger.info(f'APPID: {APPID}')
    logger.info(f'模板ID: {TEMPLATE_ID}')
    
    # 开发环境运行（使用 5001 端口，避免与 macOS AirPlay 冲突）
    app.run(host='0.0.0.0', port=5001, debug=True)

