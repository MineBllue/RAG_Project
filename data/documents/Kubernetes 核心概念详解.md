# Kubernetes 核心概念详解

> 来源: 本地生成

# Kubernetes 核心概念详解

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
- **StorageClass**：动态存储供应