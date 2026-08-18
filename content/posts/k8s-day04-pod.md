---
title: Day 04 - Pod 生命周期与多容器模式
module: M2-Pod与核心工作负载
day: 4
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- M1 完成，3 节点集群就绪
- kubectl 基本操作熟练
objectives:
- 理解 Pod 是 K8s 最小调度单元
- 掌握 Pod 生命周期各阶段
- 掌握 InitContainer 使用场景
- 掌握三种多容器模式
- 熟练配置 livenessProbe、readinessProbe、startupProbe
tags:
- Pod
- InitContainer
- Sidecar
- livenessProbe
- readinessProbe
date: '2026-08-18'
status: published
---

# 📘 Day 04：Pod 生命周期与多容器模式

## 🎯 今日目标

- [ ] 能画出 Pod 生命周期状态流转图
- [ ] 能创建含 InitContainer 的 Pod
- [ ] 能实现 Sidecar 模式的 Pod
- [ ] 能正确配置三种探针
- [ ] 能排查 Pod CrashLoopBackOff 问题

---

## 🧠 理论精讲（30 分钟）

### Pod 是什么

Pod 是 K8s **最小的调度单元**（不是容器！）。

```
┌───────────────────────── Pod ─────────────────────────┐
│                                                         │
│  共享网络命名空间（同一个 IP）                              │
│  共享 IPC 命名空间                                       │
│  共享 Volume（通过 volumes 声明）                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Container│  │ Container│  │ Container│  ← Sidecar   │
│  │   (主)   │  │  (辅助)  │  │  (辅助)  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│       │              │              │                   │
│       └──────────────┼──────────────┘                   │
│                      │                                  │
│              ┌───────┴────────┐                         │
│              │  shared volumes│                         │
│              └────────────────┘                         │
└─────────────────────────────────────────────────────────┘
```

### Pod 生命周期

```
Pending ──→ Running ──→ Succeeded（正常退出）
  │            │
  │            ├──→ Failed（异常退出）
  │            │
  │            └──→ Unknown（节点失联）
  │
  └──→ ContainerCreating（拉镜像、挂载卷）
```

### 三种多容器模式

| 模式 | 说明 | 典型场景 |
|------|------|---------|
| **Sidecar** | 辅助容器增强主容器 | 日志采集、配置热更新、代理 |
| **Ambassador** | 代理容器屏蔽外部复杂性 | 数据库代理、服务发现代理 |
| **Adapter** | 适配容器统一接口 | 日志格式转换、监控指标标准化 |

### 三种探针

| 探针 | 作用 | 失败后果 |
|------|------|---------|
| **livenessProbe** | 检查容器是否还活着 | 重启容器 |
| **readinessProbe** | 检查容器是否可接收流量 | 从 Service Endpoint 移除 |
| **startupProbe** | 检查容器是否启动完成 | 启动期间屏蔽 liveness 和 readiness |

---

## 🔧 动手实操（120 分钟）

### 练习 4.1：观察 Pod 完整生命周期

```bash
# 1. 创建 Pod 并实时观察
kubectl run lifecycle-pod --image=nginx:alpine --restart=Never

# 在另一个终端 watch
kubectl get pod lifecycle-pod -w
# 观察：Pending → ContainerCreating → Running

# 2. 查看详细信息
kubectl describe pod lifecycle-pod
# 重点关注 Events 部分

# 3. 进入容器看运行细节
kubectl exec lifecycle-pod -- cat /etc/nginx/conf.d/default.conf

# 4. 删除并观察终止过程（默认 30 秒优雅终止）
kubectl delete pod lifecycle-pod &
kubectl get pod lifecycle-pod -w
# 观察：Running → Terminating → 消失

# 5. 创建带较长 terminationGracePeriodSeconds 的 Pod
kubectl run graceful-pod --image=nginx:alpine --restart=Never \
  --overrides='{"spec":{"terminationGracePeriodSeconds":60}}'

# 验证
kubectl get pod graceful-pod -o jsonpath='{.spec.terminationGracePeriodSeconds}'
kubectl delete pod graceful-pod
```

---

### 练习 4.2：Sidecar 模式

