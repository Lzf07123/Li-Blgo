---
title: Day 08 - Service 与集群内服务发现
module: M3-网络与服务发现
day: 8
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- M2 完成，理解 Pod 和 Deployment
objectives:
- 理解 Service 的工作原理（iptables/IPVS）
- 掌握 ClusterIP、NodePort、LoadBalancer、ExternalName 四种类型
- 掌握 Endpoint 与 EndpointSlice
- 理解 CoreDNS 服务发现机制
- 能通过 Service 暴露和访问应用
tags:
- Service
- ClusterIP
- NodePort
- Endpoint
- CoreDNS
- kube-proxy
date: '2026-08-18'
status: published
---

# 📘 Day 08：Service 与集群内服务发现

## 🎯 今日目标

- [ ] 理解 kube-proxy 如何实现 Service 流量转发
- [ ] 创建四种类型 Service 并验证
- [ ] 理解 Endpoint 与 Service 的关系
- [ ] 掌握 CoreDNS 域名格式和 DNS 策略
- [ ] 能通过 Pod DNS 名称实现服务间通信

---

## 🧠 理论精讲（30 分钟）

### Service 解决了什么问题

Pod 是**短暂的**（IP 会变），Service 提供**稳定的访问入口**：

```
Pod-A (IP: 10.244.1.5) ─┐
Pod-B (IP: 10.244.2.3) ─┤──→ Service (ClusterIP: 10.96.0.1) ──→ 客户端
Pod-C (IP: 10.244.1.9) ─┘
```

无论后端 Pod 如何变化，Service 的 ClusterIP 不变。

### kube-proxy 工作模式

| 模式 | 原理 | 性能 |
|------|------|------|
| **iptables** | 通过 iptables 规则随机转发 | 规则数多时性能下降 |
| **IPVS** | 内核级负载均衡 | 高性能，支持多种调度算法 |

### 四种 Service 类型

| 类型 | 访问范围 | 典型场景 |
|------|---------|---------|
| **ClusterIP** | 集群内部 | 内部服务间通信 |
| **NodePort** | 节点 IP + 端口 | 开发调试、简单外部访问 |
| **LoadBalancer** | 外部 LB 分发 | 生产环境外部入口 |
| **ExternalName** | DNS CNAME | 外部服务映射 |

### CoreDNS 域名格式

```
<service-name>.<namespace>.svc.cluster.local
```

```bash
# 示例
api-server.default.svc.cluster.local
redis-cache.production.svc.cluster.local
```

---

## 🔧 动手实操（120 分钟）

### 练习 8.1：ClusterIP Service 基础

```bash
# 1. 创建后端 Deployment
kubectl create deploy backend --image=nginx:alpine --replicas=3

# 2. 暴露为 ClusterIP Service
kubectl expose deploy backend --port=80 --target-port=80

# 3. 查看 Service
kubectl get svc backend
# NAME      TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
# backend   ClusterIP   10.96.xxx.xxx  <none>        80/TCP    10s

# 4. 查看 Endpoint
kubectl get endpoints backend
# NAME      ENDPOINTS                                   AGE
# backend   10.244.1.2:80,10.244.2.3:80,10.244.1.4:80  10s

# 5. 用临时 Pod 测试访问
kubectl run test-client --image=busybox:1.36 --rm -it --restart=Never -- \
  wget -q -O- http://backend
# 输出：nginx 默认页面

# 6. 测试完整的 FQDN
kubectl run test-dns --image=busybox:1.36 --rm -it --restart=Never -- \
  wget -q -O- http://backend.default.svc.cluster.local
```

---

### 练习 8.2：NodePort Service

