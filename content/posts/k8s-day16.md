---
title: Day 16 - 调度策略与亲和性
module: M5-调度与资源管理
day: 16
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M2 完成，理解 Pod/Deployment
- Day 02 的 Taint/Toleration 基础
objectives:
- 掌握 nodeSelector、nodeAffinity、podAffinity、podAntiAffinity
- 掌握拓扑分布约束（topologySpreadConstraints）
- 理解调度优先级与抢占
tags:
- nodeSelector
- nodeAffinity
- podAffinity
- podAntiAffinity
- topologySpreadConstraints
date: '2026-08-18'
status: published
---

# 📘 Day 16：调度策略与亲和性

## 🎯 今日目标

- [ ] 用 nodeSelector 做简单节点选择
- [ ] 用 nodeAffinity 做高级节点亲和
- [ ] 用 podAffinity 让 Pod 靠近部署
- [ ] 用 podAntiAffinity 让 Pod 分散部署
- [ ] 用 topologySpreadConstraints 做均匀分布

---

## 🧠 理论精讲（30 分钟）

### 调度策略对比

| 策略 | 作用范围 | 强制/偏好 | 典型场景 |
|------|---------|----------|---------|
| **nodeSelector** | 节点标签 | 强制 | 简单：GPU 节点 |
| **nodeAffinity** | 节点标签 | 可偏好 | 复杂：优先 SSD，可退而求其次 |
| **podAffinity** | Pod 标签 | 可偏好 | 缓存靠近应用 |
| **podAntiAffinity** | Pod 标签 | 可偏好 | 高可用：同一服务分散 |
| **Taint/Toleration** | 节点污点 | 排斥/许可 | 专用节点 |
| **topologySpreadConstraints** | 拓扑域 | 强制 | 跨可用区均匀分布 |

### nodeAffinity 字段

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:  # 硬性要求
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/os
          operator: In
          values:
          - linux
    preferredDuringSchedulingIgnoredDuringExecution: # 软性偏好
    - weight: 1
      preference:
        matchExpressions:
        - key: disk
          operator: In
          values:
          - ssd
```

### 运算符

| 操作符 | 含义 |
|--------|------|
| `In` | 在列表中 |
| `NotIn` | 不在列表中 |
| `Exists` | 存在此标签 |
| `DoesNotExist` | 不存在此标签 |
| `Gt` | 大于（数值） |
| `Lt` | 小于（数值） |

---

## 🔧 动手实操（120 分钟）

### 练习 16.1：nodeSelector

```bash
# 1. 给节点打标签
kubectl label node k8s-node1 disk=ssd
kubectl label node k8s-node2 disk=hdd

# 2. 创建用 nodeSelector 的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ssd-pod
spec:
  nodeSelector:
    disk: ssd
  containers:
  - name: app
    image: nginx:alpine
EOF

# 3. 验证调度到 node1
kubectl get pod ssd-pod -o wide
# NODE: k8s-node1

# 4. 尝试调度到不存在的标签
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  nodeSelector:
    gpu: nvidia
  containers:
  - name: app
    image: nginx:alpine
EOF

kubectl get pod gpu-pod
# STATUS: Pending（因为没有节点有 gpu=nvidia）

kubectl describe pod gpu-pod | grep -A3 Events
# Warning  FailedScheduling  0/3 nodes are available: ...

# 5. 清理
kubectl delete pod ssd-pod gpu-pod
```

---

### 练习 16.2：nodeAffinity

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: affinity-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/os
            operator: In
            values:
            - linux
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: disk
            operator: In
            values:
            - ssd
      - weight: 50
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values:
            - cn-east
  containers:
  - name: app
    image: nginx:alpine
EOF

# 查看调度决策
kubectl get pod affinity-pod -o wide
# 优先调度到 disk=ssd 的节点

# 即使没有 disk=ssd，Pod 仍能调度（因为是 preferred）
kubectl describe pod affinity-pod | grep -A5 "Node Affinity"

kubectl delete pod affinity-pod
```

---

### 练习 16.3：podAffinity（靠近部署）

```bash
# 场景：缓存 Pod 和 应用 Pod 部署在同一节点
# 1. 创建缓存 Pod
kubectl run cache --image=redis:7-alpine --labels=app=cache

# 2. 创建应用 Pod 靠近缓存
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: app-with-cache
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname  # 同一节点
  containers:
  - name: app
    image: nginx:alpine
EOF

# 3. 验证两个 Pod 在同一节点
kubectl get pod cache app-with-cache -o wide
# 两个 Pod 的 NODE 相同

# 4. 清理
kubectl delete pod cache app-with-cache
```

---

### 练习 16.4：podAntiAffinity（分散部署）

```bash
# 场景：高可用 Web 服务分散到不同节点
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-ha
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-ha
  template:
    metadata:
      labels:
        app: web-ha
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-ha
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web
        image: nginx:alpine
EOF

# 验证 Pod 分布在不同节点（3 节点集群刚好每节点 1 个）
kubectl get pod -l app=web-ha -o wide
# 3 个 Pod 应在 3 个不同节点上

# 如果再扩容会怎样？
kubectl scale deploy web-ha --replicas=4
kubectl get pod -l app=web-ha -o wide
# 第 4 个 Pod Pending（没有第 4 个节点来分散）

kubectl describe pod <pending-pod> | grep -A5 Events

# 清理
kubectl delete deploy web-ha
```

