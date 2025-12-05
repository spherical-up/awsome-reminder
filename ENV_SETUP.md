# 环境配置和启动指南

## 一、环境说明

### 1. 前端（小程序）环境

小程序环境由微信自动识别，无需手动配置：

- **开发版** (`develop`): 在微信开发者工具中运行
- **体验版** (`trial`): 上传为体验版后
- **正式版** (`release`): 发布到线上后

API 地址会根据环境自动切换（见 `miniprogram/utils/api.js`）

### 2. 后端（服务器）环境

后端通过不同的 Docker Compose 配置文件启动：

- **开发环境**: `docker-compose.yml`
- **生产环境**: `docker-compose.prod.yml`

---

## 二、开发环境启动

### 1. 启动后端服务

```bash
cd server

# 方式1: 使用开发环境配置（默认）
docker-compose up -d

# 方式2: 明确指定开发环境配置
docker-compose -f docker-compose.yml up -d
```

**开发环境特点**：
- 端口映射：`127.0.0.1:5001` + 局域网IP（如 `10.0.1.130:5001`）
- 代码热更新：挂载代码目录，修改代码无需重建镜像
- 无资源限制

### 2. 配置前端 API 地址

**自动模式（推荐）**：
- 在微信开发者工具中运行，自动使用开发环境 API
- API 地址：`http://10.0.1.130:5001/api`（根据当前 IP 自动调整）

**手动设置 IP**（如果 IP 变化）：
```javascript
// 在开发者工具控制台执行
const api = require('./utils/api.js')
api.setDevServerIP('新的IP地址')
```

**获取当前 IP**：
```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'
```

### 3. 验证服务

```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试 API
curl http://127.0.0.1:5001/api/health
```

---

## 三、生产环境启动

### 1. 启动后端服务

```bash
cd server

# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d
```

**生产环境特点**：
- 端口映射：仅 `127.0.0.1:5001`（通过 Nginx 反向代理）
- 代码不挂载：使用镜像中的代码（更安全）
- 资源限制：CPU 和内存限制

### 2. 配置 Nginx 反向代理（推荐）

**Nginx 配置示例**：

```nginx
server {
    listen 80;
    server_name www.6ht6.com;

    # HTTP 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.6ht6.com;

    # SSL 证书配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /api/health {
        proxy_pass http://127.0.0.1:5001/api/health;
        access_log off;
    }
}
```

### 3. 前端配置

**自动模式**：
- 正式版小程序自动使用生产环境 API
- API 地址：`https://www.6ht6.com/api`

**验证**：
- 在正式版小程序中，控制台会显示：`当前 API 地址: https://www.6ht6.com/api`

---

## 四、环境切换

### 从开发环境切换到生产环境

```bash
# 1. 停止开发环境
cd server
docker-compose down

# 2. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 3. 验证
docker-compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:5001/api/health
```

### 从生产环境切换到开发环境

```bash
# 1. 停止生产环境
cd server
docker-compose -f docker-compose.prod.yml down

# 2. 启动开发环境
docker-compose up -d

# 3. 验证
docker-compose ps
curl http://127.0.0.1:5001/api/health
```

---

## 五、常用命令

### 开发环境

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 查看日志
docker-compose logs -f

# 重启
docker-compose restart

# 查看状态
docker-compose ps

# 重建并启动
docker-compose up -d --build
```

### 生产环境

```bash
# 启动
docker-compose -f docker-compose.prod.yml up -d

# 停止
docker-compose -f docker-compose.prod.yml down

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 重启
docker-compose -f docker-compose.prod.yml restart

# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 重建并启动
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 六、环境变量配置

### 创建和配置 `.env` 文件

在 `server` 目录下创建 `.env` 文件：

**Linux 服务器快速配置**：
```bash
cd server

# 使用自动配置脚本（推荐）
./setup_db_host.sh

# 或手动配置
nano .env  # 或使用 vi/vim
```

```env
# 微信小程序配置
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=your-template-id

# 数据库配置
# ⚠️ 重要：根据运行环境设置正确的 DB_HOST
# 
# 开发环境（Docker）：
# DB_HOST=host.docker.internal  # macOS/Windows Docker Desktop
# DB_HOST=172.17.0.1            # Linux 系统（Docker 默认网关）
#
# 生产环境（Docker）：
# DB_HOST=host.docker.internal  # MySQL 在宿主机上（macOS/Windows）
# DB_HOST=172.17.0.1            # MySQL 在宿主机上（Linux）
# DB_HOST=mysql-server           # MySQL 在另一个 Docker 容器中（使用服务名）
# DB_HOST=192.168.1.100          # MySQL 在远程服务器上
#
# 本地开发（非 Docker）：
# DB_HOST=localhost

DB_HOST=host.docker.internal  # 默认值（Docker 环境）
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=reminder_db
```

**数据库主机配置说明**：

