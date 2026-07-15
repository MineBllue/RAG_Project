#!/usr/bin/env python3
"""
数据爬取脚本 - 爬取技术文档和图片
来源：公开技术文档站点
"""
import os
import sys
import json
import time
import hashlib
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

DATA_DIR = Path(__file__).parent.parent / "data"
DOC_DIR = DATA_DIR / "documents"
IMG_DIR = DATA_DIR / "images"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ===== 技术文档爬取源 =====
DOC_SOURCES = [
    # Kubernetes 官方中文文档
    {
        "name": "k8s-docs",
        "base": "https://kubernetes.io/zh-cn/docs/",
        "urls": [
            "https://kubernetes.io/zh-cn/docs/concepts/overview/",
            "https://kubernetes.io/zh-cn/docs/concepts/architecture/",
            "https://kubernetes.io/zh-cn/docs/concepts/workloads/pods/",
            "https://kubernetes.io/zh-cn/docs/concepts/services-networking/service/",
            "https://kubernetes.io/zh-cn/docs/concepts/storage/volumes/",
            "https://kubernetes.io/zh-cn/docs/concepts/configuration/configmap/",
            "https://kubernetes.io/zh-cn/docs/concepts/security/overview/",
        ],
    },
]

# 备用：本地生成一些高质量技术文档
EXTRA_DOCS = [
    {
        "title": "微服务架构设计最佳实践",
        "content": """# 微服务架构设计最佳实践

## 1. 服务拆分原则

微服务拆分应遵循单一职责原则（SRP），每个服务只负责一个业务领域。

### 1.1 按业务能力拆分
- 订单服务：负责订单创建、查询、状态管理
- 用户服务：负责用户注册、登录、权限管理
- 商品服务：负责商品信息、库存管理
- 支付服务：负责支付流程、退款处理

### 1.2 按领域驱动设计（DDD）
使用限界上下文（Bounded Context）划分服务边界。每个限界上下文拥有独立的数据存储和业务逻辑。

## 2. 服务间通信

### 2.1 同步通信
- **RESTful API**：适用于对外暴露的接口，简单通用，基于 HTTP 协议
- **gRPC**：基于 HTTP/2 的高性能 RPC 框架，支持双向流式通信，性能比 REST 高 3-7 倍

### 2.2 异步通信
- **Apache Kafka**：高吞吐量的分布式消息队列，百万条/秒级别
- **RabbitMQ**：低延迟消息代理，适合实时业务场景
- **消息模式**：发布/订阅、点对点、请求/响应

## 3. 数据管理

### 3.1 数据库选型
| 类型 | 代表产品 | 适用场景 |
|------|---------|---------|
| 关系型 | MySQL/PostgreSQL | 事务性业务 |
| 文档型 | MongoDB | 灵活 Schema |
| 键值型 | Redis | 缓存/会话 |
| 列族型 | Cassandra | 时序数据 |
| 图数据库 | Neo4j | 关系分析 |

### 3.2 Saga 分布式事务
- 编排式 Saga：由协调器管理事务流程
- 编排式 Saga：事件驱动，各服务独立决策

## 4. 服务治理

### 4.1 API 网关
- 统一入口、路由转发
- 认证鉴权、限流熔断
- 请求聚合、协议转换

### 4.2 服务注册与发现
- Consul、Eureka、Nacos
- 健康检查、心跳机制
- 客户端发现 vs 服务端发现

### 4.3 配置管理
- 配置中心集中管理
- 动态刷新、版本管理
- 多环境隔离

## 5. 可观测性

### 5.1 日志
- ELK Stack（Elasticsearch + Logstash + Kibana）
- 结构化日志、链路追踪 ID

### 5.2 监控
- Prometheus + Grafana
- 指标采集、告警规则

### 5.3 链路追踪
- Jaeger/Zipkin
- OpenTelemetry 标准""",
    },
    {
        "title": "Kubernetes 核心概念详解",
        "content": """# Kubernetes 核心概念详解

## 1. Pod

Pod 是 Kubernetes 的最小部署单元，包含一个或多个容器。

### 特征
- 共享网络命名空间（共享 IP 和端口空间）
- 共享存储卷
- 生命周期绑定

### 配置示例
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.21
    ports:
    - containerPort: 80
```

## 2. Service

Service 定义了一组 Pod 的访问策略。

### 类型
- **ClusterIP**：集群内部访问（默认）
- **NodePort**：通过节点端口暴露
- **LoadBalancer**：使用云厂商负载均衡器
- **ExternalName**：DNS CNAME 映射

## 3. Deployment

管理 Pod 的声明式更新，支持滚动更新和回滚。

### 核心功能
- 副本集管理
- 滚动更新策略（maxSurge/maxUnavailable）
- 版本回滚（kubectl rollout undo）
- 暂停/恢复发布

## 4. ConfigMap & Secret

将配置与镜像解耦。

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "mysql://db:3306/mydb"
  log_level: "info"
```

### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: <base64-encoded>
```

## 5. Ingress

管理集群外部 HTTP/HTTPS 路由。

### 功能
- 基于域名和路径的路由
- TLS/SSL 终止
- 负载均衡

## 6. 持久化存储

- **PV（PersistentVolume）**：集群存储资源
- **PVC（PersistentVolumeClaim）**：存储请求
- **StorageClass**：动态存储供应""",
    },
    {
        "title": "Redis 缓存最佳实践",
        "content": """# Redis 缓存最佳实践

## 1. 缓存策略

### 1.1 Cache-Aside（旁路缓存）
应用程序先查缓存，未命中则查数据库并回写缓存。
- 适合读多写少的场景
- 需要处理缓存穿透、击穿、雪崩

### 1.2 Read/Write Through
缓存直接与数据库交互，应用只与缓存通信。

### 1.3 Write Behind（异步回写）
异步批量写入数据库，提高写入性能。

## 2. 缓存问题及解决方案

### 2.1 缓存穿透
查询不存在的数据，请求直接打到数据库。
**解决**：布隆过滤器、空值缓存

### 2.2 缓存击穿
热点 key 过期，瞬间大量请求打到数据库。
**解决**：互斥锁、永不过期 + 异步更新

### 2.3 缓存雪崩
大量 key 同时过期，数据库瞬间压力过大。
**解决**：过期时间加随机偏移、多级缓存、限流

## 3. 数据结构

| 类型 | 适用场景 |
|------|---------|
| String | 计数器、分布式锁、简单 KV |
| Hash | 对象存储、用户属性 |
| List | 消息队列、最新列表 |
| Set | 标签、共同好友 |
| Sorted Set | 排行榜、延迟队列 |

## 4. 持久化

### RDB（快照）
- 二进制压缩文件
- 适合备份和灾难恢复
- 可能丢失最后一次快照后的数据

### AOF（追加日志）
- 记录每个写操作
- fsync 策略：always/everysec/no
- 文件更大但更安全

## 5. 集群方案

### 主从复制
- 读写分离
- 数据冗余

### Sentinel（哨兵）
- 监控、自动故障转移
- 配置提供者

### Cluster
- 数据分片（16384 个槽）
- 去中心化""",
    },
    {
        "title": "MySQL 性能优化指南",
        "content": """# MySQL 性能优化指南

## 1. 索引优化

### 1.1 B+Tree 索引
- 最左前缀原则
- 覆盖索引避免回表
- 避免索引列上使用函数

### 1.2 联合索引
```sql
-- 好的索引设计（考虑查询条件顺序）
CREATE INDEX idx_user_status_time ON orders(user_id, status, create_time);

-- 可以高效执行的查询
SELECT * FROM orders WHERE user_id = 123 AND status = 'active';
SELECT * FROM orders WHERE user_id = 123 AND status = 'active' ORDER BY create_time;
```

### 1.3 索引优化建议
- EXPLAIN 分析执行计划
- type 列从优到差：system > const > eq_ref > ref > range > index > ALL
- rows 列越小越好

## 2. SQL 优化

### 2.1 分页优化
```sql
-- 慢：大偏移量
SELECT * FROM orders ORDER BY id LIMIT 100000, 20;

-- 快：基于主键的延迟关联
SELECT * FROM orders WHERE id >= (SELECT id FROM orders ORDER BY id LIMIT 100000, 1) LIMIT 20;
```

### 2.2 JOIN 优化
- 小表驱动大表
- 确保 JOIN 字段有索引
- 避免 SELECT *

## 3. 事务与锁

### 3.1 隔离级别
| 级别 | 脏读 | 不可重复读 | 幻读 |
|------|------|----------|------|
| READ UNCOMMITTED | Y | Y | Y |
| READ COMMITTED | N | Y | Y |
| REPEATABLE READ (默认) | N | N | Y（MVCC解决） |
| SERIALIZABLE | N | N | N |

### 3.2 死锁预防
- 固定加锁顺序
- 减少事务粒度
- 使用索引减少锁范围

## 4. 慢查询分析

### 配置
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 'ON';
```

### 分析工具
- mysqldumpslow
- pt-query-digest
- Performance Schema""",
    },
    {
        "title": "Docker 容器化部署实战",
        "content": """# Docker 容器化部署实战

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
```""",
    },
]


