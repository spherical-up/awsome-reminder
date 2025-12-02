# 服务端线上部署指南

## 一、部署方案选择

### 方案1：云服务器部署（推荐）

**适合场景：** 需要完全控制，适合长期运营

**推荐平台：**
- 阿里云 ECS
- 腾讯云 CVM
- 华为云 ECS
- AWS EC2

**优点：**
- 完全控制
- 可扩展性强
- 成本可控

### 方案2：云函数/Serverless

**适合场景：** 快速部署，按量付费

**推荐平台：**
- 腾讯云函数（SCF）
- 阿里云函数计算
- 微信云开发

**优点：**
- 无需管理服务器
- 自动扩缩容
- 按量计费

### 方案3：容器化部署

**适合场景：** 需要高可用、多实例

**推荐平台：**
- Docker + 云服务器
- Kubernetes
- 阿里云容器服务

## 二、云服务器部署详细步骤

### 1. 购买和配置服务器

#### 1.1 选择服务器配置

**最低配置：**
- CPU: 1核
- 内存: 1GB
- 带宽: 1Mbps
- 系统: Ubuntu 20.04 / CentOS 7

**推荐配置：**
- CPU: 2核
- 内存: 2GB
- 带宽: 3Mbps
- 系统: Ubuntu 20.04

#### 1.2 安全组配置

开放以下端口：
- **22** (SSH)
- **80** (HTTP)
- **443** (HTTPS)
- **5000** (应用端口，可选)

### 2. 服务器环境准备

#### 2.1 连接服务器

```bash
ssh root@your-server-ip
```

#### 2.2 更新系统

```bash
# Ubuntu
apt update && apt upgrade -y

# CentOS
yum update -y
```

#### 2.3 安装 Python 和依赖

```bash
# Ubuntu
apt install python3 python3-pip python3-venv -y

# CentOS
yum install python3 python3-pip -y
```

#### 2.4 安装 Nginx（用于反向代理和HTTPS）

```bash
# Ubuntu
apt install nginx -y

# CentOS
yum install nginx -y
```

### 3. 部署应用

#### 3.1 上传代码到服务器

**方法1：使用 Git**

```bash
# 在服务器上
cd /opt
git clone your-repo-url reminder-server
cd reminder-server/server
```

**方法2：使用 SCP**

```bash
# 在本地电脑
scp -r server root@your-server-ip:/opt/reminder-server
```

**方法3：使用 FTP/SFTP 工具**
- FileZilla
- WinSCP
- VS Code Remote

#### 3.2 创建虚拟环境

```bash
cd /opt/reminder-server/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3.3 配置环境变量

```bash
# 创建 .env 文件
nano .env
```

内容：
```env
WX_APPID=你的小程序AppID
WX_APPSECRET=你的小程序AppSecret
WX_TEMPLATE_ID=_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w
FLASK_ENV=production
```

#### 3.4 测试运行

```bash
python app.py
```

如果看到启动信息，说明配置正确。按 `Ctrl+C` 停止。

### 4. 配置进程管理（使用 Supervisor）

#### 4.1 安装 Supervisor

```bash
apt install supervisor -y  # Ubuntu
# 或
yum install supervisor -y  # CentOS
```

#### 4.2 创建配置文件

```bash
nano /etc/supervisor/conf.d/reminder-server.conf
```

内容：
```ini
[program:reminder-server]
command=/opt/reminder-server/server/venv/bin/python /opt/reminder-server/server/app.py
directory=/opt/reminder-server/server
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/reminder-server/error.log
stdout_logfile=/var/log/reminder-server/access.log
environment=FLASK_ENV="production"
```

#### 4.3 创建日志目录

```bash
mkdir -p /var/log/reminder-server
```

#### 4.4 启动服务

```bash
supervisorctl reread
supervisorctl update
supervisorctl start reminder-server
supervisorctl status
```

### 5. 配置 Nginx 反向代理

#### 5.1 创建 Nginx 配置

```bash
nano /etc/nginx/sites-available/reminder-server
```

内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 5.2 启用配置

```bash
# Ubuntu
ln -s /etc/nginx/sites-available/reminder-server /etc/nginx/sites-enabled/

# CentOS (配置文件在 /etc/nginx/conf.d/)
# 直接创建文件即可
```

#### 5.3 测试并重启 Nginx

```bash
nginx -t
systemctl restart nginx
systemctl enable nginx
```

### 6. 配置 HTTPS（必需）

微信小程序要求使用 HTTPS。

#### 6.1 安装 Certbot

```bash
# Ubuntu
apt install certbot python3-certbot-nginx -y

# CentOS
yum install certbot python3-certbot-nginx -y
```

#### 6.2 申请 SSL 证书

```bash
certbot --nginx -d your-domain.com
```

按提示操作，证书会自动配置。

#### 6.3 自动续期

证书有效期 90 天，设置自动续期：

```bash
certbot renew --dry-run
```

添加到 crontab：
```bash
crontab -e
# 添加以下行
0 0 * * * certbot renew --quiet
```

### 7. 修改应用配置

#### 7.1 修改 app.py 生产环境配置

```python
if __name__ == '__main__':
    # 生产环境不直接运行，由 Supervisor 管理
    # app.run(host='0.0.0.0', port=5000, debug=True)
    pass
