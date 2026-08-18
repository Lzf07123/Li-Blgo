---
title: Day 10 - 网络策略与 CNI 原理
module: M3-网络与服务发现
day: 10
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 08-09 完成，理解 Service 和 Ingress
objectives:
- 理解 CNI 工作原理
- 掌握 NetworkPolicy 配置
- 实现命名空间级别网络隔离
- 实现 Pod 级别精细化网络控制
- 掌握 ingress/egress 规则
tags:
- CNI
- NetworkPolicy
- Calico
- 网络隔离
- ingress
- egress
date: '2026-08-18'
status: published
---

# 📘 Day 10：网络策略与 CNI 原理

## 🎯 今日目标

- [ ] 理解 Calico CNI 的基本原理
- [ ] 能创建 NetworkPolicy 实现 Pod 间访问控制
- [ ] 掌握 namespaceSelector 和 podSelector
- [ ] 能配置 ingress 和 egress 规则
- [ ] 能通过 NetworkPolicy 实现零信任网络

---

## 🧠 理论精讲（30 分钟）

### CNI 工作流程

```
1. kubelet 创建 Pod → 
2. 调用 CNI 插件 → 
3. CNI 分配 IP、创建 veth pair →
4. 配置路由规则 →
5. Pod 获得网络
```

### Calico 数据路径

```
Pod-A (veth) ←→ Host-A (cali-xxx) ←→ BGP/IPIP ←→ Host-B (cali-yyy) ←→ Pod-B (veth)
```

### NetworkPolicy 核心概念

```yaml
# 默认规则：所有流量允许（无 NetworkPolicy 时）
# 一旦创建 NetworkPolicy，默认拒绝所有未明确允许的流量

spec:
  podSelector: {}        # 选择受影响的 Pod
  policyTypes:           # 规则方向
  - Ingress
  - Egress
  ingress: [...]         # 入站规则
  egress: [...]          # 出站规则
```

### 选择器组合

| 选择器 | 作用域 |
|--------|--------|
| `podSelector` | 选 Pod |
| `namespaceSelector` | 选命名空间 |
| `ipBlock` | 选 IP CIDR |

---

## 🔧 动手实操（120 分钟）

### 练习 10.1：Deny-All 策略

```bash
# 1. 创建测试命名空间和 Pod
kubectl create ns netpol-test

kubectl run web --image=nginx:alpine -n netpol-test --port=80
kubectl expose pod web -n netpol-test --port=80

kubectl run client --image=busybox:1.36 -n netpol-test -- sleep 3600

# 2. 验证默认情况下可访问
kubectl exec client -n netpol-test -- wget -q -O- http://web.netpol-test
# 正常返回

# 3. 创建 Deny-All 策略
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: netpol-test
spec:
  podSelector: {}        # 选择所有 Pod
  policyTypes:
  - Ingress
  - Egress
  # 空的 ingress/egress = 不允许任何流量
EOF

# 4. 再次尝试访问
kubectl exec client -n netpol-test -- wget -q -O- http://web.netpol-test --timeout=5
# 超时！被 NetworkPolicy 阻止

# 5. 清理
kubectl delete networkpolicy deny-all -n netpol-test
```

---

### 练习 10.2：精确允许 Ingress

```bash
# 1. 只允许特定标签的 Pod 访问 web
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-access
  namespace: netpol-test
spec:
  podSelector:
    matchLabels:
      run: web              # 应用到 web Pod
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend    # 只允许有 role=frontend 的 Pod
    ports:
    - protocol: TCP
      port: 80
EOF

# 2. client 没有 role=frontend 标签，应被拒绝
kubectl exec client -n netpol-test -- wget -q -O- http://web.netpol-test --timeout=5
# 超时

# 3. 给 client 打上标签
kubectl label pod client -n netpol-test role=frontend

# 4. 再次访问，应成功
kubectl exec client -n netpol-test -- wget -q -O- http://web.netpol-test
# 正常返回

# 5. 清理
kubectl delete networkpolicy allow-web-access -n netpol-test
kubectl label pod client -n netpol-test role-
```

---

### 练习 10.3：namespaceSelector 跨命名空间控制

```bash
# 1. 创建第二个命名空间
kubectl create ns netpol-external

# 2. 在 external 命名空间创建 Pod
kubectl run ext-client --image=busybox:1.36 -n netpol-external -- sleep 3600
kubectl label ns netpol-external env=trusted

# 3. 创建允许来自 trusted 命名空间的策略
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-trusted-ns
  namespace: netpol-test
spec:
  podSelector:
    matchLabels:
      run: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          env: trusted         # 允许 env=trusted 的命名空间
    ports:
    - protocol: TCP
      port: 80
EOF

# 4. 测试从不同命名空间访问
kubectl exec ext-client -n netpol-external -- \
  wget -q -O- http://web.netpol-test.netpol-test.svc.cluster.local --timeout=5
# 正常返回

kubectl exec client -n netpol-test -- \
  wget -q -O- http://web --timeout=5
# 超时（test 命名空间内默认 Pod 被拒绝）

# 5. 清理
kubectl delete networkpolicy allow-trusted-ns -n netpol-test
kubectl label ns netpol-external env-
```

---

### 练习 10.4：Egress 出站控制

