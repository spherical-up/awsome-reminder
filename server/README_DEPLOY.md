# 部署说明

## 开发环境

使用 `docker-compose.yml`：

```bash
# 1. 更新 IP 地址（如果变化）
# 编辑 docker-compose.yml，更新第12行的IP地址
# 获取当前IP: ipconfig getifaddr en0 (macOS) 或 hostname -I (Linux)

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

## 生产环境

### 方式1：使用生产环境配置（推荐）

```bash
# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

**特点**：
- 只绑定到 `127.0.0.1`，更安全
- 通过 Nginx 反向代理对外提供服务
- 不挂载代码目录，使用镜像中的代码
- 限制资源使用

### 方式2：使用 Nginx 反向代理（推荐用于生产环境）

1. **修改 docker-compose.prod.yml**：
   - 端口映射改为 `127.0.0.1:5001:5001`（仅本地访问）

2. **配置 Nginx**：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **使用 HTTPS**（推荐）：
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 方式3：直接暴露端口（不推荐，仅用于测试）

如果需要直接暴露端口（不推荐用于生产环境）：

```yaml
ports:
  - "0.0.0.0:5001:5001"  # 绑定所有网络接口
```

**注意**：
- 需要配置防火墙规则
- 建议使用 HTTPS
- 考虑使用 Nginx 反向代理

## 环境变量配置

创建 `.env` 文件：

```env
# 微信小程序配置
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=your-template-id

# 数据库配置
DB_HOST=host.docker.internal  # Docker 环境
# DB_HOST=localhost  # 本地环境
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=reminder_db
```

## 常用命令

```bash
# 开发环境
docker-compose up -d              # 启动
docker-compose down               # 停止
docker-compose logs -f            # 查看日志
docker-compose restart            # 重启

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml restart
```

## 更新服务

```bash
# 开发环境
docker-compose down
docker-compose build
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

