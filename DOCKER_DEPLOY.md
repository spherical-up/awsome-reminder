# Docker 部署指南（阿里云）

## 一、准备工作

### 1. 阿里云服务器配置

- **系统：** Ubuntu 20.04 或 CentOS 7
- **配置：** 1核2G 起步（约 50-100元/月）
- **安全组：** 开放端口 22, 80, 443

### 2. 域名准备

- 购买域名（如：阿里云域名）
- 解析域名到服务器IP

## 二、服务器环境准备

### 1. 连接服务器

```bash
ssh root@your-server-ip
```

### 2. 安装 Docker 和 Docker Compose

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 3. 安装 Nginx（用于 HTTPS）

```bash
apt update && apt install nginx certbot python3-certbot-nginx -y  # Ubuntu
# 或
yum install nginx certbot python3-certbot-nginx -y  # CentOS
```

## 三、部署应用

### 1. 上传代码到服务器

```bash
# 方法1：使用 Git
cd /opt
git clone your-repo-url reminder-server
cd reminder-server/server

# 方法2：使用 SCP（在本地执行）
scp -r server root@your-server-ip:/opt/reminder-server/
```

### 2. 配置环境变量

```bash
cd /opt/reminder-server/server
nano .env
```

内容：
```env
WX_APPID=你的小程序AppID
WX_APPSECRET=你的小程序AppSecret
WX_TEMPLATE_ID=_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w
FLASK_ENV=production
```

### 3. 构建和启动容器

```bash
cd /opt/reminder-server/server
docker-compose up -d
```

### 4. 查看运行状态

```bash
docker-compose ps
docker-compose logs -f
```

## 四、配置 Nginx 和 HTTPS

### 1. 创建 Nginx 配置

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

### 2. 启用配置

```bash
# Ubuntu
ln -s /etc/nginx/sites-available/reminder-server /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# CentOS（配置文件在 /etc/nginx/conf.d/）
cp /etc/nginx/sites-available/reminder-server /etc/nginx/conf.d/reminder-server.conf
nginx -t
systemctl restart nginx
```

### 3. 申请 SSL 证书

```bash
certbot --nginx -d your-domain.com
```

按提示操作，证书会自动配置。

## 五、更新小程序配置

### 1. 修改 API 地址

编辑 `utils/api.js`：

```javascript
// 生产环境
const API_BASE_URL = 'https://your-domain.com/api'
```

### 2. 配置服务器域名

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入 **开发** -> **开发管理** -> **开发设置**
3. 在 **服务器域名** 中添加：
   - request合法域名: `https://your-domain.com`

## 六、常用命令

### 查看日志

```bash
# 容器日志
docker-compose logs -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 重启服务

```bash
cd /opt/reminder-server/server
docker-compose restart
```

### 更新代码

```bash
cd /opt/reminder-server/server
git pull  # 或重新上传代码
docker-compose down
docker-compose up -d --build
```

### 停止服务

```bash
docker-compose down
```

## 七、测试

### 1. 测试服务

```bash
# 本地测试
curl http://localhost:5000/api/health

# 外网测试
curl https://your-domain.com/api/health
```

### 2. 在小程序中测试

1. 更新 `utils/api.js` 中的地址
2. 配置服务器域名
3. 测试创建提醒功能

## 八、故障排查

### 容器无法启动

```bash
# 查看日志
docker-compose logs

# 检查配置
docker-compose config
```

### 502 Bad Gateway

```bash
# 检查容器是否运行
docker-compose ps

# 检查端口
netstat -tlnp | grep 5000
```

### SSL 证书问题

```bash
# 续期证书
certbot renew

# 测试续期
certbot renew --dry-run
```

## 九、一键部署脚本

创建 `quick-deploy.sh`：

```bash
#!/bin/bash

echo "开始部署..."

# 1. 进入目录
cd /opt/reminder-server/server

# 2. 停止旧容器
docker-compose down

# 3. 更新代码（如果使用 Git）
# git pull

# 4. 重新构建和启动
docker-compose up -d --build

# 5. 检查状态
docker-compose ps

echo "部署完成！"
```

使用：
```bash
chmod +x quick-deploy.sh
./quick-deploy.sh
```

## 十、检查清单

- [ ] 服务器已购买并配置
- [ ] Docker 和 Docker Compose 已安装
- [ ] 代码已上传到服务器
- [ ] `.env` 文件已配置
- [ ] 容器已启动（`docker-compose ps`）
- [ ] Nginx 已配置
- [ ] SSL 证书已申请
- [ ] 域名已解析
- [ ] 小程序服务器域名已配置
- [ ] API 地址已更新
- [ ] 功能测试通过

完成！🎉