```

#### 7.2 使用 Gunicorn（推荐）

安装 Gunicorn：
```bash
pip install gunicorn
```

修改 Supervisor 配置：
```ini
[program:reminder-server]
command=/opt/reminder-server/server/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
directory=/opt/reminder-server/server
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/reminder-server/error.log
stdout_logfile=/var/log/reminder-server/access.log
environment=FLASK_ENV="production"
```

### 8. 更新小程序配置

#### 8.1 修改 API 地址

编辑 `utils/api.js`：

```javascript
// 生产环境
const API_BASE_URL = 'https://your-domain.com/api'
```

#### 8.2 配置服务器域名

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入 **开发** -> **开发管理** -> **开发设置**
3. 在 **服务器域名** 中添加：
   - request合法域名: `https://your-domain.com`
   - uploadFile合法域名: `https://your-domain.com`
   - downloadFile合法域名: `https://your-domain.com`

## 三、使用 Gunicorn 部署（推荐）

### 1. 安装 Gunicorn

```bash
cd /opt/reminder-server/server
source venv/bin/activate
pip install gunicorn
```

### 2. 创建 Gunicorn 配置文件

```bash
nano /opt/reminder-server/server/gunicorn_config.py
```

内容：
```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/reminder-server/access.log"
errorlog = "/var/log/reminder-server/error.log"
loglevel = "info"
```

### 3. 更新 Supervisor 配置

```ini
[program:reminder-server]
command=/opt/reminder-server/server/venv/bin/gunicorn -c /opt/reminder-server/server/gunicorn_config.py app:app
directory=/opt/reminder-server/server
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/reminder-server/error.log
stdout_logfile=/var/log/reminder-server/access.log
environment=FLASK_ENV="production"
```

### 4. 重启服务

```bash
supervisorctl restart reminder-server
```

## 四、使用 Docker 部署（可选）

### 1. 创建 Dockerfile

```bash
nano /opt/reminder-server/server/Dockerfile
```

内容：
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  reminder-server:
    build: .
    ports:
      - "5000:5000"
    environment:
      - WX_APPID=${WX_APPID}
      - WX_APPSECRET=${WX_APPSECRET}
      - WX_TEMPLATE_ID=${WX_TEMPLATE_ID}
    volumes:
      - ./logs:/var/log/reminder-server
    restart: always
```

### 3. 构建和运行

```bash
docker-compose up -d
```

## 五、数据库配置（生产环境推荐）

### 1. 安装 MySQL/PostgreSQL

```bash
# MySQL
apt install mysql-server -y

# PostgreSQL
apt install postgresql postgresql-contrib -y
```

### 2. 修改 app.py 使用数据库

参考 `server/README.md` 中的数据库配置说明。

## 六、监控和日志

### 1. 查看日志

```bash
# Supervisor 日志
tail -f /var/log/reminder-server/access.log
tail -f /var/log/reminder-server/error.log

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Supervisor 状态
supervisorctl status reminder-server
```

### 2. 设置日志轮转

```bash
nano /etc/logrotate.d/reminder-server
```

内容：
```
/var/log/reminder-server/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
}
```

## 七、安全加固

### 1. 防火墙配置

```bash
# Ubuntu (UFW)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### 2. 禁用 root 登录（可选）

```bash
# 创建新用户
adduser deploy
usermod -aG sudo deploy

# 配置 SSH 密钥登录
# 编辑 /etc/ssh/sshd_config
# PermitRootLogin no
```

### 3. 定期更新

```bash
# 设置自动更新
apt install unattended-upgrades -y  # Ubuntu
```

## 八、快速部署脚本

创建 `deploy.sh`：

```bash
#!/bin/bash

echo "开始部署..."

# 1. 更新代码
cd /opt/reminder-server/server
git pull

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 重启服务
supervisorctl restart reminder-server

# 5. 检查状态
supervisorctl status reminder-server

echo "部署完成！"
```

使用：
```bash
chmod +x deploy.sh
./deploy.sh
```

## 九、测试部署

### 1. 测试服务是否运行

```bash
curl http://localhost:5000/api/health
```

### 2. 测试 HTTPS

```bash
curl https://your-domain.com/api/health
```

### 3. 在小程序中测试

1. 更新 `utils/api.js` 中的地址
2. 配置服务器域名
3. 测试创建提醒功能

## 十、常见问题

### 问题1：502 Bad Gateway

**原因：** 应用未启动或端口不对

**解决：**
```bash
supervisorctl status reminder-server
supervisorctl restart reminder-server
```

### 问题2：SSL 证书问题

**解决：**
```bash
certbot renew
nginx -t
systemctl restart nginx
```

### 问题3：定时任务不执行

**检查：**
```bash
# 查看进程
ps aux | grep python
ps aux | grep gunicorn

# 查看日志
tail -f /var/log/reminder-server/error.log
```

## 十一、成本估算

### 云服务器（阿里云/腾讯云）

- **最低配置：** 约 50-100元/月
- **推荐配置：** 约 100-200元/月
- **域名：** 约 50-100元/年
- **SSL证书：** Let's Encrypt 免费

### 总成本

- **初期：** 约 100-200元/月
- **包含：** 服务器 + 域名 + SSL

## 十二、部署检查清单

- [ ] 服务器已购买并配置
- [ ] 代码已上传到服务器
- [ ] Python 环境已配置
- [ ] 依赖已安装
- [ ] 环境变量已配置
- [ ] Supervisor 已配置并启动
- [ ] Nginx 已配置并启动
- [ ] SSL 证书已申请并配置
- [ ] 域名已解析
- [ ] 防火墙已配置
- [ ] 小程序服务器域名已配置
- [ ] API 地址已更新
- [ ] 功能测试通过

完成以上步骤后，你的服务就可以在线上运行了！🎉

