---
title: Day 17 - 资源限制、QoS 与 HPA
module: M5-调度与资源管理
day: 17
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- Day 16 完成，理解调度基础
objectives:
- 掌握 requests 和 limits 的区别
- 理解 QoS 三种等级及其驱逐优先级
- 掌握 LimitRange 和 ResourceQuota
- 配置 HPA 实现自动扩缩容
tags:
- requests
- limits
- QoS
- LimitRange
- ResourceQuota
- HPA
date: '2026-08-18'
status: published
---

# 📘 Day 17：资源限制、QoS 与 HPA

## 🎯 今日目标

- [ ] 理解 requests ≠ limits 的区别与作用
- [ ] 能判断 Pod 的 QoS 等级
- [ ] 会用 LimitRange 限制默认资源
- [ ] 会用 ResourceQuota 限制命名空间
- [ ] 用 HPA 实现自动伸缩

---

## 🧠 理论精讲（30 分钟）

### requests vs limits

| 参数 | 含义 | 调度影响 |
|------|------|---------|
| **requests** | 保证分配的资源 | 调度器按此值找节点 |
| **limits** | 资源使用上限 | 超出即被 throttle/杀死 |

```yaml
resources:
  requests:
    cpu: "200m"      # 保证 0.2 核
    memory: "256Mi"  # 保证 256M 内存
  limits:
    cpu: "500m"      # 最多用 0.5 核
    memory: "512Mi"  # 最多用 512M 内存
```

### QoS 等级

| 等级 | 条件 | 驱逐优先级 |
|------|------|-----------|
| **Guaranteed** | requests == limits（两者都设且相等） | 最低 |
| **Burstable** | requests < limits（至少一个容器设了 requests） | 中等 |
| **BestEffort** | 未设任何 requests/limits | 最高（最先被驱逐） |

### HPA 公式

```
期望副本数 = ceil(当前副本数 × (当前指标值 / 目标指标值))
```

---

## 🔧 动手实操（120 分钟）

### 练习 17.1：requests 与 limits

```bash
# 1. 创建不同资源规格的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
  - name: app
    image: nginx:alpine
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "100m"
        memory: "128Mi"
---
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
  - name: app
    image: nginx:alpine
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
---
apiVersion: v1
kind: Pod
metadata:
  name: beste-ffort-pod
spec:
  containers:
  - name: app
    image: nginx:alpine
EOF

# 2. 查看 QoS 等级
kubectl get pod guaranteed-pod -o jsonpath='{.status.qosClass}'
echo
# Guaranteed

kubectl get pod burstable-pod -o jsonpath='{.status.qosClass}'
echo
# Burstable

kubectl get pod beste-ffort-pod -o jsonpath='{.status.qosClass}'
echo
# BestEffort

# 3. 模拟内存超限（OOMKilled）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: oom-pod
spec:
  containers:
  - name: mem-eater
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      # 分配超过 limit 的内存
      dd if=/dev/zero of=/dev/shm/bigfile bs=100M count=10
      sleep 3600
    resources:
      limits:
        memory: "50Mi"
EOF

kubectl get pod oom-pod -w
# 观察 RESTARTS 递增，Last State: OOMKilled

kubectl describe pod oom-pod | grep -A5 "Last State"

# 4. 清理
kubectl delete pod guaranteed-pod burstable-pod beste-ffort-pod oom-pod
```

---

### 练习 17.2：LimitRange

```bash
# 创建命名空间
kubectl create ns resource-lab

# 创建 LimitRange
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: resource-lab
spec:
  limits:
  - type: Container
    default:
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    max:
      cpu: "1"
      memory: "1Gi"
    min:
      cpu: "50m"
      memory: "64Mi"
EOF

# 创建不设 resources 的 Pod（自动应用默认值）
kubectl run auto-pod --image=nginx:alpine -n resource-lab

# 验证自动注入
kubectl get pod auto-pod -n resource-lab -o yaml | grep -A8 resources
# 应有默认的 requests 和 limits

# 尝试创建超过 max 的 Pod（应被拒绝）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: over-limit-pod
  namespace: resource-lab
spec:
  containers:
  - name: app
    image: nginx:alpine
    resources:
      limits:
        cpu: "2"          # 超过 max.cpu=1
        memory: "256Mi"
EOF
# Error: [cpu: Invalid value: "2": must be less than or equal to cpu limit]

# 清理
kubectl delete pod auto-pod -n resource-lab
```

---

### 练习 17.3：ResourceQuota

```bash
# 创建 ResourceQuota
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: resource-lab
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "2Gi"
    limits.cpu: "4"
    limits.memory: "4Gi"
    pods: "10"
    persistentvolumeclaims: "5"
    services: "5"
EOF

# 查看配额
kubectl describe quota team-quota -n resource-lab

# 创建 Deployment 测试配额消耗
kubectl create deploy quota-test -n resource-lab --image=nginx:alpine --replicas=5

# 查看配额使用情况
kubectl describe quota team-quota -n resource-lab
# 可以看到 Used vs Hard

# 清理
kubectl delete deploy quota-test -n resource-lab
```

---

### 练习 17.4：HPA 自动伸缩

