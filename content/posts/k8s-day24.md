---
title: Day 24 - 故障排查实战
module: M7-监控日志与排错
day: 24
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M7 Day 22-23 完成
- 所有前序模块完成
objectives:
- 掌握 K8s 故障排查方法论
- 排查 Pod/Node/Network/Storage 各类故障
- 能写出标准化的排查报告
tags:
- 故障排查
- 排错方法论
- Pod 故障
- 节点故障
- 网络故障
date: '2026-08-18'
status: published
---

# 📘 Day 24：故障排查实战

## 🎯 今日目标

- [ ] 掌握 K8s 系统化排错方法
- [ ] 能独立排查 Pod CrashLoopBackOff
- [ ] 能排查 Service 不通的问题
- [ ] 能排查 PVC 绑定失败

---

## 🧠 理论精讲（30 分钟）

### 系统化排错方法论

```
第 1 层：现象确认
  kubectl get pods/nodes/svc → 确认哪个对象出问题？

第 2 层：事件查看
  kubectl describe <resource> → 看 Events 区域

第 3 层：日志分析
  kubectl logs <pod> → 应用日志
  journalctl -u kubelet → 系统日志

第 4 层：深入诊断
  kubectl exec → 进容器验证
  网络： nc / curl / nslookup
  存储： ls / df / mount

第 5 层：关联分析
  有没有 NetworkPolicy？RBAC？ResourceQuota？
```

### 常见故障速查表

| 现象 | 可能原因 | 排查命令 |
|------|---------|---------|
| `Pending` | 资源不足/调度失败 | `describe pod` |
| `CrashLoopBackOff` | 应用崩溃/OOM | `logs --previous` |
| `ImagePullBackOff` | 镜像问题 | `describe pod` |
| `ContainerCreating` | 卷挂载/CNI | `describe pod` |
| `NotReady` (Node) | kubelet 问题 | `describe node` |
| Service 不通 | selector/label | `get endpoints` |
| PVC Pending | 无 PV/SC | `describe pvc` |

---

## 🔧 动手实操（120 分钟）

### 练习 24.1：Pod 故障排查

**故障 1：CrashLoopBackOff**

```bash
# 创建故意崩溃的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: crash-demo
spec:
  containers:
  - name: bad-app
    image: busybox:1.36
    command: ["sh", "-c", "echo 'Starting...'; sleep 5; exit 1"]
EOF

# 排查流程：
# Step 1: 确认状态
kubectl get pod crash-demo
# STATUS: CrashLoopBackOff

# Step 2: 查看事件
kubectl describe pod crash-demo | grep -A15 Events
# Back-off restarting failed container

# Step 3: 查看日志（包括上一次）
kubectl logs crash-demo
kubectl logs crash-demo --previous
# Starting...

# Step 4: 结论 → 应用启动后 exit 1，需要检查应用配置
kubectl delete pod crash-demo
```

**故障 2：OOMKilled**

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
spec:
  containers:
  - name: mem-hog
    image: busybox:1.36
    command:
    - sh
    - -c
    - dd if=/dev/zero of=/dev/shm/big bs=50M count=10
    resources:
      limits:
        memory: "100Mi"
EOF

# 排查
kubectl get pod oom-demo -w
# STATUS: OOMKilled

kubectl describe pod oom-demo | grep -A5 "State"
# Reason: OOMKilled

kubectl delete pod oom-demo
```

**故障 3：ImagePullBackOff**

```bash
kubectl run bad-image --image=notexist/image:v99 --restart=Never

kubectl get pod bad-image
# STATUS: ImagePullBackOff / ErrImagePull

kubectl describe pod bad-image | grep -A5 Events
# Failed to pull image: notexist/image:v99

kubectl delete pod bad-image
```

---

### 练习 24.2：Service 网络故障排查

```bash
# 模拟 Service 不通的场景
# 1. 创建后端但故意 label 不匹配
kubectl create deploy web-backend --image=nginx:alpine --replicas=2

# 2. 创建 Service 选错误的 label
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  selector:
    app: non-existent     # 故意不匹配！
  ports:
  - port: 80
EOF

# 3. 排查
kubectl get endpoints bad-svc
# ENDPOINTS: <none>  ← 问题！

kubectl get pod -l app=web-backend --show-labels
# 实际 label: app=web-backend

kubectl get svc bad-svc -o jsonpath='{.spec.selector}'
# {"app":"non-existent"}

# 4. 修复
kubectl patch svc bad-svc -p '{"spec":{"selector":{"app":"web-backend"}}}'
kubectl get endpoints bad-svc
# 现在有 ENDPOINTS 了

# 5. 清理
kubectl delete deploy web-backend
kubectl delete svc bad-svc
```

---

### 练习 24.3：节点故障排查

```bash
# 模拟节点问题
# 1. 对节点加污点使其不可调度
kubectl taint node k8s-node1 test=block:NoSchedule

# 2. 创建 Pod 观察现象
kubectl run taint-test --image=nginx:alpine
kubectl get pod taint-test -o wide
# 被调度到其他节点

