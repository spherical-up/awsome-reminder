#!/bin/bash
# 数据库连接检查脚本
# 用于诊断 Docker 容器中的数据库连接问题

echo "=========================================="
echo "数据库连接诊断工具"
echo "=========================================="
echo ""

# 检查是否在 Docker 容器中
if [ -f /.dockerenv ]; then
    echo "✅ 检测到 Docker 环境"
    CONTAINER_NAME="当前容器"
else
    echo "⚠️  不在 Docker 容器中，将检查容器配置"
    CONTAINER_NAME="reminder-server"
fi

echo ""
echo "1. 检查环境变量配置..."
echo "----------------------------------------"

if [ -f .env ]; then
    echo "✅ 找到 .env 文件"
    echo ""
    echo "数据库配置："
    grep "^DB_" .env | sed 's/PASSWORD=.*/PASSWORD=***/' || echo "⚠️  未找到 DB_* 配置"
else
    echo "❌ 未找到 .env 文件"
    echo "   请创建 .env 文件并配置数据库连接"
fi

echo ""
echo "2. 检查 Docker 网络配置..."
echo "----------------------------------------"

# 检查 extra_hosts 配置
if docker inspect $CONTAINER_NAME 2>/dev/null | grep -q "host.docker.internal"; then
    echo "✅ Docker 容器已配置 host.docker.internal"
else
    echo "⚠️  Docker 容器未配置 host.docker.internal"
    echo "   请检查 docker-compose.yml 中的 extra_hosts 配置"
fi

echo ""
echo "3. 测试数据库连接..."
echo "----------------------------------------"

# 读取 .env 文件中的配置
if [ -f .env ]; then
    source .env
    
    DB_HOST=${DB_HOST:-host.docker.internal}
    DB_PORT=${DB_PORT:-3306}
    DB_USER=${DB_USER:-root}
    DB_NAME=${DB_NAME:-reminder_db}
    
    echo "尝试连接: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    echo ""
    
    # 在容器内测试连接
    if [ -f /.dockerenv ]; then
        # 在容器内直接测试
        python3 << EOF
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'host.docker.internal')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'reminder_db')

try:
    print(f"正在连接 {DB_USER}@{DB_HOST}:{DB_PORT}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        connect_timeout=5
    )
    print("✅ 数据库连接成功！")
    
    # 检查数据库是否存在
    with conn.cursor() as cursor:
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        result = cursor.fetchone()
        if result:
            print(f"✅ 数据库 '{DB_NAME}' 存在")
        else:
            print(f"⚠️  数据库 '{DB_NAME}' 不存在")
    
    conn.close()
except pymysql.err.OperationalError as e:
    print(f"❌ 数据库连接失败: {e}")
    print("")
    print("可能的解决方案：")
    print("1. 检查 MySQL 服务是否运行")
    print("2. 检查 .env 中的 DB_HOST 配置：")
    print("   - macOS/Windows: DB_HOST=host.docker.internal")
    print("   - Linux: DB_HOST=172.17.0.1")
    print("3. 检查防火墙设置")
    print("4. 检查 MySQL 用户权限")
except Exception as e:
    print(f"❌ 发生错误: {e}")
EOF
    else
        # 在容器外，通过 docker exec 测试
        echo "通过 Docker 容器测试连接..."
        docker exec $CONTAINER_NAME python3 << EOF
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'host.docker.internal')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'reminder_db')

try:
    print(f"正在连接 {DB_USER}@{DB_HOST}:{DB_PORT}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        connect_timeout=5
    )
    print("✅ 数据库连接成功！")
    
    with conn.cursor() as cursor:
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        result = cursor.fetchone()
        if result:
            print(f"✅ 数据库 '{DB_NAME}' 存在")
        else:
            print(f"⚠️  数据库 '{DB_NAME}' 不存在")
    
    conn.close()
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
EOF
    fi
else
    echo "❌ 未找到 .env 文件，无法测试连接"
fi

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="