```bash
# 1. 限制 Pod 只能访问特定外部地址
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-egress
  namespace: netpol-test
spec:
  podSelector:
    matchLabels:
      run: client
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          run: web           # 允许访问 web
    ports:
    - protocol: TCP
      port: 80
  - to:                      # 还允许 DNS
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
EOF

# 2. 测试访问 web（应允许）
kubectl exec client -n netpol-test -- wget -q -O- http://web --timeout=5
# 正常返回

# 3. 测试访问外部（应被拒绝）
kubectl exec client -n netpol-test -- wget -q -O- http://www.baidu.com --timeout=5
# 超时

# 4. 清理
kubectl delete networkpolicy restrict-egress -n netpol-test
```

---

### 练习 10.5：ipBlock 白名单

```bash
# 允许来自特定 IP 段的访问
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ipblock
  namespace: netpol-test
spec:
  podSelector:
    matchLabels:
      run: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.244.0.0/16     # Pod 网络
    - ipBlock:
        cidr: 10.0.0.0/8        # 节点网络
    ports:
    - protocol: TCP
      port: 80
EOF

kubectl get networkpolicy allow-ipblock -n netpol-test -o yaml
```

---

## 🐛 排错练习（30 分钟）

### 场景：NetworkPolicy 导致服务不可用

```bash
# 问题：创建 NetworkPolicy 后某些服务突然不可用

# 排查步骤：
# 1. 列出所有 NetworkPolicy
kubectl get networkpolicy --all-namespaces

# 2. 查看具体策略规则
kubectl describe networkpolicy <name> -n <ns>

# 3. 检查是否缺少必需的规则
# - CoreDNS 访问（UDP 53）
# - api-server 访问
# - 健康检查端点

# 4. 临时删除策略验证
kubectl delete networkpolicy <name> -n <ns>

# 5. 恢复后确认问题根源，补充遗漏规则
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：零信任网络策略**

```
【初始环境】
- 命名空间 secure-app 中存在以下 Pod：
  - db（标签 app=db，端口 5432）
  - api（标签 app=api，端口 8080）
  - web（标签 app=web，端口 80）

【操作要求】

1. 创建 Deny-All 默认策略（拒绝所有入站和出站流量）

2. 放行规则：
   a. web → api:8080（前端调用 API）
   b. api → db:5432（API 调用数据库）
   c. 所有 Pod → CoreDNS（UDP 53，kube-system 命名空间）
   d. web 允许来自 Ingress Controller 命名空间的入站（标签 app=ingress-nginx）

3. 验证：
   - web 可以访问 api:8080 ✅
   - api 可以访问 db:5432 ✅
   - web 无法直接访问 db:5432 ❌（应被拒绝）
   - api 无法访问外部网络 ❌（应被拒绝）

【评分标准】
- Deny-All 策略正确（15 分）
- web→api 规则正确（20 分）
- api→db 规则正确（20 分）
- DNS 放行规则正确（20 分）
- Ingress Controller 入站规则正确（15 分）
- 隔离验证通过（10 分）
```

---

## 🧹 环境清理

```bash
kubectl delete ns netpol-test netpol-external
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get networkpolicy` | 列出所有 NetworkPolicy | short name: netpol |
| `kubectl get networkpolicy -o yaml` | 查看 NetworkPolicy 详细规则 | 查看 podSelector、ingress/egress 规则、policyTypes |
| `kubectl describe networkpolicy <name>` | NetworkPolicy 详情 | 包含规则匹配的 Pod 和流向 |
| `kubectl get pods -n kube-system -l k8s-app=calico-node` | 查看 Calico node Pod | Calico 在每个节点运行一个 agent |
| `kubectl -n kube-system logs -l k8s-app=calico-node --tail=50` | 查看 Calico 日志 | NetworkPolicy 不生效时首要排查 |
| `calicoctl get ippool -o wide` | 查看 IP 地址池 | 确认 Pod CIDR 与 kubeadm init 一致 |
| `calicoctl get felixconfiguration` | 查看 Calico Felix 配置 | Felix 是每个节点的策略执行引擎 |
| `calicoctl get networkpolicy` | 查看 Calico 层面的网络策略 | 比 kubectl get netpol 更底层 |
| `kubectl run test --image=busybox --rm -it --labels="app=test" -- wget -O- --timeout=3 http://<svc>` | 携带标签测试连通性 | NetworkPolicy 基于标签匹配，运行测试 Pod 时需带正确的 labels |
| `kubectl exec <pod> -- nc -zv <target-ip> <port>` | 测试 TCP 端口通断 | 比 curl/wget 更底层的连通性测试 |
| `kubectl get nodes -o wide \| awk '{print $6}'` | 提取所有节点 CIDR | Calico IPAM 基于节点 CIDR 分配 Pod IP |
| `kubectl exec <pod> -- ip route` | 查看 Pod 内路由表 | 理解 Pod 出站流量路径 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：NetworkPolicy | https://kubernetes.io/docs/concepts/services-networking/network-policies/ |
| Kubernetes 官方：声明 Network Policy | https://kubernetes.io/docs/tasks/administer-cluster/declare-network-policy/ |
| Calico 官方文档 | https://docs.tigera.io/calico/latest/about/ |
| Calico 网络策略指南 | https://docs.tigera.io/calico/latest/network-policy/ |
| CNI 规范 | https://github.com/containernetworking/cni/blob/master/SPEC.md |
| Calico IPAM 原理 | https://docs.tigera.io/calico/latest/networking/ipam/ |
