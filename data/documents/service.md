# service

> 来源: https://kubernetes.io/zh-cn/docs/concepts/services-networking/service/

此文档中的信息可能已过时
此文档的更新日期比原文晚，因此其中的信息可能已过时。如果能阅读英文，请查看英文版本以获取最新信息：
Service
服务（Service）
将在集群中运行的应用通过同一个面向外界的端点公开出去，即使工作负载分散于多个后端也完全可行。
Kubernetes 中 Service 是 将运行在一个或一组
Pod
上的网络应用程序公开为网络服务的方法。
Kubernetes 中 Service 的一个关键目标是让你无需修改现有应用以使用某种不熟悉的服务发现机制。
你可以在 Pod 集合中运行代码，无论该代码是为云原生环境设计的，还是被容器化的老应用。
你可以使用 Service 让一组 Pod 可在网络上访问，这样客户端就能与之交互。
如果你使用
Deployment
来运行你的应用，
Deployment 可以动态地创建和销毁 Pod。
在任何时刻，你都不知道有多少个这样的 Pod 正在工作以及它们健康与否；
你可能甚至不知道如何辨别健康的 Pod。
Kubernetes
Pod
的创建和销毁是为了匹配集群的预期状态。
Pod 是临时资源（你不应该期待单个 Pod 既可靠又耐用）。
每个 Pod 会获得属于自己的 IP 地址（Kubernetes 期待网络插件来保证这一点）。
对于集群中给定的某个 Deployment，这一刻运行的 Pod 集合可能不同于下一刻运行该应用的
Pod 集合。
这就带来了一个问题：如果某组 Pod（称为“后端”）为集群内的其他 Pod（称为“前端”）
集合提供功能，前端要如何发现并跟踪要连接的 IP 地址，以便其使用负载的后端组件呢？
Kubernetes 中的 Service
Service API 是 Kubernetes 的组成部分，它是一种抽象，帮助你将 Pod 集合在网络上公开出去。
每个 Service 对象定义端点的一个逻辑集合（通常这些端点就是 Pod）以及如何访问到这些 Pod 的策略。
例如，考虑一个无状态的图像处理后端，其中运行 3 个副本（Replicas）。
这些副本是可互换的 —— 前端不需要关心它们调用的是哪个后端。
即便构成后端集合的实际 Pod 可能会发生变化，前端客户端不应该也没必要知道这些，
而且它们也不必亲自跟踪后端的状态变化。
Service 抽象使这种解耦成为可能。
Service 所对应的 Pod 集合通常由你定义的
选择算符
来确定。
若想了解定义 Service 端点的其他方式，可以查阅
不带
选择算符的 Service
。
如果你的工作负载使用 HTTP 通信，你可能会选择使用
Ingress
来控制
Web 流量如何到达该工作负载。Ingress 不是一种 Service，但它可用作集群的入口点。
Ingress 能让你将路由规则整合到同一个资源内，这样你就能将工作负载的多个组件公开出去，
这些组件使用同一个侦听器，但各自独立地运行在集群中。
用于 Kubernetes 的
Gateway
API
能够提供 Ingress 和 Service 所不具备的一些额外能力。
Gateway 是使用
CustomResourceDefinitions
实现的一系列扩展 API。
你可以添加 Gateway 到你的集群中，之后就可以使用它们配置如何访问集群中运行的网络服务。
云原生服务发现
如果你想要在自己的应用中使用 Kubernetes API 进行服务发现，可以查询
API 服务器
，
寻找匹配的 EndpointSlice 对象。
只要 Service 中的 Pod 集合发生变化，Kubernetes 就会为其更新 EndpointSlice。
对于非本地应用，Kubernetes 提供了在应用和后端 Pod 之间放置网络端口或负载均衡器的方法。
无论采用那种方式，你的负载都可以使用这里的
服务发现
机制找到希望连接的目标。
定义 Service
Kubernetes 中的 Service 是一个
对象
（与 Pod 或 ConfigMap 类似）。你可以使用 Kubernetes API 创建、查看或修改 Service 定义。
通常你会使用
kubectl
这类工具来替你发起这些 API 调用。
例如，假定有一组 Pod，每个 Pod 都在侦听 TCP 端口 9376，并且它们还被打上
app.kubernetes.io/name=MyApp
标签。你可以定义一个 Service 来发布该 TCP 侦听器。
service/simple-service.yaml
apiVersion
:
v1
kind
:
Service
metadata
:
name
:
my-service
spec
:
selector
:
app.kubernetes.io/name
:
MyApp
ports
:
-
protocol
:
TCP
port
:
80
targetPort
:
9376
应用上述清单时，系统将创建一个名为 "my-service" 的、
服务类型
默认为 ClusterIP 的 Service。
该 Service 指向带有标签
app.kubernetes.io/name: MyApp
的所有 Pod 的 TCP 端口 9376。
Kubernetes 为该 Service 分配一个 IP 地址（称为 “集群 IP”），供虚拟 IP 地址机制使用。
有关该机制的更多详情，请阅读
虚拟 IP 和服务代理
。
此 Service 的控制器不断扫描与其选择算符匹配的 Pod 集合，然后对 Service 的
EndpointSlice 集合执行必要的更新。
Service 对象的名称必须是有效的
RFC 1035 标签名称
。
说明：
Service 能够将
任意
入站
port
映射到某个
targetPort
。
默认情况下，出于方便考虑，
targetPort
会被设置为与
port
字段相同的值。
对 Service 对象放宽命名限制
特性状态：
Kubernetes v1.36 [beta]
（默认启用）
RelaxedServiceNameValidation
特性开关允许 Service 对象的名称以数字开头。
启用该特性后，Service 对象的名称必须符合
RFC 1123 标签名称
的规范。
端口定义
Pod 中的端口定义是有名字的，你可以在 Service 的
targetPort
属性中引用这些名字。
例如，我们可以通过以下方式将 Service 的
targetPort
绑定到 Pod 端口：
apiVersion
:
v1
kind
:
Service
metadata
:
name
:
nginx-service
spec
:
selector
:
app.kubernetes.io/name
:
proxy
ports
:
-
name
:
name-of-service-port
protocol
:
TCP
port
:
80
targetPort
:
http-web-svc
---
+apiVersion
:
v1
kind
:
Pod
metadata
:
name
:
nginx
labels
:
app.kubernetes.io/name
:
proxy
spec
:
containers
:
-
name
:
nginx
image
:
nginx:stable
ports
:
-
containerPort
:
80
name
:
http-web-svc
即使在 Service 中混合使用配置名称相同的多个 Pod，各 Pod 通过不同的端口号支持相同的网络协议，
此机制也可以工作。这一机制为 Service 的部署和演化提供了较高的灵活性。
例如，你可以在后端软件的新版本中更改 Pod 公开的端口号，但不会影响到客户端。
Service 的默认协议是
TCP
；
你还可以使用其他
受支持的任何协议
。
由于许多 Service 需要公开多个端口，所以 Kubernetes 为同一 Service 定义
多个端口
。
每个端口定义可以具有相同的
protocol
，也可以具有不同协议。
没有选择算符的 Service
由于选择算符的存在，Service 的最常见用法是为 Kubernetes Pod 集合提供访问抽象，
但是当与相应的
EndpointSlice
对象一起使用且没有设置选择算符时，Service 也可以为其他类型的后端提供抽象，
包括在集群外运行的后端。
例如：
你希望在生产环境中使用外部数据库集群，但在测试环境中使用自己的数据库。
你希望让你的 Service 指向另一个
名字空间（Namespace）
中或其它集群中的 Service。
你正在将工作负载迁移到 Kubernetes 上来。在评估所采用的方法时，你仅在 Kubernetes
中运行一部分后端。
在所有这些场景中，你都可以定义
不
指定用来匹配 Pod 的选择算符的 Service。例如：
apiVersion
:
v1
kind
:
Service
metadata
:
name
:
my-service
spec
:
ports
:
-
protocol
:
TCP
port
:
80
targetPort
:
9376
由于此 Service 没有选择算符，因此不会自动创建对应的 EndpointSlice 对象。
你可以通过手动添加 EndpointSlice 对象，将 Service 映射到该服务运行位置的网络地址和端口：
apiVersion
:
discovery.k8s.io/v1
kind
:
EndpointSlice
metadata
:
name
:
my-service-1
# 按惯例将 Service 的名称用作 EndpointSlice 名称的前缀
labels
:
# 你应设置 "kubernetes.io/service-name" 标签。
# 设置其值以匹配 Service 的名称
kubernetes.io/service-name
:
my-service
addressType
:
IPv4
ports
:
-
name
:
''
# 应与上面定义的 Service 端口的名称匹配
appProtocol
:
http
protocol
:
TCP
port
:
9376
endpoints
:
# 此列表中的 IP 地址可以按任何顺序显示
-
addresses
:
-
"10.4.5.6"
-
addresses
:
-
"10.1.2.3"
自定义 EndpointSlices
当为 Service 创建
EndpointSlice
对象时，可以为 EndpointSlice 使用任何名称。
一个名字空间中的各个 EndpointSlice 都必须具有一个唯一的名称。通过在 EndpointSlice 上设置
kubernetes.io/service-name
标签
可以将
EndpointSlice 链接到 Service。
说明：
端点 IP 地址
必须不是
：本地回路地址（IPv4 的 127.0.0.0/8、IPv6 的 ::1/128）
或链路本地地址（IPv4 的 169.254.0.0/16 和 224.0.0.0/24、IPv6 的 fe80::/64）。
端点 IP 地址不能是其他 Kubernetes 服务的集群 IP，因为
kube-proxy
不支持将虚拟 IP 作为目标地址。
对于你自己或在你自己代码中创建的 EndpointSlice，你还应该为
endpointslice.kubernetes.io/managed-by
标签设置一个值。如果你创建自己的控制器代码来管理 EndpointSlice，
请考虑使用类似于
"my-domain.example/name-of-contro