#!/bin/bash
# Linux 服务器上设置 DB_HOST 的辅助脚本

echo "=========================================="
echo "Linux 服务器 DB_HOST 配置工具"
echo "=========================================="
echo ""

# 检查是否在 Docker 容器中
if [ -f /.dockerenv ]; then
    echo "⚠️  检测到在 Docker 容器内运行"
    echo "   请在宿主机上运行此脚本"
    exit 1
fi

echo "1. 检测 Docker 网络配置..."
echo "----------------------------------------"

# 方法1: 从 Docker 网络获取网关 IP
GATEWAY_IP=$(docker network inspect bridge 2>/dev/null | grep -i gateway | head -1 | awk -F'"' '{print $4}')

if [ -n "$GATEWAY_IP" ]; then
    echo "✅ 检测到 Docker 网关 IP: $GATEWAY_IP"
    RECOMMENDED_HOST="$GATEWAY_IP"
else
    echo "⚠️  无法自动检测 Docker 网关 IP"
    echo "   尝试其他方法..."
    
    # 方法2: 从默认路由获取
    DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -1)
    if [ -n "$DEFAULT_GW" ]; then
        echo "   检测到默认网关: $DEFAULT_GW"
        RECOMMENDED_HOST="$DEFAULT_GW"
    else
        # 方法3: 使用常见的 Docker 默认网关
        RECOMMENDED_HOST="172.17.0.1"
        echo "   使用默认值: $RECOMMENDED_HOST"
    fi
fi

echo ""
echo "2. 检查 MySQL 服务位置..."
echo "----------------------------------------"

# 检查 MySQL 是否在宿主机上运行
if systemctl is-active --quiet mysql || systemctl is-active --quiet mysqld || systemctl is-active --quiet mariadb; then
    echo "✅ 检测到 MySQL 在宿主机上运行"
    MYSQL_ON_HOST=true
elif docker ps | grep -q mysql; then
    echo "✅ 检测到 MySQL 在 Docker 容器中运行"
    MYSQL_CONTAINER=$(docker ps | grep mysql | awk '{print $NF}' | head -1)
    echo "   MySQL 容器名: $MYSQL_CONTAINER"
    MYSQL_ON_HOST=false
else
    echo "⚠️  未检测到 MySQL 服务"
    echo "   请确认 MySQL 是否已安装并运行"
    MYSQL_ON_HOST=null
fi

echo ""
echo "3. 推荐配置..."
echo "----------------------------------------"

if [ "$MYSQL_ON_HOST" = "true" ]; then
    echo "MySQL 在宿主机上，推荐配置："
    echo ""
    echo "  方案 A: 使用 Docker 网关 IP（推荐）"
    echo "    DB_HOST=$RECOMMENDED_HOST"
    echo ""
    echo "  方案 B: 使用 host.docker.internal（需要配置 extra_hosts）"
    echo "    DB_HOST=host.docker.internal"
    echo "    （确保 docker-compose.yml 中有 extra_hosts 配置）"
    RECOMMENDED_DB_HOST="$RECOMMENDED_HOST"
elif [ "$MYSQL_ON_HOST" = "false" ]; then
    echo "MySQL 在 Docker 容器中，推荐配置："
    echo ""
    echo "  方案 A: 使用 Docker Compose 服务名（推荐）"
    echo "    DB_HOST=mysql  # 或实际的 MySQL 服务名"
    echo ""
    echo "  方案 B: 使用容器 IP"
    MYSQL_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $MYSQL_CONTAINER 2>/dev/null)
    if [ -n "$MYSQL_IP" ]; then
        echo "    DB_HOST=$MYSQL_IP"
    fi
    RECOMMENDED_DB_HOST="mysql"  # 假设使用 docker-compose 服务名
else
    echo "无法确定 MySQL 位置，使用默认配置："
    RECOMMENDED_DB_HOST="$RECOMMENDED_HOST"
fi

echo ""
echo "4. 当前 .env 文件配置..."
echo "----------------------------------------"

if [ -f .env ]; then
    echo "✅ 找到 .env 文件"
    CURRENT_DB_HOST=$(grep "^DB_HOST=" .env | cut -d'=' -f2)
    if [ -n "$CURRENT_DB_HOST" ]; then
        echo "   当前 DB_HOST: $CURRENT_DB_HOST"
    else
        echo "   ⚠️  未找到 DB_HOST 配置"
    fi
else
    echo "❌ 未找到 .env 文件"
    echo "   将创建新的 .env 文件"
fi

echo ""
echo "5. 设置 DB_HOST..."
echo "----------------------------------------"

# 询问用户是否要更新
read -p "是否要设置 DB_HOST=$RECOMMENDED_DB_HOST? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 备份现有 .env 文件
    if [ -f .env ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo "✅ 已备份现有 .env 文件"
    fi
    
    # 更新或添加 DB_HOST
    if grep -q "^DB_HOST=" .env 2>/dev/null; then
        # 如果存在，更新它
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^DB_HOST=.*/DB_HOST=$RECOMMENDED_DB_HOST/" .env
        else
            # Linux
            sed -i "s/^DB_HOST=.*/DB_HOST=$RECOMMENDED_DB_HOST/" .env
        fi
        echo "✅ 已更新 DB_HOST=$RECOMMENDED_DB_HOST"
    else
        # 如果不存在，添加它
        echo "" >> .env
        echo "# 数据库配置" >> .env
        echo "DB_HOST=$RECOMMENDED_DB_HOST" >> .env
        echo "✅ 已添加 DB_HOST=$RECOMMENDED_DB_HOST"
    fi
    
    echo ""
    echo "6. 验证配置..."
    echo "----------------------------------------"
    echo "当前 .env 中的数据库配置："
    grep "^DB_" .env | sed 's/PASSWORD=.*/PASSWORD=***/'
    
    echo ""
    echo "✅ 配置完成！"
    echo ""
    echo "下一步："
    echo "1. 检查其他数据库配置（DB_PORT, DB_USER, DB_PASSWORD, DB_NAME）"
    echo "2. 重启 Docker 容器使配置生效："
    echo "   docker-compose -f docker-compose.prod.yml down"
    echo "   docker-compose -f docker-compose.prod.yml up -d"
    echo "3. 运行连接测试："
    echo "   ./check_db_connection.sh"
else
    echo "已取消，未修改配置"
    echo ""
    echo "手动设置方法："
    echo "1. 编辑 .env 文件："
    echo "   nano .env  # 或使用其他编辑器"
    echo ""
    echo "2. 添加或修改以下行："
    echo "   DB_HOST=$RECOMMENDED_DB_HOST"
    echo ""
    echo "3. 保存并重启容器"
fi

echo ""
echo "=========================================="

