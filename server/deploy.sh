#!/bin/bash

# 部署脚本
# 使用方法: ./deploy.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始部署提醒服务..."
echo "=========================================="

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否在正确的目录
if [ ! -f "app.py" ]; then
    echo -e "${RED}错误: 请在 server 目录下运行此脚本${NC}"
    exit 1
fi

# 1. 激活虚拟环境
echo "1. 激活虚拟环境..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}错误: 虚拟环境不存在，请先创建: python3 -m venv venv${NC}"
    exit 1
fi

# 2. 更新依赖
echo "2. 安装/更新依赖..."
pip install -r requirements.txt --upgrade

# 3. 检查环境变量
echo "3. 检查环境变量..."
if [ ! -f ".env" ]; then
    echo -e "${RED}警告: .env 文件不存在，请创建并配置环境变量${NC}"
else
    echo -e "${GREEN}✓ .env 文件存在${NC}"
fi

# 4. 测试应用
echo "4. 测试应用配置..."
python -c "from app import app; print('应用配置正确')" || {
    echo -e "${RED}错误: 应用配置有问题${NC}"
    exit 1
}

# 5. 重启服务（如果使用 Supervisor）
if command -v supervisorctl &> /dev/null; then
    echo "5. 重启 Supervisor 服务..."
    supervisorctl restart reminder-server || {
        echo -e "${RED}警告: Supervisor 服务重启失败，请手动检查${NC}"
    }
else
    echo "5. 跳过 Supervisor（未安装）"
fi

# 6. 检查服务状态
echo "6. 检查服务状态..."
sleep 2
if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务运行正常${NC}"
else
    echo -e "${RED}警告: 服务可能未启动，请检查${NC}"
fi

echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 检查服务日志: tail -f /var/log/reminder-server/access.log"
echo "2. 测试接口: curl http://localhost:5000/api/health"
echo "3. 更新小程序配置中的 API 地址"

