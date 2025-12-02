FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/reminder-server

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 启动（生产环境）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "/var/log/reminder-server/access.log", "--error-logfile", "/var/log/reminder-server/error.log", "app:app"]

