# Nginx反向代理配置

# Nginx 反向代理配置
## 负载均衡
upstream 定义后端服务器组。策略：轮询（默认）、least_conn 最少连接、ip_hash 会话保持。
## 静态资源优化
expires 设置缓存时间，gzip 压缩文本资源，sendfile 零拷贝传输静态文件。
## HTTPS 配置
listen 443 ssl，ssl_certificate 证书路径。HTTP/2 支持多路复用，减少连接开销。
## 日志配置
access_log 记录请求，error_log 错误分级。配合 logrotate 日志轮转，避免磁盘占满。