1. **MySQL 在宿主机上**（最常见）：
   - macOS/Windows Docker Desktop: `DB_HOST=host.docker.internal`
   - Linux 系统: `DB_HOST=172.17.0.1`（Docker 默认网关 IP）

2. **MySQL 在另一个 Docker 容器中**：
   - 使用 Docker Compose 服务名: `DB_HOST=mysql-server`（服务名）
   - 或使用 Docker 网络 IP

3. **MySQL 在远程服务器**：
   - 使用实际 IP 或域名: `DB_HOST=192.168.1.100`

**如何查找 Docker 网关 IP**（Linux 系统）：
```bash
# 方法1: 查看 Docker 网络
docker network inspect bridge | grep Gateway

# 方法2: 查看默认网关
ip route | grep default

# 方法3: 使用 host.docker.internal（如果支持）
# Docker Desktop 自动支持，Linux 需要配置 extra_hosts
```

---

## 七、故障排查

### 0. 数据库连接问题（常见）

**错误信息**：`Can't connect to MySQL server on 'localhost'`

**原因**：Docker 容器中 `localhost` 指向容器内部，无法访问宿主机的 MySQL。

**解决方案**：

1. **检查 `.env` 文件中的 `DB_HOST` 配置**：
   ```bash
   cd server
   cat .env | grep DB_HOST
   ```

2. **根据系统类型设置正确的 `DB_HOST`**：
   - **macOS/Windows**: `DB_HOST=host.docker.internal`
   - **Linux**: `DB_HOST=172.17.0.1` 或使用 `host.docker.internal`（需要配置 `extra_hosts`）

3. **验证数据库连接**：
   ```bash
   # 进入容器测试连接
   docker exec -it reminder-server bash
   
   # 在容器内测试连接
   python3 -c "
   import pymysql
   import os
   from dotenv import load_dotenv
   load_dotenv()
   try:
       conn = pymysql.connect(
           host=os.getenv('DB_HOST', 'host.docker.internal'),
           port=int(os.getenv('DB_PORT', 3306)),
           user=os.getenv('DB_USER', 'root'),
           password=os.getenv('DB_PASSWORD', ''),
           charset='utf8mb4'
       )
       print('✅ 数据库连接成功')
       conn.close()
   except Exception as e:
       print(f'❌ 数据库连接失败: {e}')
   "
   ```

4. **如果使用 Linux 且 `host.docker.internal` 不工作**：
   ```bash
   # 查找 Docker 网关 IP
   docker network inspect bridge | grep Gateway
   
   # 在 .env 中设置
   DB_HOST=172.17.0.1  # 替换为实际网关 IP
   ```

5. **重启容器使配置生效**：
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d
   ```

### 1. 检查环境是否正确

**前端**：
```javascript
// 在开发者工具控制台执行
const accountInfo = wx.getAccountInfoSync()
console.log('环境版本:', accountInfo.miniProgram.envVersion)
console.log('API 地址:', require('./utils/api.js').API_BASE_URL)
```

**后端**：
```bash
# 检查容器使用的配置文件
docker inspect reminder-server | grep -A 10 "Config"

# 检查端口映射
docker port reminder-server
```

### 2. 检查服务是否正常

```bash
# 健康检查
curl http://127.0.0.1:5001/api/health

# 查看日志
docker-compose logs --tail 50
```

### 3. 强制使用特定环境

**前端**（在 `miniprogram/utils/api.js` 中）：
```javascript
// 强制使用生产环境
const API_BASE_URL = 'https://www.6ht6.com/api'

// 强制使用开发环境
const API_BASE_URL = `http://${getLocalIP()}:5001/api`
```

**后端**：
```bash
# 明确指定配置文件
docker-compose -f docker-compose.yml up -d      # 开发环境
docker-compose -f docker-compose.prod.yml up -d # 生产环境
```

---

## 八、快速参考

| 环境 | 前端配置 | 后端启动命令 | API 地址 |
|------|---------|------------|---------|
| **开发环境** | 自动（开发者工具） | `docker-compose up -d` | `http://10.0.1.130:5001/api` |
| **生产环境** | 自动（正式版） | `docker-compose -f docker-compose.prod.yml up -d` | `https://www.6ht6.com/api` |

---

## 九、注意事项

1. **IP 地址变化**：
   - 开发环境 IP 变化时，需要更新 `docker-compose.yml` 中的端口映射
   - 前端可以通过 `api.setDevServerIP('新IP')` 动态设置

2. **环境变量**：
   - 确保 `.env` 文件配置正确
   - 生产环境建议使用环境变量管理敏感信息

3. **端口冲突**：
   - 开发环境使用 5001 端口（避免与 macOS AirPlay 冲突）
   - 生产环境通过 Nginx 反向代理，不直接暴露端口

4. **代码更新**：
   - 开发环境：代码修改后无需重建，直接生效
   - 生产环境：需要重建镜像：`docker-compose -f docker-compose.prod.yml up -d --build`

