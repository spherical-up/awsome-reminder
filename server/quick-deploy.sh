#!/bin/bash

# 快速部署脚本（Docker）
# 使用方法: ./quick-deploy.sh

set -e

echo "=========================================="
echo "Docker 快速部署脚本"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，请先创建并配置"
    echo "示例:"
    echo "WX_APPID=your-appid"
    echo "WX_APPSECRET=your-appsecret"
    echo "WX_TEMPLATE_ID=_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w"
    exit 1
fi

# 停止旧容器
echo "1. 停止旧容器..."
docker-compose down

# 构建新镜像
echo "2. 构建新镜像..."
docker-compose build

# 启动容器
echo "3. 启动容器..."
docker-compose up -d

# 等待服务启动
echo "4. 等待服务启动..."
sleep 5

# 检查状态
echo "5. 检查服务状态..."
docker-compose ps

# 测试健康检查
echo "6. 测试服务..."
if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✓ 服务运行正常"
else
    echo "✗ 服务可能未正常启动，请查看日志: docker-compose logs"
fi

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"