```bash
# 创建 Sidecar Pod：主容器写日志，Sidecar 读取
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sidecar-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    args:
    - /bin/sh
    - -c
    - |
      i=0
      while true; do
        echo "$(date): log entry $i" >> /var/log/app.log
        i=$((i+1))
        sleep 2
      done
    volumeMounts:
    - name: logs
      mountPath: /var/log

  - name: log-reader
    image: busybox:1.36
    args:
    - /bin/sh
    - -c
    - tail -f /var/log/app.log
    volumeMounts:
    - name: logs
      mountPath: /var/log

  volumes:
  - name: logs
    emptyDir: {}
EOF

# 验证 Sidecar 能读到主容器的日志
kubectl logs sidecar-demo -c log-reader --tail=10

# 查看两个容器的状态
kubectl get pod sidecar-demo
# READY 2/2

# 清理
kubectl delete pod sidecar-demo
```

---

### 练习 4.3：InitContainer 等待依赖

```bash
# 第一步：创建需要等待的依赖 Service
kubectl create deploy backend --image=nginx:alpine --replicas=1
kubectl expose deploy backend --port=80

# 第二步：创建带 InitContainer 的 Pod
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  initContainers:
  - name: wait-for-backend
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      echo "Waiting for backend service..."
      until wget -q --spider http://backend-service.default.svc.cluster.local; do
        echo "Backend not ready yet..."
        sleep 2
      done
      echo "Backend is ready!"
  containers:
  - name: app
    image: busybox:1.36
    command:
    - sh
    - -c
    - echo "Main app started!" && sleep 3600
EOF

# 观察 InitContainer 执行
kubectl get pod init-demo -w
# 看到 STATUS 列：Init:0/1 → PodInitializing → Running

# 查看 InitContainer 日志
kubectl logs init-demo -c wait-for-backend

# 清理
kubectl delete pod init-demo
kubectl delete deploy backend
kubectl delete svc backend
```

---

### 练习 4.4：livenessProbe 排错实战

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: liveness-demo
spec:
  containers:
  - name: unhealthy
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      touch /tmp/healthy
      # 30 秒后删除健康标志文件，模拟程序故障
      sleep 30
      rm /tmp/healthy
      sleep 3600
    livenessProbe:
      exec:
        command:
        - cat
        - /tmp/healthy
      initialDelaySeconds: 5
      periodSeconds: 5
      failureThreshold: 3
EOF

# 持续观察 Pod 状态
kubectl get pod liveness-demo -w

# 另一个终端查看事件
kubectl describe pod liveness-demo | grep -A5 "Events"

# 预期：约 30 + 5*3 = 45 秒后 Pod 被重启
kubectl get pod liveness-demo
# RESTARTS 列从 0 递增

# 清理
kubectl delete pod liveness-demo
```

---

### 练习 4.5：readinessProbe 流量控制

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: readiness-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: readiness-demo
  template:
    metadata:
      labels:
        app: readiness-demo
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 3
          periodSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: readiness-svc
spec:
  selector:
    app: readiness-demo
  ports:
  - port: 80
    targetPort: 80
EOF

# 查看 Endpoint 变化
kubectl get endpoints readiness-svc -w
# Pod Ready 后 Endpoint 出现

# 模拟 Pod 不健康：修改 nginx 配置让 / 返回错误
# （略，比赛环境可能需要替代方案）

# 清理
kubectl delete deploy readiness-demo
kubectl delete svc readiness-svc
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：Pod CrashLoopBackOff

```bash
# 创建一个会立即退出的 Pod
kubectl run crash-demo --image=busybox:1.36 --restart=Always -- /bin/false

# 观察状态
kubectl get pod crash-demo
# STATUS: CrashLoopBackOff

# 查看上一次崩溃的日志
kubectl logs crash-demo --previous

# 查看事件
kubectl describe pod crash-demo | grep -A10 Events

# 进入容器调试（如果容器立即退出，无法 exec）
kubectl run debug-pod --image=busybox:1.36 --restart=Never -it --rm -- sh

# 清理
kubectl delete pod crash-demo
```

### 场景 2：READY 0/1 但状态 Running

```bash
# 创建一个配置了错误端口的 readinessProbe
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ready-fail
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    readinessProbe:
      httpGet:
        path: /
        port: 8080    # 错误端口！nginx 在 80
      initialDelaySeconds: 3
      periodSeconds: 3
EOF

# 观察
kubectl get pod ready-fail
# STATUS: Running   READY: 0/1

kubectl describe pod ready-fail | grep -A5 Readiness
# Warning  Unhealthy  Readiness probe failed: dial tcp ...:8080: connect: connection refused

# 修复：正确配置端口 → 直接重建 Pod（探针不可变）
kubectl delete pod ready-fail
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：多容器应用 Pod 设计**