```bash
# 1. 创建 NodePort Service
kubectl expose deploy backend --type=NodePort --port=80 --name=backend-np

# 2. 查看分配的端口
kubectl get svc backend-np
# NAME         TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
# backend-np   NodePort   10.96.xxx.xxx  <none>        80:30080/TCP   5s

# NodePort 范围：30000-32767

# 3. 通过节点 IP 访问
# 获取任一节点 IP
kubectl get nodes -o wide
# 在集群外浏览器或 curl 访问：
curl http://<任意节点IP>:30080

# 4. 验证 NodePort 也在 ClusterIP 上可用
kubectl run test-np --image=busybox:1.36 --rm -it --restart=Never -- \
  wget -q -O- http://backend-np

# 5. 清理
kubectl delete svc backend-np
```

---

### 练习 8.3：ExternalName Service

```bash
# 将外部域名映射为集群内部 Service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  type: ExternalName
  externalName: database.example.com
EOF

# 验证
kubectl get svc external-db
# NAME          TYPE           CLUSTER-IP   EXTERNAL-IP          PORT(S)   AGE
# external-db   ExternalName   <none>       database.example.com <none>    5s

# 集群内 Pod 访问 external-db 会解析到 database.example.com
kubectl run dns-check --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup external-db

# 清理
kubectl delete svc external-db
```

---

### 练习 8.4：Headless Service + 直接 Pod DNS

```bash
# 1. 创建 Headless Service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: headless-svc
spec:
  clusterIP: None
  selector:
    app: backend
  ports:
  - port: 80
EOF

# 2. 验证 ClusterIP 为空
kubectl get svc headless-svc
# CLUSTER-IP: None

# 3. DNS 查询 Headless Service
kubectl run dns-hl --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup headless-svc
# 返回所有后端 Pod 的 IP（而不是一个 ClusterIP）

# 4. 清理
kubectl delete svc headless-svc
```

---

### 练习 8.5：Service 负载均衡验证

```bash
# 1. 创建一个能区分 Pod 的后端
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-test
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lb-test
  template:
    metadata:
      labels:
        app: lb-test
    spec:
      containers:
      - name: http
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          echo -e "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello from $(hostname)" > /tmp/response
          while true; do nc -l -p 8080 < /tmp/response; done
        ports:
        - containerPort: 8080
EOF

kubectl expose deploy lb-test --port=8080 --target-port=8080

# 2. 多次请求验证负载均衡效果
kubectl run lb-client --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c 'for i in $(seq 1 10); do wget -q -O- http://lb-test:8080; echo; done'
# 输出应分布在不同 Pod

# 3. 检查 kube-proxy 模式
kubectl logs -n kube-system -l k8s-app=kube-proxy | grep "Using"

# 4. 清理
kubectl delete deploy backend lb-test
kubectl delete svc backend lb-test
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：Service 无法访问

```bash
# 排查清单
# 1. Service 的 selector 是否匹配 Pod 的 labels？
kubectl get svc <svc-name> -o jsonpath='{.spec.selector}'
kubectl get pod -l <key>=<value>

# 2. Endpoint 是否为空？
kubectl get endpoints <svc-name>
# 如果 ENDPOINTS 为空，说明 selector 不匹配

# 3. targetPort 是否正确？
kubectl get svc <svc-name> -o jsonpath='{.spec.ports[*].targetPort}'
kubectl get pod -l app=<name> -o jsonpath='{.spec.containers[*].ports}'

# 4. 网络策略是否阻止？
kubectl get networkpolicies
```

### 场景 2：CoreDNS 解析失败

```bash
# 测试 DNS 解析
kubectl run dns-debug --image=busybox:1.36 --rm -it --restart=Never -- nslookup kubernetes.default

# 检查 CoreDNS Pod
kubectl get pods -n kube-system -l k8s-app=kube-dns

# 检查 CoreDNS 日志
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20

# 重启 CoreDNS
kubectl rollout restart deploy/coredns -n kube-system
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：多层服务暴露**

