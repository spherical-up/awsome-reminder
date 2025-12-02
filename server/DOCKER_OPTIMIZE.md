# Docker 部署优化指南

## 为什么 Docker 部署慢？

### 常见原因：

1. **网络问题**：从国外源下载依赖很慢
2. **没有使用缓存**：每次构建都重新安装所有依赖
3. **构建上下文太大**：复制了不必要的文件
4. **镜像层过多**：没有合并 RUN 命令

## 已优化的内容

### 1. 使用国内镜像源

**pip 镜像源（清华大学）：**
```dockerfile
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

**apt 镜像源（清华大学）：**
```dockerfile
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources
```

### 2. 优化 Dockerfile 层缓存

- 先复制 `requirements.txt`，再安装依赖
- 最后复制应用代码
- 这样代码变更时，依赖层可以复用缓存

### 3. 减少构建上下文

`.dockerignore` 已配置，排除：
- 日志文件
- 虚拟环境
- 测试文件
- 文档文件

### 4. 合并 RUN 命令

减少镜像层数，加快构建速度。

## 加速构建的方法

### 方法1：使用构建缓存

```bash
# 首次构建（会慢一些）
docker-compose build

# 后续构建（使用缓存，很快）
docker-compose build
```

### 方法2：只构建特定服务

```bash
docker-compose build reminder-server
```

### 方法3：使用预构建镜像

```bash
# 拉取基础镜像（提前下载）
docker pull python:3.9-slim

# 然后构建
docker-compose build
```

### 方法4：并行构建（如果有多个服务）

```bash
docker-compose build --parallel
```

## 构建时间对比

### 优化前：
- 首次构建：5-10 分钟
- 后续构建：3-5 分钟

### 优化后：
- 首次构建：2-3 分钟（使用国内镜像）
- 后续构建：10-30 秒（使用缓存）

## 进一步优化建议

### 1. 使用多阶段构建（可选）

如果镜像仍然很大，可以使用多阶段构建：

```dockerfile
# 构建阶段
FROM python:3.9-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt gunicorn

# 运行阶段
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "..."]
```

### 2. 使用 BuildKit（Docker 19.03+）

```bash
# 启用 BuildKit
export DOCKER_BUILDKIT=1
docker-compose build
```

### 3. 使用 .dockerignore 优化

确保 `.dockerignore` 包含所有不需要的文件。

### 4. 使用 Docker 缓存挂载（BuildKit）

```dockerfile
# 缓存 pip 下载
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

## 检查构建时间

```bash
# 查看构建时间
time docker-compose build

# 查看镜像大小
docker images | grep reminder-server
```

## 常见问题

### Q: 为什么首次构建还是很慢？

A: 首次构建需要下载基础镜像和所有依赖，这是正常的。后续构建会使用缓存，会快很多。

### Q: 如何清理缓存重新构建？

```bash
# 清理构建缓存
docker builder prune

# 不使用缓存重新构建
docker-compose build --no-cache
```

### Q: 如何查看构建过程？

```bash
# 显示详细构建日志
docker-compose build --progress=plain
```

## 性能优化检查清单

- [x] 使用国内镜像源
- [x] 优化 Dockerfile 层顺序
- [x] 配置 .dockerignore
- [x] 合并 RUN 命令
- [ ] 使用多阶段构建（可选）
- [ ] 启用 BuildKit（可选）

