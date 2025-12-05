# Linux 服务器数据库配置指南

## 一、快速配置（推荐）

### 使用自动配置脚本

```bash
cd server
chmod +x setup_db_host.sh
./setup_db_host.sh
```

脚本会自动：
1. 检测 Docker 网关 IP
2. 检测 MySQL 服务位置
3. 推荐最佳配置
4. 自动更新 `.env` 文件

---

## 二、手动配置

### 1. 查找 Docker 网关 IP

```bash
# 方法1: 查看 Docker 默认网络网关（推荐）
docker network inspect bridge | grep Gateway

# 输出示例：
# "Gateway": "172.17.0.1"

# 方法2: 查看默认路由
ip route | grep default

# 方法3: 查看 Docker 网络详情
docker network inspect bridge
```

### 2. 确定 MySQL 服务位置

#### 情况 A: MySQL 在宿主机上（最常见）

```bash
# 检查 MySQL 是否在宿主机运行
systemctl status mysql
# 或
systemctl status mysqld
# 或
systemctl status mariadb
```

**配置方式**：
```bash
# 编辑 .env 文件
cd server
nano .env  # 或使用 vi/vim

# 添加或修改以下配置
DB_HOST=172.17.0.1  # 使用步骤1中找到的网关IP
# 或
DB_HOST=host.docker.internal  # 如果已配置 extra_hosts
```

#### 情况 B: MySQL 在另一个 Docker 容器中

```bash
# 查看 MySQL 容器
docker ps | grep mysql

# 获取容器 IP
docker inspect <mysql-container-name> | grep IPAddress
```

**配置方式**：
```bash
# 如果使用 Docker Compose，使用服务名（推荐）
DB_HOST=mysql  # 或实际的 MySQL 服务名

# 如果使用独立容器，使用容器 IP
DB_HOST=172.18.0.2  # 替换为实际 IP
```

#### 情况 C: MySQL 在远程服务器

```bash
# 直接使用远程服务器 IP 或域名
DB_HOST=192.168.1.100  # 远程服务器 IP
# 或
DB_HOST=mysql.example.com  # 远程服务器域名
```

---

## 三、完整 .env 文件示例

### MySQL 在宿主机上

```env
# 微信小程序配置
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=your-template-id

# 数据库配置
DB_HOST=172.17.0.1  # Docker 网关 IP（从宿主机访问）
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=reminder_db
```

### MySQL 在 Docker Compose 网络中

```env
# 微信小程序配置
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=your-template-id

# 数据库配置
DB_HOST=mysql  # Docker Compose 服务名
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=reminder_db
```

### MySQL 在远程服务器

```env
# 微信小程序配置
WX_APPID=your-appid
WX_APPSECRET=your-appsecret
WX_TEMPLATE_ID=your-template-id

# 数据库配置
DB_HOST=192.168.1.100  # 远程服务器 IP
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=reminder_db
```

---

## 四、验证配置

### 1. 检查 .env 文件

```bash
cd server
cat .env | grep DB_HOST
```

### 2. 测试数据库连接

```bash
# 使用诊断脚本
./check_db_connection.sh

# 或手动测试
docker exec reminder-server python3 << EOF
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        charset='utf8mb4',
        connect_timeout=5
    )
    print("✅ 数据库连接成功！")
    conn.close()
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
EOF
```

### 3. 重启容器使配置生效

```bash
# 开发环境
docker-compose down
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 五、常见问题

### 问题 1: 连接被拒绝 (Connection refused)

**原因**：`DB_HOST` 配置错误或 MySQL 未运行

**解决方案**：
```bash
# 1. 检查 MySQL 是否运行
systemctl status mysql

# 2. 检查 MySQL 监听地址
netstat -tlnp | grep 3306
# 或
ss -tlnp | grep 3306

# 3. 如果 MySQL 只监听 127.0.0.1，需要修改配置
# 编辑 /etc/mysql/mysql.conf.d/mysqld.cnf
# 将 bind-address = 127.0.0.1 改为 bind-address = 0.0.0.0
# 然后重启 MySQL: systemctl restart mysql
```

### 问题 2: 无法解析 host.docker.internal

**原因**：Linux 系统默认不支持 `host.docker.internal`

**解决方案**：
```bash
# 方案 A: 使用 Docker 网关 IP（推荐）
DB_HOST=172.17.0.1

# 方案 B: 在 docker-compose.yml 中配置 extra_hosts
# docker-compose.yml 中已有此配置，确保使用即可
```

### 问题 3: 权限被拒绝 (Access denied)

**原因**：MySQL 用户权限配置问题

**解决方案**：
```bash
# 1. 登录 MySQL
mysql -u root -p

# 2. 检查用户权限
SELECT user, host FROM mysql.user WHERE user='root';

# 3. 如果需要，创建允许从 Docker 网络访问的用户
CREATE USER 'root'@'172.17.%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON reminder_db.* TO 'root'@'172.17.%';
FLUSH PRIVILEGES;

# 或允许所有 IP（不推荐，仅用于开发）
GRANT ALL PRIVILEGES ON reminder_db.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

### 问题 4: 防火墙阻止连接

**原因**：防火墙规则阻止了数据库连接

**解决方案**：
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 3306/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=3306/tcp
sudo firewall-cmd --reload

# 或临时关闭防火墙测试（不推荐用于生产环境）
sudo systemctl stop ufw  # Ubuntu/Debian
sudo systemctl stop firewalld  # CentOS/RHEL
```

---

## 六、安全建议

1. **不要使用 root 用户**：
   ```sql
   CREATE USER 'reminder_user'@'172.17.%' IDENTIFIED BY 'strong-password';
   GRANT ALL PRIVILEGES ON reminder_db.* TO 'reminder_user'@'172.17.%';
   FLUSH PRIVILEGES;
   ```

2. **限制访问 IP**：
   - 只允许 Docker 网络段访问：`172.17.%`
   - 不要使用 `%`（允许所有 IP）

3. **使用强密码**：
   - 在 `.env` 文件中使用强密码
   - 确保 `.env` 文件权限：`chmod 600 .env`

4. **定期备份**：
   ```bash
   # 备份数据库
   mysqldump -u root -p reminder_db > backup_$(date +%Y%m%d).sql
   ```

---

## 七、快速命令参考

```bash
# 查找 Docker 网关 IP
docker network inspect bridge | grep Gateway

# 检查 MySQL 状态
systemctl status mysql

# 检查 MySQL 端口
netstat -tlnp | grep 3306

# 测试数据库连接
docker exec reminder-server python3 -c "
import pymysql, os
from dotenv import load_dotenv
load_dotenv()
conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    charset='utf8mb4'
)
print('✅ 连接成功')
conn.close()
"

# 查看容器日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 八、总结

**推荐配置流程**：

1. 运行自动配置脚本：`./setup_db_host.sh`
2. 检查配置：`cat .env | grep DB_HOST`
3. 测试连接：`./check_db_connection.sh`
4. 重启容器：`docker-compose -f docker-compose.prod.yml up -d`
5. 查看日志：`docker-compose -f docker-compose.prod.yml logs -f`

**常见配置值**：
- MySQL 在宿主机：`DB_HOST=172.17.0.1`
- MySQL 在 Docker Compose：`DB_HOST=mysql`（服务名）
- MySQL 在远程服务器：`DB_HOST=192.168.1.100`（实际 IP）