def save_document(title: str, content: str, source: str):
    """保存文档为 Markdown 文件"""
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:80]
    if not safe_title:
        safe_title = hashlib.md5(content.encode()).hexdigest()[:8]
    filepath = DOC_DIR / f"{safe_title}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> 来源: {source}\n\n")
        f.write(content)
    print(f"  [OK] {filepath.name}")
    return filepath


def crawl_page(url: str) -> str:
    """爬取单个页面"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # 移除脚本和样式
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        # 提取主要内容
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            return ""
        text = main.get_text(separator="\n", strip=True)
        # 清理多余空行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        print(f"  [ERR] {url}: {e}")
        return ""


def generate_image_captions():
    """生成图片描述 JSON（模拟技术图表数据）"""
    images = [
        {"filename": "microservice-architecture.png", "description": "微服务架构图：展示 API Gateway、服务注册中心、多个微服务（订单、用户、商品、支付）之间的调用关系，以及消息队列和数据库的拓扑结构"},
        {"filename": "k8s-cluster.png", "description": "Kubernetes 集群架构图：包含 Master 节点（API Server、Scheduler、Controller Manager、etcd）和多个 Worker 节点（kubelet、kube-proxy、Pod）"},
        {"filename": "redis-cluster.png", "description": "Redis Cluster 架构图：6 个节点组成集群，展示数据分片（16384 个哈希槽）、主从复制和 Sentinel 哨兵机制"},
        {"filename": "mysql-index-btree.png", "description": "MySQL B+Tree 索引结构图：三层 B+Tree，展示根节点、内部节点和叶子节点，叶子节点形成双向链表支持范围查询"},
        {"filename": "docker-compose-flow.png", "description": "Docker Compose 多服务部署流程图：展示 Nginx 反向代理 -> FastAPI 应用 -> MySQL/Redis/Milvus 的网络拓扑和依赖关系"},
        {"filename": "rag-pipeline.png", "description": "RAG 检索增强生成流程图：用户提问 -> 向量检索 -> 召回 Top-K 文档块 -> Reranker 重排序 -> LLM 生成回答 -> 返回带来源引用的答案"},
        {"filename": "jwt-auth-flow.png", "description": "JWT 认证流程图：用户登录 -> 服务端生成 Access Token（30min）+ Refresh Token（7天）-> 客户端携带 Bearer Token -> 中间件验证 -> 自动刷新"},
        {"filename": "cicd-pipeline.png", "description": "CI/CD 流水线图：Git Push -> Jenkins 构建 -> 单元测试 -> Docker 镜像构建 -> 推送镜像仓库 -> Docker Compose 部署 -> 健康检查"},
        {"filename": "saga-transaction.png", "description": "Saga 分布式事务流程图：订单服务创建订单 -> 库存服务扣减库存 -> 支付服务处理支付 -> 若失败则触发补偿事务依次回滚"},
        {"filename": "prometheus-grafana.png", "description": "Prometheus + Grafana 监控架构图：Prometheus 抓取各服务指标 -> AlertManager 告警 -> Grafana Dashboard 可视化展示 QPS/延迟/错误率"},
        {"filename": "nginx-load-balance.png", "description": "Nginx 负载均衡配置图：upstream 配置多个后端服务 -> 负载均衡策略（轮询/最少连接/IP Hash）-> 健康检查 -> 失败重试"},
        {"filename": "text-embedding.png", "description": "文本 Embedding 向量化示意图：输入文本 -> Tokenizer 分词 -> BGE-M3 模型编码 -> 输出 1024 维向量 -> 存入 Milvus 向量数据库"},
    ]
    for img in images:
        img_path = IMG_DIR / img["filename"]
        desc_path = IMG_DIR / f"{img['filename']}.json"
        # 生成一个简单的占位图
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (800, 500), color=(13, 13, 15))
        draw = ImageDraw.Draw(im)
        # 画一些简单的几何图形代表架构图
        import random
        colors = [(38, 100, 236), (238, 177, 77), (46, 168, 122), (229, 72, 77), (139, 139, 150)]
        for _ in range(15):
            x1 = random.randint(50, 700)
            y1 = random.randint(50, 400)
            w = random.randint(60, 150)
            h = random.randint(30, 80)
            color = random.choice(colors)
            draw.rectangle([x1, y1, x1 + w, y1 + h], outline=color, width=2)
            draw.rectangle([x1 + 3, y1 + 3, x1 + w - 3, y1 + h - 3], fill=(color[0] // 4, color[1] // 4, color[2] // 4))
            if random.random() > 0.3:
                x2 = random.randint(50, 700)
                y2 = random.randint(50, 400)
                draw.line([x1 + w // 2, y1 + h // 2, x2, y2], fill=(100, 100, 120), width=1)
        title = img["description"].split("：")[0] if "：" in img["description"] else img["description"][:20]
        draw.text((20, 10), title, fill=(200, 200, 220))
        im.save(img_path, "PNG")
        with open(desc_path, "w", encoding="utf-8") as f:
            json.dump(img, f, ensure_ascii=False, indent=2)
        print(f"  [IMG] {img['filename']} ({img_path.stat().st_size} bytes)")


def main():
    print("=" * 60)
    print("RAG 数据爬取 - 技术文档 & 图片")
    print("=" * 60)

    DOC_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 爬取在线文档
    print("\n[1/3] 爬取在线技术文档...")
    crawled = 0
    for source in DOC_SOURCES:
        print(f"  Source: {source['name']}")
        for url in source["urls"]:
            print(f"    {url}")
            text = crawl_page(url)
            if text and len(text) > 200:
                title = url.rstrip("/").split("/")[-1] or "doc"
                save_document(title, text[:5000], url)
                crawled += 1
                # 也收录页面中的图片
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=30)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for img in soup.find_all("img", src=True):
                        img_url = urljoin(url, img["src"])
                        alt = img.get("alt", "技术图表")
                        if any(ext in img_url.lower() for ext in [".png", ".jpg", ".svg", ".webp"]):
                            try:
                                img_resp = requests.get(img_url, headers=HEADERS, timeout=15)
                                if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                                    img_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                                    img_path = IMG_DIR / f"crawled_{img_hash}.png"
                                    with open(img_path, "wb") as f:
                                        f.write(img_resp.content)
                                    desc_path = IMG_DIR / f"crawled_{img_hash}.png.json"
                                    with open(desc_path, "w", encoding="utf-8") as f:
                                        json.dump({"filename": img_path.name, "description": alt, "source_url": url}, f, ensure_ascii=False)
                                    print(f"    [IMG] {img_path.name}")
                            except Exception:
                                pass
                except Exception:
                    pass
            time.sleep(0.5)  # 礼貌延迟

    # 2. 生成本地文档
    print(f"\n[2/3] 生成本地技术文档...")
    for doc in EXTRA_DOCS:
        save_document(doc["title"], doc["content"], "本地生成")
        crawled += 1

    # 3. 生成技术图片
    print(f"\n[3/3] 生成技术图表图片...")
    generate_image_captions()

    print(f"\n{'=' * 60}")
    print(f"完成！共生成 {crawled} 篇文档 + {len(list(IMG_DIR.glob('*.png')))} 张图片")
    print(f"文档目录: {DOC_DIR}")
    print(f"图片目录: {IMG_DIR}")


if __name__ == "__main__":
    main()