# 3. 如果所有节点都有污点？
kubectl describe pod taint-test | grep -A10 Events
# Warning  FailedScheduling  ...

# 4. 排查节点状况
kubectl describe node k8s-node1 | grep -A10 Taints
kubectl describe node k8s-node1 | grep -A5 Conditions
# MemoryPressure / DiskPressure / PIDPressure

# 5. 恢复
kubectl taint node k8s-node1 test-
kubectl delete pod taint-test
```

---

### 练习 24.4：存储故障排查

```bash
# 模拟 PVC 无法绑定
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: impossible-pvc
spec:
  accessModes: ["ReadWriteMany"]
  resources:
    requests:
      storage: 100Ti    # 不可能有的容量
EOF

# 排查
kubectl get pvc impossible-pvc
# STATUS: Pending

kubectl describe pvc impossible-pvc | grep -A5 Events
# "no persistent volumes available..."

kubectl get pv
# 没有 100Ti 的 PV

kubectl delete pvc impossible-pvc
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：故障诊断竞赛**

```
【场景】以下每个故障独立出现。针对每个故障写出：
1. 排查步骤（具体命令）
2. 可能的根因
3. 解决方案

【故障列表】

故障 1：Pod 状态 CrashLoopBackOff
- Deployment web-app 的 Pod 不断重启
- kubectl get pod 显示 RESTARTS=15

故障 2：Service 无法访问
- 集群内 curl http://api-svc 超时
- kubectl get svc api-svc 正常
- kubectl get endpoints api-svc 为空

故障 3：PVC 一直 Pending
- 创建了 PVC，状态始终 Pending
- kubectl get sc 为空

故障 4：Pod 调度失败
- 4 节点集群，创建 10 副本 Deployment
- 第 8 个 Pod 一直是 Pending
- kubectl describe pod 显示 Insufficient cpu

故障 5：DNS 解析失败
- Pod 内 nslookup kubernetes.default 返回 server can't find
- CoreDNS Pod Running 正常

【评分标准】
- 每个故障：排查步骤(10分) + 根因分析(5分) + 解决方案(5分)
- 总计 100 分
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl describe pod <pod> \| tail -30` | Pod Events（排错第一入口） | 80% 的故障在 Events 里能找到原因 |
| `kubectl get events --sort-by=.lastTimestamp` | 按时间排序所有事件 | 全局视角查看集群正在发生什么 |
| `kubectl get events -w` | 实时监听事件 | 操作时开一个终端 watch，观察连锁反应 |
| `kubectl get events --field-selector type=Warning` | 只看 Warning 事件 | 过滤 Normal 噪音，聚焦异常 |
| `kubectl get pods --field-selector=status.phase=Pending` | 筛选 Pending Pod | 调度失败/镜像拉取失败 |
| `kubectl get pods --field-selector=status.phase=Failed` | 筛选 Failed Pod | CrashLoopBackOff/Error/Completed(exit≠0) |
| `kubectl get pods --field-selector=status.phase!=Running` | 筛选非 Running Pod | 一次性找出所有问题 Pod |
| `kubectl describe pod <pod> \| grep -A 5 "State:\|Ready:\|Restart"` | 容器状态摘要 | 快速确认容器是 Waiting/Running/Terminated |
| `kubectl describe pod <pod> \| grep -B 2 "Exit Code"` | 查看容器退出码 | Exit Code 137=OOMKilled, 143=SIGTERM, 1=应用错误 |
| `kubectl logs <pod> --previous` | 上一次崩溃的日志 | CrashLoopBackOff 时当前容器可能还没产生日志 |
| `kubectl -n kube-system logs kube-apiserver-<node>` | apiserver 日志 | 集群入口故障，大量 5xx/超时根因在此 |
| `kubectl -n kube-system logs -l k8s-app=kube-dns --tail=50` | CoreDNS 日志 | DNS 解析超时/失败时的排查 |
| `kubectl -n kube-system logs -l k8s-app=calico-node --tail=50` | CNI 日志 | 网络不通、Pod IP 分配失败 |
| `journalctl -u kubelet --since "5 min ago" --no-pager` | kubelet 近 5 分钟日志 | 无需 `--no-pager` 短输出更易读 |
| `kubectl cluster-info dump \| grep -i "error\|failed" \| head -30` | 集群诊断 + 错误过滤 | 输出所有组件的日志摘要 |
| `kubectl get componentstatuses` | 控制平面组件健康 | 1.19+ 建议用 `--raw='/readyz?verbose'` |
| `kubectl get nodes -o json \| jq '.items[] \| {name:.metadata.name, conditions:.status.conditions}'` | 节点 Conditions JSON 输出 | 结构化的节点健康状况 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：排错指南 | https://kubernetes.io/docs/tasks/debug/ |
| Kubernetes 官方：排错 Pod | https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/ |
| Kubernetes 官方：排错 Service | https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/ |
| Kubernetes 官方：排错集群 | https://kubernetes.io/docs/tasks/debug/debug-cluster/ |
| Kubernetes 官方：节点健康监控 | https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-summary/ |
| kubectl 排错速查表 | https://kubernetes.io/docs/reference/kubectl/quick-reference/ |