```
【操作要求】

1. 创建一个 Pod，名称为 multi-container-app，包含：
   - 1 个 InitContainer（名称为 init-setup）：
     * 镜像 busybox:1.36
     * 从 wget 获取一个测试 HTML 文件写入 /data/index.html
     * 共享卷 data-volume
   - 1 个主容器（名称为 web-server）：
     * 镜像 nginx:alpine
     * 将 /data/index.html 挂载到 /usr/share/nginx/html/index.html
     * 配置 readinessProbe：HTTP GET /，端口 80
     * 配置 livenessProbe：HTTP GET /，端口 80，
       initialDelaySeconds: 10, periodSeconds: 5
   - 1 个 Sidecar 容器（名称为 health-checker）：
     * 镜像 busybox:1.36
     * 每 10 秒执行 wget -q --spider http://localhost 并输出状态
     * 共享网络命名空间（同 Pod 内自然共享）

2. 验证：
   - 所有容器正常运行（kubectl get pod 显示 2/2 Ready）
   - InitContainer 执行成功（查看日志）
   - Sidecar 能访问 localhost 的 nginx

3. 排错：
   - 修改主容器端口为 8080（通过环境变量 NGINX_PORT=8080 或其他方式）
     观察 readiness 探针是否失败

【提交物】
- 完整的 Pod YAML
- 每步骤的验证命令截图或输出
- 遇到的问题和排查过程

【评分标准】
- YAML 结构正确（30 分）
- Pod 状态 2/2 Ready（30 分）
- InitContainer 执行成功（15 分）
- 探针配置正确（15 分）
- 排错分析（10 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl run nginx --image=nginx:alpine` | 快速创建 Pod | 直接创建单个 Pod（非 Deployment） |
| `kubectl run nginx --image=nginx:alpine --dry-run=client -o yaml > pod.yaml` | 生成 Pod YAML | 最佳 YAML 生成方式，比手写快且不出错 |
| `kubectl get pods -o wide` | Pod + 节点 + IP | 定位 Pod 运行位置 |
| `kubectl get pods -w` | 实时监控 Pod 状态变化 | 观察 Pod 从 Pending → Running 全过程 |
| `kubectl describe pod <pod>` | Pod 详细信息 | Events 段包含调度决策、镜像拉取状态、容器启停原因 |
| `kubectl logs <pod> -c <container> --tail=20` | 指定容器最后 20 行日志 | 多容器模式必须用 -c 指定 |
| `kubectl logs <pod> --all-containers=true` | 所有容器日志 | 一次性查看 Pod 内全部容器输出 |
| `kubectl exec <pod> -- <cmd>` | 在容器内执行命令 | 用于健康检查、调试 |
| `kubectl exec -it <pod> -- /bin/sh` | 交互式进入容器 | 查看文件系统、进程、网络连通性 |
| `kubectl port-forward pod/<pod> 8080:80` | 本地端口转发到 Pod | 无需 Service 直接访问 Pod 端口 |
| `kubectl delete pod <pod>` | 删除 Pod | 优雅终止（默认 30s） |
| `kubectl delete pod <pod> --force --grace-period=0` | 强制立即删除 | 卡在 Terminating 时救急 |
| `kubectl delete pod <pod> --now` | 立即删除 Pod | `--now` = `--grace-period=1` |
| `kubectl wait --for=condition=Ready pod/<pod>` | 等待 Pod 就绪 | 脚本中阻塞直到 Pod Ready |
| `kubectl cp <pod>:<path> <local-path>` | 从 Pod 复制文件 | 双向可操作 |
| `kubectl top pods` | Pod 实时资源用量 | 需安装 metrics-server |
| `kubectl get events --field-selector involvedObject.name=<pod>` | 查看特定 Pod 的 Event | 比 describe 更轻量 |
| `kubectl debug -it <pod> --image=busybox --target=<container>` | 调试容器（临时容器） | 1.25+ 支持，不影响原容器运行 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：Pod | https://kubernetes.io/docs/concepts/workloads/pods/ |
| Kubernetes 官方：Pod 生命周期 | https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ |
| Kubernetes 官方：Init 容器 | https://kubernetes.io/docs/concepts/workloads/pods/init-containers/ |
| Kubernetes 官方：探针配置 | https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/ |
| Kubernetes 官方：边车容器 | https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/ |
| Kubernetes 官方：临时容器调试 | https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/#ephemeral-container |