```
【操作要求】

1. 创建 Deployment app-v1（3 副本，nginx:alpine），暴露为 ClusterIP Service app-svc
2. 创建 Deployment app-v2（2 副本，httpd:alpine），暴露为 ClusterIP Service app-v2-svc
3. 在 app-v1 的 nginx 中配置反向代理到 app-v2-svc（通过 Service 名称）
4. 创建 NodePort Service app-gateway，暴露 app-svc 到节点 31080 端口
5. 验证：
   - 集群内 curl http://app-svc → 返回 nginx 页面
   - 集群内 curl http://app-v2-svc → 返回 httpd 页面
   - 节点 IP:31080 → 返回 nginx 页面
   - CoreDNS 解析 app-svc 和 app-v2-svc 均正常
6. 输出所有 Service 的 Endpoint 信息

【评分标准】
- Service 创建正确（30 分）
- 集群内通信正常（25 分）
- NodePort 访问正常（20 分）
- DNS 解析正常（15 分）
- Endpoint 正确（10 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get svc` | 列出所有 Service | TYPE 列显示 ClusterIP/NodePort/LoadBalancer/ExternalName |
| `kubectl get svc -o wide` | Service + 选择器/端口 | 确认 Selector 和暴露的端口 |
| `kubectl get endpoints` | 查看 Service 后端端点 | 为空说明 Selector 没匹配到 Running Pod |
| `kubectl describe svc <name>` | Service 详细信息 | 查看 SessionAffinity、Endpoints、Events |
| `kubectl expose deploy <name> --port=80 --target-port=8080` | 快速创建 Service 暴露 Deployment | 默认创建 ClusterIP 类型 |
| `kubectl expose deploy <name> --type=NodePort --port=80 --target-port=8080` | 创建 NodePort Service | 节点 IP:30000-32767 可外部访问 |
| `kubectl expose deploy <name> --type=LoadBalancer --port=80` | 创建 LoadBalancer Service | 云厂商分配外部 LB IP（学习环境会一直 Pending） |
| `kubectl run test --image=busybox --rm -it -- wget -O- http://<svc-name>` | 临时 Pod 测试 Service 可达性 | `--rm` 退出即删除，网络调试首选 |
| `kubectl exec <pod> -- nslookup <svc-name>` | 验证 CoreDNS 解析 | 解析失败说明 CoreDNS 故障或 SVC 不存在 |
| `kubectl exec <pod> -- nslookup <svc-name>.<ns>.svc.cluster.local` | 验证 FQDN 解析 | 全限定域名格式：`<svc>.<namespace>.svc.cluster.local` |
| `kubectl exec <pod> -- curl -s <svc-name>.<ns>.svc.cluster.local:<port>` | 通过 FQDN 访问服务 | 跨命名空间通信必须用 FQDN |
| `kubectl get pods -l app=<label>` | 按标签查 Pod | 验证 Service Selector 是否匹配到正确的 Pod |
| `kubectl patch svc <name> -p '{"spec":{"sessionAffinity":"ClientIP"}}'` | 修改会话亲和性 | 同一客户端 IP 始终路由到同一 Pod |
| `kubectl create svc clusterip <name> --tcp=80:8080 --dry-run=client -o yaml` | 生成 ClusterIP Service YAML | `--tcp` 指定 `<port>:<targetPort>` |
| `kubectl create svc nodeport <name> --tcp=80:8080 --node-port=30080 --dry-run=client -o yaml` | 生成 NodePort Service YAML | 指定固定 NodePort 而非随机端口 |
| `kubectl -n kube-system logs -l k8s-app=kube-dns` | 查看 CoreDNS 日志 | DNS 解析故障时首要排查 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：Service | https://kubernetes.io/docs/concepts/services-networking/service/ |
| Kubernetes 官方：DNS 与服务发现 | https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/ |
| Kubernetes 官方：Service 调试 | https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/ |
| Kubernetes 官方：EndpointSlice | https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/ |
| CoreDNS 官方文档 | https://coredns.io/manual/toc/ |
