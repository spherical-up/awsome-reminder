FROM python:3.9-slim

WORKDIR /app

# 设置环境变量（加速 pip 安装，使用国内镜像）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_DEFAULT_TIMEOUT=100

# 安装系统依赖（合并命令减少层数，使用国内镜像源）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .

# 安装 Python 依赖（使用国内镜像，缓存 pip 缓存）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码（放在最后，代码变更时不影响依赖层缓存）
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/reminder-server

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 启动（生产环境）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "/var/log/reminder-server/access.log", "--error-logfile", "/var/log/reminder-server/error.log", "app:app"]

