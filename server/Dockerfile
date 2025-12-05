FROM python:3.9-slim

WORKDIR /app

# 设置环境变量（加速 pip 安装，使用国内镜像）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_DEFAULT_TIMEOUT=100

# 安装系统依赖（合并命令减少层数，使用国内镜像源）
# 配置镜像源并添加重试机制以提高可靠性
RUN set -x; \
    # 替换主源文件
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list 2>/dev/null || true; \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list 2>/dev/null || true; \
    # 替换 sources.list.d 中的文件
    if [ -d /etc/apt/sources.list.d ]; then \
        find /etc/apt/sources.list.d -name "*.sources" -exec sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' {} \; 2>/dev/null || true; \
        find /etc/apt/sources.list.d -name "*.sources" -exec sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' {} \; 2>/dev/null || true; \
    fi; \
    # 清理并更新，带重试机制
    apt-get clean; \
    for i in 1 2 3; do \
        apt-get update --fix-missing && break || sleep 5; \
    done; \
    # 安装依赖，带重试机制
    for i in 1 2 3; do \
        apt-get install -y --no-install-recommends --fix-missing gcc curl && break || sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .

# 安装 Python 依赖（使用国内镜像，缓存 pip 缓存）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# 复制应用代码（放在最后，代码变更时不影响依赖层缓存）
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/reminder-server

# 暴露端口（使用5001避免与macOS AirPlay冲突）
EXPOSE 5001

# 使用 Gunicorn 启动（生产环境）
# 日志输出到标准输出（-），方便 docker compose logs 查看
# 如果需要保存日志文件，可以通过 Docker 日志驱动或挂载卷来保存
CMD ["gunicorn", "--preload", "-w", "4", "-b", "0.0.0.0:5001", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--log-level", "info", "app:app"]

