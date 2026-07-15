# API网关设计模式

# API 网关设计模式
## 核心职责
统一入口管理：路由转发、认证鉴权、限流熔断、请求聚合、协议转换。
## 限流策略
令牌桶算法平滑突发流量，滑动窗口精确控制QPS。Sentinel 集成 Gateway 实现网关层限流。
## 熔断降级
Hystrix/Sentinel 熔断器：错误率超阈值自动断路，半开状态探测恢复。降级返回兜底数据。
## 灰度发布
通过 Header/Cookie 路由到不同版本服务。Istio VirtualService 实现基于权重的流量分配。