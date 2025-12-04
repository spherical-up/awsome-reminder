#!/usr/bin/env python3
"""
测试数据库和表创建脚本
用于验证数据库连接和表创建是否正常
"""
import sys
import os
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# 获取数据库配置
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'reminder_db')

print("=" * 60)
print("数据库和表创建测试")
print("=" * 60)
print(f"数据库: {DB_NAME}")
print(f"主机: {DB_HOST}:{DB_PORT}")
print(f"用户: {DB_USER}")
print("=" * 60)

# 1. 测试数据库连接
print("\n1. 测试数据库连接...")
try:
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    print("✅ 数据库连接成功")
    connection.close()
except Exception as e:
    print(f"❌ 数据库连接失败: {str(e)}")
    sys.exit(1)

# 2. 测试数据库是否存在
print("\n2. 检查数据库是否存在...")
try:
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        result = cursor.fetchone()
        if result:
            print(f"✅ 数据库 {DB_NAME} 已存在")
        else:
            print(f"⚠️  数据库 {DB_NAME} 不存在，尝试创建...")
            cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            print(f"✅ 数据库 {DB_NAME} 创建成功")
    connection.close()
except Exception as e:
    print(f"❌ 检查/创建数据库失败: {str(e)}")
    sys.exit(1)

# 3. 测试 SQLAlchemy 连接
print("\n3. 测试 SQLAlchemy 连接...")
try:
    DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, echo=False)
    
    # 测试连接
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()
    print("✅ SQLAlchemy 连接成功")
except Exception as e:
    print(f"❌ SQLAlchemy 连接失败: {str(e)}")
    sys.exit(1)

# 4. 测试表创建（需要导入模型）
print("\n4. 测试表创建...")
print("⚠️  需要运行 app.py 来创建表，或者手动执行 SQL")
print("   建议运行: python app.py")
print("   或者手动执行以下 SQL:")
print("   - 查看 app.py 中的 Reminder 和 ReminderAssignment 模型定义")

# 5. 检查表是否存在
print("\n5. 检查表是否存在...")
try:
    DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, echo=False)
    
    with engine.connect() as conn:
        # 检查 reminders 表
        try:
            result = conn.execute(text("SELECT 1 FROM reminders LIMIT 1"))
            result.fetchone()
            print("✅ reminders 表存在")
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print("❌ reminders 表不存在")
                print("   请运行 app.py 来创建表")
            else:
                print(f"❌ 检查 reminders 表时出错: {error_msg}")
        
        # 检查 reminder_assignments 表
        try:
            result = conn.execute(text("SELECT 1 FROM reminder_assignments LIMIT 1"))
            result.fetchone()
            print("✅ reminder_assignments 表存在")
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "1146" in error_msg:
                print("❌ reminder_assignments 表不存在")
                print("   请运行 app.py 来创建表")
            else:
                print(f"❌ 检查 reminder_assignments 表时出错: {error_msg}")
except Exception as e:
    print(f"❌ 检查表时出错: {str(e)}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n如果表不存在，请:")
print("1. 确保所有依赖已安装: pip install -r requirements.txt")
print("2. 运行应用: python app.py")
print("3. 查看日志确认表是否创建成功")

