# Docker容器化部署实战

# Docker 容器化部署实战
## 多阶段构建
使用多阶段构建减小镜像体积，构建阶段用完整SDK，运行阶段只保留二进制和运行时依赖。
## Docker Compose 编排
通过 docker-compose.yml 定义多服务依赖关系。关键配置：depends_on + healthcheck 确保启动顺序，volumes 持久化数据，networks 服务间通信。
## 网络模式
bridge 默认桥接、host 宿主机网络、overlay 跨主机通信。生产环境推荐自定义 bridge 网络实现服务间 DNS 解析。
## 资源限制
通过 deploy.resources.limits 设置 cpus/memory 上限，reservations 预留资源。防止单容器耗尽宿主机资源。