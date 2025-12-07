"""
微信小程序订阅消息服务端 - Flask 实现
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
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
from sqlalchemy import text
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
# 确保日志输出到标准输出，方便 docker compose logs 查看
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()  # 输出到标准输出
    ]
)
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
    """确保数据库表存在，如果不存在则创建，并检查字段是否完整"""
    logger.info('开始检查/创建数据库表...')
    
    # 先检查表是否已存在，避免重复创建
    db = SessionLocal()
    try:
        # 检查 reminders 表是否存在
        result = db.execute(text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'reminders'
        """), {'db_name': DB_NAME})
        row = result.fetchone()
        table_exists = row[0] > 0 if row else False
        
        if table_exists:
            logger.info('✅ reminders 表已存在，跳过创建')
            db.close()
            # 表已存在，直接进入字段检查流程
        else:
            db.close()
            logger.info('reminders 表不存在，开始创建...')
            # 表不存在，需要创建
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f'尝试创建表 (第 {attempt + 1}/{max_retries} 次)')
                    # 先尝试创建所有表（如果不存在会自动创建）
                    Base.metadata.create_all(engine, checkfirst=True)
                    logger.info('✅ SQLAlchemy 表创建/检查完成')
                    break
                except Exception as create_error:
                    error_msg = str(create_error)
                    # 如果表已存在（可能是其他进程刚创建的），忽略错误
                    if "already exists" in error_msg or "1050" in error_msg:
                        logger.info('✅ 表已存在（可能由其他进程创建），跳过创建')
                        break
                    else:
                        logger.warning(f'创建表失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}')
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(1)  # 等待1秒后重试
                            continue
                        else:
                            raise create_error
    except Exception as check_error:
        db.close()
        error_msg = str(check_error)
        # 如果检查表存在时出错，尝试直接创建（可能是权限问题）
        logger.warning(f'检查表存在时出错: {error_msg}，尝试直接创建表')
        try:
            Base.metadata.create_all(engine, checkfirst=True)
            logger.info('✅ SQLAlchemy 表创建/检查完成')
        except Exception as create_error:
            error_msg = str(create_error)
            # 如果表已存在，忽略错误
            if "already exists" in error_msg or "1050" in error_msg:
                logger.info('✅ 表已存在，跳过创建')
            else:
                logger.error(f'数据库表创建失败: {create_error}')
                raise create_error
    
    # 验证表是否真的存在（简单验证）
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1 FROM reminders LIMIT 1"))
        result.fetchone()  # 确保查询执行
        db.close()
        logger.info('✅ 验证表存在成功 - reminders 表已存在')
    except Exception as verify_error:
        db.close()
        error_msg = str(verify_error)
        logger.error(f'验证表存在失败: {error_msg}')
        # 如果表真的不存在，尝试最后一次创建
        if "doesn't exist" in error_msg or "1146" in error_msg:
            logger.warning('表验证失败，尝试最后一次创建...')
            try:
                Base.metadata.create_all(engine, checkfirst=True)
                logger.info('✅ 最后创建尝试完成')
            except Exception as create_error:
                error_msg = str(create_error)
                if "already exists" in error_msg or "1050" in error_msg:
                    logger.info('✅ 表已存在（可能由其他进程创建）')
                else:
                    logger.error(f'最后创建尝试失败: {create_error}')
                    raise create_error
    
    # 检查并添加缺失的字段（用于表结构升级）
    db = SessionLocal()
    try:
        # 检查 reminders 表是否存在 owner_openid 字段
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as cnt
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = :db_name 
                AND TABLE_NAME = 'reminders' 
                AND COLUMN_NAME = 'owner_openid'
            """), {'db_name': DB_NAME})
            row = result.fetchone()
            has_owner_openid = row[0] > 0 if row else False
            
            if not has_owner_openid:
                logger.info('检测到 reminders 表缺少 owner_openid 字段，正在添加...')
                try:
                    # 先添加字段（允许NULL，避免已有数据问题）
                    db.execute(text("""
                        ALTER TABLE reminders 
                        ADD COLUMN owner_openid VARCHAR(100) DEFAULT ''
                    """))
                    # 更新已有数据的 owner_openid
                    db.execute(text("""
                        UPDATE reminders 
                        SET owner_openid = openid 
                        WHERE owner_openid = '' OR owner_openid IS NULL
                    """))
                    # 然后设置为 NOT NULL
                    db.execute(text("""
                        ALTER TABLE reminders 
                        MODIFY COLUMN owner_openid VARCHAR(100) NOT NULL DEFAULT ''
                    """))
                    db.commit()
                    logger.info('✅ 已添加 owner_openid 字段并更新数据')
                except Exception as e:
                    logger.warning(f'添加 owner_openid 字段失败（可能已存在）: {str(e)}')
                    db.rollback()
        except Exception as e:
            logger.warning(f'检查 owner_openid 字段时出错: {str(e)}')
        
        # 检查 shared 字段
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as cnt
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = :db_name 
                AND TABLE_NAME = 'reminders' 
                AND COLUMN_NAME = 'shared'
            """), {'db_name': DB_NAME})
            row = result.fetchone()
            has_shared = row[0] > 0 if row else False
            
            if not has_shared:
                logger.info('检测到 reminders 表缺少 shared 字段，正在添加...')
                try:
                    db.execute(text("""
                        ALTER TABLE reminders 
                        ADD COLUMN shared BOOLEAN DEFAULT FALSE
                    """))
                    db.commit()
                    logger.info('✅ 已添加 shared 字段')
                except Exception as e:
                    logger.warning(f'添加 shared 字段失败（可能已存在）: {str(e)}')
                    db.rollback()
        except Exception as e:
            logger.warning(f'检查 shared 字段时出错: {str(e)}')
        
        # 检查索引（如果字段存在）
        if has_owner_openid:
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) as cnt
                    FROM information_schema.STATISTICS 
                    WHERE TABLE_SCHEMA = :db_name 
                    AND TABLE_NAME = 'reminders' 
                    AND INDEX_NAME = 'idx_owner_openid'
                """), {'db_name': DB_NAME})
                row = result.fetchone()
                has_index = row[0] > 0 if row else False
                
                if not has_index:
                    logger.info('检测到 reminders 表缺少 idx_owner_openid 索引，正在添加...')
                    try:
                        db.execute(text("""
                            CREATE INDEX idx_owner_openid ON reminders(owner_openid)
                        """))
                        db.commit()
                        logger.info('✅ 已添加 idx_owner_openid 索引')
                    except Exception as e:
                        logger.warning(f'添加索引失败（可能已存在）: {str(e)}')
                        db.rollback()
            except Exception as e:
                logger.warning(f'检查索引时出错: {str(e)}')
                
    except Exception as e:
        logger.warning(f'检查表结构时出错: {str(e)}')
    finally:
        db.close()
    
    logger.info('数据库表检查/创建完成')

# 确保表存在的辅助函数（在数据库操作失败时调用）
def handle_table_error(error, operation_name="数据库操作"):
    """处理表不存在的错误，自动创建表"""
    error_msg = str(error)
    if "doesn't exist" in error_msg or "1146" in error_msg or "Table" in error_msg and "doesn't exist" in error_msg:
        logger.warning(f'检测到表不存在错误 ({operation_name})，尝试自动创建表')
        try:
            ensure_tables_exist()
            logger.info(f'✅ 表创建完成，{operation_name} 可以重试')
            return True
        except Exception as create_error:
            logger.error(f'自动创建表失败: {str(create_error)}')
            return False
    return False

# 延迟初始化：避免在导入时执行，只在应用启动时执行
# 在 Gunicorn 环境下，这些会在 worker 启动时执行
# 在直接运行 app.py 时，会在 if __name__ == '__main__' 中执行

# 初始化调度器（延迟到应用启动时）
scheduler = None

def init_app():
    """初始化应用（数据库表、调度器等）"""
    global scheduler
    try:
        # 确保表存在
        ensure_tables_exist()
        
        # 初始化调度器
        if scheduler is None:
            scheduler = BackgroundScheduler()
            scheduler.start()
            logger.info('✅ 调度器启动成功')
    except Exception as e:
        logger.error(f'❌ 应用初始化失败: {str(e)}')
        logger.error(f'错误详情: {type(e).__name__}: {str(e)}')
        import traceback
        logger.error(f'堆栈跟踪:\n{traceback.format_exc()}')
        # 不抛出异常，允许应用继续运行
        logger.warning('应用将继续运行，但某些功能可能不可用')

# 在 Gunicorn 环境下，使用 post_fork 钩子初始化
# 对于直接运行，在 if __name__ == '__main__' 中调用


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
            # 将过期时间存储为 datetime 对象
            token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
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
                logger.info(f'开始发送提醒: ID={reminder["id"]}, openid={reminder["openid"]}, owner_openid={reminder.get("ownerOpenid")}')
                
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
                
                db = SessionLocal()
                try:
                    # 查找所有需要发送提醒的用户
                    # 1. 创建者（owner_openid）
                    # 2. 所有被分配者（通过reminder_assignments表查找）
                    owner_openid = reminder.get('ownerOpenid') or reminder.get('owner_openid')
                    reminder_time_stamp = reminder.get('reminderTime')
                    current_reminder_id = reminder.get('id')
                    current_openid = reminder.get('openid')
                    
                    # 确定原提醒ID
                    # 如果当前提醒是创建者的（openid == owner_openid），则当前ID就是原提醒ID
                    # 如果当前提醒是被分配者的（openid != owner_openid），则需要通过owner_openid和reminder_time构造原提醒ID
                    if current_openid == owner_openid:
                        original_reminder_id = current_reminder_id
                    else:
                        # 被分配者的提醒，原提醒ID是 owner_openid_reminder_time
                        original_reminder_id = f"{owner_openid}_{reminder_time_stamp}"
                    
                    # 获取创建者的提醒记录（通过owner_openid和reminder_time查找）
                    owner_reminder = db.query(Reminder).filter(
                        Reminder.owner_openid == owner_openid,
                        Reminder.openid == owner_openid,
                        Reminder.reminder_time == reminder_time_stamp
                    ).first()
                    
                    # 获取所有被分配的提醒记录（通过原提醒ID查找）
                    # 注意：assignment.reminder_id是原提醒的ID（owner_openid_reminder_time）
                    assignments = db.query(ReminderAssignment).filter(
                        ReminderAssignment.reminder_id == original_reminder_id,
                        ReminderAssignment.status == 'accepted'
                    ).all()
                    
                    # 收集所有需要发送提醒的openid
                    openids_to_notify = set()
                    
                    # 添加创建者
                    if owner_reminder and owner_reminder.enable_subscribe:
                        openids_to_notify.add(owner_openid)
                        logger.info(f'添加创建者到通知列表: {owner_openid}')
                    
                    # 添加所有被分配者
                    for assignment in assignments:
                        # 验证assignment对应的提醒是否存在且开启了订阅
                        assigned_reminder = db.query(Reminder).filter(
                            Reminder.id == f"{assignment.assigned_openid}_{reminder_time_stamp}"
                        ).first()
                        
                        if assigned_reminder and assigned_reminder.enable_subscribe:
                            openids_to_notify.add(assignment.assigned_openid)
                            logger.info(f'添加被分配者到通知列表: {assignment.assigned_openid}')
                    
                    logger.info(f'需要发送提醒的用户数量: {len(openids_to_notify)}, 用户列表: {list(openids_to_notify)}')
                    
                    # 发送提醒给所有用户
                    success_count = 0
                    fail_count = 0
                    
                    for openid in openids_to_notify:
                        # 发送订阅消息
                        result = send_subscribe_message(
                            openid=openid,
                            template_id=TEMPLATE_ID,
                            page='pages/index/index',
                            data=template_data
                        )
                        
                        logger.info(f'订阅消息发送结果 (openid={openid}): {result}')
                        
                        if result.get('errcode') == 0:
                            success_count += 1
                            logger.info(f'✅ 提醒发送成功: openid={openid}')
                        else:
                            fail_count += 1
                            error_code = result.get('errcode')
                            error_msg = result.get('errmsg', '未知错误')
                            logger.error(f'❌ 提醒发送失败: openid={openid}, errcode={error_code}, errmsg={error_msg}')
                    
                    # 更新所有相关提醒的状态到数据库
                    # 更新创建者的提醒状态
                    if owner_reminder:
                        if success_count > 0:
                            owner_reminder.status = 'sent'
                        else:
                            owner_reminder.status = 'failed'
                    
                    # 更新所有被分配者的提醒状态
                    for assignment in assignments:
                        assigned_reminder = db.query(Reminder).filter(
                            Reminder.id == f"{assignment.assigned_openid}_{reminder_time_stamp}"
                        ).first()
                        
                        if assigned_reminder:
                            if success_count > 0:
                                assigned_reminder.status = 'sent'
                            else:
                                assigned_reminder.status = 'failed'
                    
                    db.commit()
                    logger.info(f'提醒发送完成: 成功={success_count}, 失败={fail_count}')
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f'发送提醒异常: ID={reminder["id"]}, 错误: {str(e)}', exc_info=True)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f'发送提醒异常: ID={reminder["id"]}, 错误: {str(e)}', exc_info=True)
        
        # 确保调度器已初始化
        global scheduler
        if scheduler is None:
            logger.warning('调度器未初始化，尝试初始化...')
            init_app()
            if scheduler is None:
                logger.error('调度器初始化失败，无法安排提醒任务')
                return
        
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
        # 使用 openid + 创建时间戳（毫秒）作为唯一 ID，这样ID不会因为reminderTime改变而改变
        create_timestamp = int(datetime.now().timestamp() * 1000)  # 当前时间戳（毫秒）
        reminder_id = f"{data['openid']}_{create_timestamp}"
        owner_openid = data['openid']  # 创建者就是当前用户
        db = SessionLocal()
        try:
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
            except Exception as add_error:
                # 如果表不存在，尝试创建后重试
                if handle_table_error(add_error, "创建提醒"):
                    reminder = Reminder(
                        id=reminder_id,
                        openid=data['openid'],
                        owner_openid=owner_openid,
                        title=thing1,
                        thing1=thing1,
                        thing4=thing4,
                        time=time_str,
                        reminder_time=data['reminderTime'],
                        enable_subscribe=data.get('enableSubscribe', False),
                        status='pending',
                        completed=False,
                        shared=False
                    )
                    db.add(reminder)
                    db.commit()
                else:
                    raise add_error
            
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
                
                # 权限检查：只有创建者（owner_openid）可以修改提醒
                # 如果 openid != owner_openid，说明这是被分享的提醒，不能修改
                if reminder.openid != reminder.owner_openid:
                    return jsonify({
                        'errcode': 403,
                        'errmsg': '不能修改他人分享的提醒'
                    }), 403
                
                # 保存原始提醒时间，用于查找被分享的提醒
                original_reminder_time = reminder.reminder_time
                original_owner_openid = reminder.owner_openid
                
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
                    global scheduler
                    if scheduler is not None:
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
                
                # 同步更新所有被分享的提醒副本
                # 由于ID现在是基于openid_创建时间戳，不会因为reminderTime改变而改变
                # 所以可以直接通过owner_openid和reminder_time查找所有被分享的提醒
                # 如果reminderTime改变了，我们需要先通过原reminder_time查找，然后更新
                
                # 查找所有被分享的提醒（owner_openid相同，但openid不同）
                # 如果reminderTime改变了，先通过原reminder_time查找
                if 'reminderTime' in data and data['reminderTime'] != original_reminder_time:
                    # reminderTime改变了，先通过原reminder_time查找所有被分享的提醒
                    shared_reminders = db.query(Reminder).filter(
                        Reminder.owner_openid == original_owner_openid,
                        Reminder.openid != original_owner_openid,
                        Reminder.reminder_time == original_reminder_time
                    ).all()
                else:
                    # reminderTime未改变，直接通过当前reminder_time查找
                    current_reminder_time = reminder.reminder_time
                    shared_reminders = db.query(Reminder).filter(
                        Reminder.owner_openid == original_owner_openid,
                        Reminder.openid != original_owner_openid,
                        Reminder.reminder_time == current_reminder_time
                    ).all()
                
                logger.info(f'找到 {len(shared_reminders)} 个被分享的提醒副本，开始同步更新')
                
                for shared_reminder in shared_reminders:
                    # 同步更新字段（直接更新，不删除重建）
                    if 'thing1' in data:
                        shared_reminder.thing1 = data['thing1']
                        shared_reminder.title = data['thing1']
                    if 'thing4' in data:
                        shared_reminder.thing4 = data['thing4']
                    if 'time' in data:
                        shared_reminder.time = data['time']
                    if 'reminderTime' in data:
                        shared_reminder.reminder_time = data['reminderTime']
                    
                    # 同步订阅状态
                    if 'enableSubscribe' in data:
                        shared_reminder.enable_subscribe = data['enableSubscribe']
                    
                    # 如果开启了订阅，为被分享的提醒也重新安排定时任务
                    if shared_reminder.enable_subscribe and shared_reminder.reminder_time:
                        # 先取消旧任务
                        if scheduler is not None:
                            try:
                                scheduler.remove_job(f"reminder_{shared_reminder.id}")
                            except:
                                pass
                        
                        # 重新安排任务
                        shared_reminder_dict = shared_reminder.to_dict()
                        schedule_reminder(shared_reminder_dict)
                        shared_reminder.status = 'pending'
                    else:
                        # 未开启订阅，根据时间判断状态
                        shared_reminder_time = datetime.fromtimestamp(shared_reminder.reminder_time / 1000)
                        now = datetime.now()
                        if shared_reminder_time <= now:
                            shared_reminder.status = 'expired'
                        else:
                            shared_reminder.status = 'no_subscribe'
                    
                    logger.info(f'已同步更新被分享的提醒: ID={shared_reminder.id}, openid={shared_reminder.openid}')
                
                db.commit()
                
                logger.info(f'更新提醒成功: ID={reminder_id}, 同步更新了 {len(shared_reminders)} 个被分享的提醒')
                
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
            global scheduler
            if scheduler is not None:
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
            try:
                reminders = db.query(Reminder).filter(
                    Reminder.openid == openid
                ).order_by(Reminder.create_time.desc()).all()
            except Exception as query_error:
                # 如果表不存在，尝试创建后重试
                if handle_table_error(query_error, "获取提醒列表"):
                    reminders = db.query(Reminder).filter(
                        Reminder.openid == openid
                    ).order_by(Reminder.create_time.desc()).all()
                else:
                    raise query_error
            
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
            
            # 防重复2：检查是否已经接受过此提醒（通过assignment表检查）
            # 检查是否已经存在该提醒的分配记录
            assignment_id = f"{reminder_id}_{assigned_openid}"
            existing_assignment = db.query(ReminderAssignment).filter(
                ReminderAssignment.id == assignment_id
            ).first()
            
            # 如果已经接受过，查找对应的提醒
            if existing_assignment and existing_assignment.status == 'accepted':
                # 通过owner_openid和reminder_time查找已存在的提醒
                existing_reminder = db.query(Reminder).filter(
                    Reminder.owner_openid == original_reminder.owner_openid,
                    Reminder.openid == assigned_openid,
                    Reminder.reminder_time == original_reminder.reminder_time
                ).first()
            else:
                existing_reminder = None
            
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
            # 通过owner_openid和reminder_time查找
            final_check = db.query(Reminder).filter(
                Reminder.owner_openid == original_reminder.owner_openid,
                Reminder.openid == assigned_openid,
                Reminder.reminder_time == original_reminder.reminder_time
            ).first()
            
            if final_check:
                db.commit()
                logger.info(f'并发检查：提醒已存在，返回现有提醒: reminder_id={final_check.id}')
                return jsonify({
                    'errcode': 0,
                    'errmsg': 'success',
                    'data': {
                        'reminder': final_check.to_dict(),
                        'message': '提醒已存在'
                    }
                })
            
            # 创建新提醒
            # 使用 openid + 创建时间戳作为ID（确保ID唯一且不会因为reminderTime改变而改变）
            create_timestamp = int(datetime.now().timestamp() * 1000)
            new_reminder_id = f"{assigned_openid}_{create_timestamp}"
            
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


# Gunicorn 启动时的钩子函数
def on_starting(server):
    """Gunicorn 启动时的回调（在主进程中执行）"""
    logger.info('=' * 60)
    logger.info('Gunicorn 主进程启动中...')
    logger.info('=' * 60)

def when_ready(server):
    """所有 worker 就绪时的回调"""
    logger.info('=' * 60)
    logger.info('所有 Worker 已就绪')
    logger.info('=' * 60)

def post_fork(server, worker):
    """Worker 进程 fork 后的回调（在每个 worker 中执行）"""
    logger.info(f'Worker {worker.pid} 启动中...')
    try:
        init_app()
        logger.info(f'✅ Worker {worker.pid} 初始化完成')
    except Exception as e:
        logger.error(f'❌ Worker {worker.pid} 初始化失败: {str(e)}')
        import traceback
        logger.error(f'堆栈跟踪:\n{traceback.format_exc()}')

def worker_int(worker):
    """Worker 接收到 INT 信号时的回调"""
    logger.info(f'Worker {worker.pid} 接收到 INT 信号')

if __name__ == '__main__':
    logger.info('=' * 60)
    logger.info('启动 Flask 服务（开发模式）...')
    logger.info(f'APPID: {APPID}')
    logger.info(f'模板ID: {TEMPLATE_ID}')
    logger.info('=' * 60)
    
    # 初始化应用
    init_app()
    
    logger.info('=' * 60)
    logger.info('Flask 服务启动中...')
    logger.info('=' * 60)
    
    # 开发环境运行（使用 5001 端口，避免与 macOS AirPlay 冲突）
    app.run(host='0.0.0.0', port=5001, debug=True)