---

### 练习 16.5：topologySpreadConstraints

```bash
# 按可用区均匀分布
kubectl label node k8s-master topology.kubernetes.io/zone=zone-a --overwrite
kubectl label node k8s-node1 topology.kubernetes.io/zone=zone-a --overwrite
kubectl label node k8s-node2 topology.kubernetes.io/zone=zone-b --overwrite

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spread-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spread-demo
  template:
    metadata:
      labels:
        app: spread-demo
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spread-demo
      containers:
      - name: app
        image: nginx:alpine
EOF

# 查看分布
kubectl get pod -l app=spread-demo -o wide
# 预期 zone-a 和 zone-b 各 3 个 Pod（maxSkew=1）

# 清理
kubectl delete deploy spread-demo
```

---

## 🐛 排错练习（30 分钟）

### 场景：Pod 一直 Pending（调度失败）

```bash
# 排查清单：
# 1. 查看 Pod 事件
kubectl describe pod <pod-name> | grep -A20 Events

# 常见原因：
# - "0/3 nodes are available: 3 node(s) didn't match node selector"
#   → nodeSelector 太严格
# - "0/3 nodes are available: 3 node(s) had taint {xxx}, that the pod didn't tolerate"
#   → 节点有污点，Pod 没容忍
# - "0/3 nodes are available: 3 Insufficient cpu/memory"
#   → 资源不足

# 2. 检查节点资源
kubectl describe node <node-name> | grep -A5 "Allocated resources"
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：高级调度策略**

```
【初始环境】3 节点集群

【操作要求】

1. 标签准备：
   - k8s-node1：env=prod, tier=frontend
   - k8s-node2：env=prod, tier=backend
   - k8s-master：env=prod, tier=management

2. 部署 frontend Deployment（3 副本）：
   - podAntiAffinity：同 app=frontend 的 Pod 不在同一节点
   - nodeAffinity (required)：tier=frontend
   - 观察 Pod 会不会 Pending（只有 1 个 frontend 节点但有 3 个副本）

3. 部署 backend Deployment（2 副本）：
   - nodeAffinity (required)：tier=backend
   - podAffinity (preferred)：靠近 app=cache 的 Pod

4. 部署 cache Pod（1 个）：
   - nodeAffinity (required)：tier=backend
   - 无其他限制

5. 观察 backend 是否自动调度到与 cache 同一节点

6. 添加 topologySpreadConstraints：backend 按 zone 均匀分布

【评分标准】
- 标签设置正确（10 分）
- frontend 反亲和正确（25 分）
- backend nodeAffinity 正确（20 分）
- podAffinity 靠近 cache 正确（20 分）
- topologySpreadConstraints 正确（15 分）
- 观察分析完整（10 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl label node <node> key=value` | 给节点打标签 | 配合 nodeSelector 使用，Pod 通过 nodeSelector 精确匹配 |
| `kubectl label node <node> key-` | 删除节点标签 | 标签名后加 `-` |
| `kubectl get nodes --show-labels` | 查看节点和标签 | 确认标签是否打对 |
| `kubectl get nodes -l key=value` | 按标签筛选节点 | `-l` = `--selector`，快速找到匹配标签的节点 |
| `kubectl taint node <node> key=value:NoSchedule` | 添加污点（硬排斥） | 无对应 Toleration 的 Pod 无法调度 |
| `kubectl taint node <node> key=value:PreferNoSchedule` | 添加软污点 | 尽量不调度，资源不足时仍可调度 |
| `kubectl taint node <node> key=value:NoExecute` | 添加驱逐级污点 | 已有 Pod 若未容忍也会被驱逐 |
| `kubectl taint node <node> key=value:NoSchedule-` | 移除污点 | 末尾加 `-` 删除对应 Taint |
| `kubectl describe node <node> \| grep Taints` | 查看节点污点 | 排错时确认节点是否有预期外的污点 |
| `kubectl cordon <node>` | 标记节点不可调度 | 等同于添加 node.kubernetes.io/unschedulable:NoSchedule |
| `kubectl uncordon <node>` | 恢复节点可调度 | 取消 cordon 标记 |
| `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` | 安全驱逐节点上所有 Pod | 节点维护必需；DaemonSet Pod 需 --ignore-daemonsets 跳过 |
| `kubectl top nodes` | 查看节点资源用量 | 调度决策参考；需安装 metrics-server |
| `kubectl get pods -o wide \| grep <node>` | 查看某节点上的所有 Pod | 替代 `--field-selector=spec.nodeName=<node>` |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：调度与驱逐 | https://kubernetes.io/docs/concepts/scheduling-eviction/ |
| Kubernetes 官方：节点亲和性 | https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity |
| Kubernetes 官方：污点与容忍 | https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| Kubernetes 官方：Pod 拓扑分布约束 | https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/ |
| Kubernetes 官方：安全驱逐节点 | https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/ |