```bash
# 0. 确保 metrics-server 已安装
kubectl get pods -n kube-system -l k8s-app=metrics-server
# 如果没有，先安装：
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 1. 创建 Deployment（带资源请求）
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hpa-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hpa-demo
  template:
    metadata:
      labels:
        app: hpa-demo
    spec:
      containers:
      - name: web
        image: nginx:alpine
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "128Mi"
EOF

kubectl expose deploy hpa-demo --port=80

# 2. 创建 HPA
kubectl autoscale deployment hpa-demo --cpu=50% --min=1 --max=5

# 3. 查看 HPA
kubectl get hpa
# NAME       REFERENCE             TARGETS   MINPODS   MAXPODS   REPLICAS
# hpa-demo   Deployment/hpa-demo   0%/50%    1         5         1

kubectl describe hpa hpa-demo

# 4. 生成负载
kubectl run load-generator --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c 'while true; do wget -q -O- http://hpa-demo; done'

# 在另一个终端观察 HPA
kubectl get hpa hpa-demo -w
# 观察 TARGETS 上升，REPLICAS 自动增加

# 5. Ctrl+C 停止负载，观察缩容
kubectl get hpa hpa-demo -w
# REPLICAS 逐渐减少回 1

# 6. 清理
kubectl delete hpa hpa-demo
kubectl delete deploy hpa-demo
kubectl delete svc hpa-demo
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：HPA 不工作

```bash
# 排查清单
# 1. metrics-server 是否运行？
kubectl get pods -n kube-system -l k8s-app=metrics-server

# 2. 能否获取到指标？
kubectl top pods
kubectl top nodes

# 3. Deployment 是否设置了 resources.requests？
kubectl get deploy <name> -o yaml | grep -A5 resources
# HPA 基于百分比需要 requests 做基准

# 4. HPA 状态
kubectl describe hpa <name>
# 看 Events 区域的错误信息
```

### 场景 2：Pod 被驱逐（Evicted）

```bash
# 查看被驱逐的 Pod
kubectl get pods --field-selector=status.phase=Failed

# 查看驱逐原因
kubectl describe pod <evicted-pod>
# The node was low on resource: memory.
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：资源管理与自动伸缩**

```
【操作要求】

1. 创建命名空间 resource-exam

2. 创建 LimitRange：
   - 容器默认 requests：cpu 100m, memory 128Mi
   - 容器默认 limits：cpu 500m, memory 256Mi
   - max cpu: 1, max memory: 512Mi

3. 创建 ResourceQuota：
   - 最多 10 个 Pod
   - 总 requests.cpu 不超过 2 核
   - 总 requests.memory 不超过 2Gi

4. 创建 Deployment web-api（2 副本，nginx:alpine）：
   - requests: cpu 100m, memory 128Mi
   - limits: cpu 200m, memory 256Mi
   - QoS 应为 Guaranteed?（检查：不是，因为 requests ≠ limits）
   - 修改使其达到 Guaranteed

5. 配置 HPA：
   - 基于 CPU，目标 60%
   - min 2, max 8

6. 验证：
   - kubectl describe quota -n resource-exam
   - kubectl get hpa
   - kubectl get pod 确认 QoS 等级

【评分标准】
- LimitRange 正确（15 分）
- ResourceQuota 正确（15 分）
- QoS Guaranteed 实现（20 分）
- HPA 配置正确（20 分）
- 配额验证（15 分）
- 整体正确性（15 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl set resources deploy/<name> -c=<container> --limits=cpu=200m,memory=256Mi --requests=cpu=100m,memory=128Mi` | 设置容器资源限制 | 触发滚动更新重建 Pod |
| `kubectl describe pod <pod> \| grep -A 5 "Requests\|Limits"` | 查看 Pod 资源配置 | 确认 requests/limits 是否生效 |
| `kubectl describe node <node> \| grep -A 5 "Allocated"` | 查看节点已分配资源 | CPU/Memory 分配比例，判断节点是否过载 |
| `kubectl top pods -A --sort-by=cpu` | 按 CPU 排序 Pod 用量 | 找出 CPU 消耗最高的 Pod |
| `kubectl top pods -A --sort-by=memory` | 按内存排序 Pod 用量 | 找出内存消耗最高的 Pod |
| `kubectl get pod <pod> -o jsonpath='{.status.qosClass}'` | 查看 Pod QoS 等级 | 返回 Guaranteed/Burstable/BestEffort |
| `kubectl get limitrange -A` | 列出所有 LimitRange | 命名空间级默认资源限制 |
| `kubectl describe limitrange <name> -n <ns>` | 查看 LimitRange 详情 | 确认默认 requests/limits 和最大/最小限制 |
| `kubectl get resourcequota -A` | 列出所有 ResourceQuota | 命名空间级资源配额 |
| `kubectl describe resourcequota <name> -n <ns>` | 查看 ResourceQuota 详情 | 已用 vs 硬限制对比 |
| `kubectl get hpa` | 列出水平自动扩缩器 | 查看当前/目标 CPU/内存使用率 |
| `kubectl describe hpa <name>` | HPA 详情 | Metrics 段显示当前值 vs 目标值，Events 显示扩缩事件 |
| `kubectl autoscale deploy <name> --min=2 --max=10 --cpu=80%` | 创建 HPA | 基于 CPU 使用率自动扩缩副本数 |
| `kubectl delete hpa <name>` | 删除 HPA | 删除后副本数不再自动调整 |
| `kubectl get vpa` | 列出垂直自动扩缩器 | 需安装 VPA；自动调整 Pod requests/limits |
| `kubectl get events --field-selector=reason=FailedScheduling` | 查看调度失败事件 | 资源不足导致 Pending 时的排错入口 |
| `kubectl describe pod <pod> \| grep -A 10 Events` | 查看 Pod 调度事件 | 确认是否因资源不足 Pending |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：资源管理 | https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| Kubernetes 官方：QoS 等级 | https://kubernetes.io/docs/tasks/configure-pod-container/quality-service-pod/ |
| Kubernetes 官方：LimitRange | https://kubernetes.io/docs/concepts/policy/limit-range/ |
| Kubernetes 官方：ResourceQuota | https://kubernetes.io/docs/concepts/policy/resource-quotas/ |
| Kubernetes 官方：HPA | https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ |
| Kubernetes 官方：VPA | https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler |
