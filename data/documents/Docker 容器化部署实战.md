# Docker 容器化部署实战

> 来源: 本地生成

# Docker 容器化部署实战

## 1. Dockerfile 最佳实践

### 多阶段构建
```dockerfile
# 构建阶段
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o /app/server

# 运行阶段
FROM alpine:3.19
COPY --from=builder /app/server /server
CMD ["/server"]
```

### 优化建议
- 使用 .dockerignore 排除无用文件
- 合并 RUN 命令减少层数
- 使用特定版本的基础镜像
- 非 root 用户运行

## 2. Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=mysql
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_DATABASE: appdb
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mysql_data:
```

## 3. 网络模式

- **bridge**：默认桥接网络
- **host**：使用宿主机网络
- **overlay**：跨主机通信（Swarm）
- **none**：无网络

## 4. 资源限制

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

## 5. 日志管理

```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```