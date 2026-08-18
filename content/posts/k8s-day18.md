---
title: Day 18 - 调度综合实战
module: M5-调度与资源管理
day: 18
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M5 Day 16-17 全部完成
objectives:
- 综合调度策略 + 资源管理 + 自动伸缩
- 设计多租户资源隔离方案
tags:
- 综合实战
- 多租户
- 资源隔离
date: '2026-08-18'
status: published
---

# 📘 Day 18：调度综合实战

## 🎯 今日目标

- [ ] 综合使用调度策略实现多层级部署
- [ ] 设计命名空间级别资源隔离
- [ ] 故障自愈 + 自动伸缩全链路验证

---

## 🧠 理论精讲（10 分钟）

### 多租户资源隔离架构

```
┌────────────────────────────────────────────┐
│                K8s Cluster                  │
│                                             │
│  ┌── ns: team-a ──┐  ┌── ns: team-b ──┐   │
│  │ ResourceQuota   │  │ ResourceQuota   │   │
│  │ CPU: 4, Mem: 8G │  │ CPU: 2, Mem: 4G │   │
│  │                 │  │                 │   │
│  │ NodeSelector:   │  │ NodeSelector:   │   │
│  │ node-group=a    │  │ node-group=b    │   │
│  │                 │  │                 │   │
│  │ HPA + PDB      │  │ HPA + PDB      │   │
│  └─────────────────┘  └─────────────────┘   │
└────────────────────────────────────────────┘
```

---

## 🔧 动手实操（150 分钟）

### 练习 18.1：多租户场景构建

```bash
# 1. 准备节点分组
kubectl label node k8s-node1 node-group=team-a
kubectl label node k8s-node2 node-group=team-b

# 2. 创建租户命名空间
kubectl create ns team-a
kubectl create ns team-b

# 3. Team A 的 ResourceQuota + LimitRange
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "3"
    requests.memory: "4Gi"
    pods: "15"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: team-a-limits
  namespace: team-a
spec:
  limits:
  - type: Container
    default:
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
EOF

# 4. Team B 的 ResourceQuota
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-b-quota
  namespace: team-b
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "3Gi"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - type: Container
    default:
      cpu: "150m"
      memory: "192Mi"
    defaultRequest:
      cpu: "75m"
      memory: "96Mi"
EOF

# 5. Team A 部署应用到专属节点
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-a
  namespace: team-a
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app-a
  template:
    metadata:
      labels:
        app: app-a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: node-group
                operator: In
                values:
                - team-a
      containers:
      - name: app
        image: nginx:alpine
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
EOF

# 6. Team B 部署
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-b
  namespace: team-b
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app-b
  template:
    metadata:
      labels:
        app: app-b
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: node-group
                operator: In
                values:
                - team-b
      containers:
      - name: app
        image: httpd:alpine
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "300m"
            memory: "256Mi"
EOF

# 7. 验证配额
kubectl describe quota -n team-a
kubectl describe quota -n team-b

# 8. 验证 Pod 分布
kubectl get pod -n team-a -o wide
kubectl get pod -n team-b -o wide
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：多租户资源隔离与弹性伸缩**

```
【场景】公司两个团队共享 K8s 集群

【操作要求】

1. 命名空间与标签：
   - ns: dev-team, prod-team
   - 节点标签 tier: k8s-node1→dev, k8s-node2→prod

2. dev-team 配置：
   - ResourceQuota: CPU 2 核, Memory 4Gi, Pod ≤ 10
   - LimitRange: 默认 requests cpu 100m/mem 128Mi
   - Deployment dev-app: 2 副本, nginx:alpine
     * nodeAffinity: tier=dev
     * HPA: CPU 50%, min 2, max 5

3. prod-team 配置：
   - ResourceQuota: CPU 4 核, Memory 8Gi, Pod ≤ 20
   - LimitRange: 默认 requests cpu 200m/mem 256Mi
   - Deployment prod-api: 3 副本, httpd:alpine
     * nodeAffinity: tier=prod
     * podAntiAffinity: 按 hostname 分散
     * HPA: CPU 70%, min 3, max 10
   - Deployment prod-worker: 2 副本, busybox (sleep 3600)
     * nodeAffinity: tier=prod

4. 验证：
   - 两个团队配额互不干扰
   - dev-app 全部在 dev 节点
   - prod 所有 Pod 在 prod 节点
   - prod-api 分散在不同节点
   - HPA 工作正常

【评分标准】
- 命名空间和标签（10 分）
- ResourceQuota 正确（15 分）
- LimitRange 正确（10 分）
- nodeAffinity 正确（20 分）
- podAntiAffinity 正确（15 分）
- HPA 配置（20 分）
- 整体隔离验证（10 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints[*].key` | 自定义列查看节点污点 | 快速扫描所有节点的污点分布 |
| `kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,NODE-SELECTOR:.spec.nodeSelector` | 自定义列查看 Pod 调度策略 | 同时显示 Pod 所在节点和 nodeSelector |
| `kubectl get pods -o wide --field-selector=spec.nodeName=<node>` | 筛选某节点上的 Pod | 迁移 Pod 前确认受影响范围 |
| `kubectl get pods -o wide --field-selector=status.phase=Pending` | 筛选 Pending Pod | 快速定位未调度的 Pod |
| `kubectl describe pod <pod> \| grep -A 5 "Node-Selectors\|Tolerations\|Affinity"` | 查看 Pod 调度要求 | 综合排错时快速了解 Pod 的调度偏好 |
| `kubectl patch deploy <name> -p '{"spec":{"template":{"spec":{"nodeSelector":{"key":"value"}}}}}'` | 给 Deployment 添加 nodeSelector | 触发滚动更新将 Pod 迁移到匹配节点 |
| `kubectl patch deploy <name> -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"key","operator":"Equal","value":"value","effect":"NoSchedule"}]}}}}'` | 给 Deployment 添加 Toleration | 允许 Pod 调度到有对应污点的节点 |
| `kubectl get events --sort-by=.metadata.creationTimestamp \| tail -20` | 最近 20 条事件 | 综合实战中快速了解集群正在发生什么 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：调度器 | https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/ |
| Kubernetes 官方：高级调度 | https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/ |
| Kubernetes 官方：Pod 优先级与抢占 | https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/ |
| Kubernetes 官方：资源管理 | https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
