# Gunicorn 配置文件
import multiprocessing

# 服务器socket
bind = "127.0.0.1:5000"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时时间
timeout = 120

# 保持连接
keepalive = 5

# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 日志配置
accesslog = "/var/log/reminder-server/access.log"
errorlog = "/var/log/reminder-server/error.log"
loglevel = "info"

# 进程名称
proc_name = "reminder-server"

# 守护进程（由 Supervisor 管理，不需要守护）
daemon = False

