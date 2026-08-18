---
title: Day 07 - Pod 资源综合实战
module: M2-Pod与核心工作负载
day: 7
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- M2 Day 04-06 全部完成
objectives:
- 从零构建完整微服务应用（多个工作负载类型）
- 故障演练：Pod 删除、进程 kill、节点宕机
- 版本演练：滚动更新 + 回滚全流程
- 工作负载选型决策训练
tags:
- 综合实战
- 故障演练
- 微服务
- 工作负载选型
date: '2026-08-18'
status: published
---

# 📘 Day 07：Pod 资源综合实战

## 🎯 今日目标

- [ ] 在一个命名空间内从零搭建多类型工作负载
- [ ] 通过故障注入验证 K8s 自愈能力
- [ ] 完成完整的版本发布与回滚流程
- [ ] 能根据业务需求选择正确的工作负载类型

---

## 🧠 理论精讲（10 分钟）

### 工作负载选型决策树

```
需要运行容器？
├── 需要每节点一个？──→ DaemonSet
├── 需要稳定网络标识 + 持久存储？──→ StatefulSet
├── 一次性任务？──→ Job
├── 定时任务？──→ CronJob
├── 无状态、需要滚动更新？──→ Deployment
└── 单个 Pod，不需要自愈？──→ Pod（restartPolicy: Never）
```

---

## 🔧 动手实操（150 分钟）

### 练习 7.1：从零构建微服务应用

```bash
# 创建独立命名空间
kubectl create ns microshop

# === 1. 数据库层（StatefulSet） ===
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: db-svc
  namespace: microshop
spec:
  clusterIP: None
  selector:
    app: shop-db
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: shop-db
  namespace: microshop
spec:
  serviceName: db-svc
  replicas: 1
  selector:
    matchLabels:
      app: shop-db
  template:
    metadata:
      labels:
        app: shop-db
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: db-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: db-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Mi
EOF

# === 2. 后端服务（Deployment） ===
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: microshop
spec:
  replicas: 2
  selector:
    matchLabels:
      app: shop-backend
  template:
    metadata:
      labels:
        app: shop-backend
    spec:
      containers:
      - name: api
        image: nginx:alpine
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 3
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
EOF

kubectl expose deploy backend -n microshop --name=backend-svc --port=80

# === 3. 前端服务（Deployment） ===
kubectl create deploy frontend -n microshop --image=nginx:alpine --replicas=3
kubectl expose deploy frontend -n microshop --name=frontend-svc --port=80

# === 4. 日志采集（DaemonSet） ===
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-agent
  namespace: microshop
spec:
  selector:
    matchLabels:
      app: log-agent
  template:
    metadata:
      labels:
        app: log-agent
    spec:
      containers:
      - name: logger
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          while true; do
            echo "[$(date)] Node: $(hostname) - collecting logs"
            sleep 10
          done
EOF

# === 5. 定时清理（CronJob） ===
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: log-cleanup
  namespace: microshop
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: busybox:1.36
            command:
            - sh
            - -c
            - echo "Cleaning old logs at $(date)"
          restartPolicy: Never
EOF

# 6. 验证全部资源
kubectl get all -n microshop
# 预期：
# - Pod: frontend×3, backend×2, shop-db-0×1, log-agent×3
# - Service: db-svc, backend-svc, frontend-svc
# - DaemonSet: log-agent
# - StatefulSet: shop-db
# - CronJob: log-cleanup
```

---

### 练习 7.2：故障演练

```bash
# 故障 1：删除 Pod（验证自愈）
kubectl get pod -n microshop -l app=shop-backend
POD_NAME=$(kubectl get pod -n microshop -l app=shop-backend -o name | head -1)
kubectl delete $POD_NAME -n microshop
kubectl get pod -n microshop -l app=shop-backend -w
# 观察：旧 Pod Terminating，新 Pod 自动创建并 Running

# 故障 2：杀掉容器进程（验证 livenessProbe）
BACKEND_POD=$(kubectl get pod -n microshop -l app=shop-backend -o name | head -1)
kubectl exec $BACKEND_POD -n microshop -- nginx -s stop
# 预期：livenessProbe 失败 → 容器重启
kubectl get $BACKEND_POD -n microshop -w
# RESTARTS 列递增

# 故障 3：缩容 frontend（验证可用性）
kubectl scale deploy/frontend -n microshop --replicas=1
kubectl get pod -n microshop -l app=shop-frontend
# 只保留 1 个

# 故障 4：模拟节点不可用（cordon）
kubectl cordon k8s-node1
# 注意：已有 Pod 不受影响，新 Pod 不调度到 node1

# 恢复
kubectl uncordon k8s-node1
kubectl scale deploy/frontend -n microshop --replicas=3
```

---

### 练习 7.3：版本演练

```bash
# 1. 记录当前版本
kubectl get deploy -n microshop backend -o jsonpath='{.spec.template.spec.containers[0].image}'
# nginx:alpine

# 2. 更新 backend
kubectl set image deploy/backend -n microshop api=nginx:alpine-slim
kubectl annotate deploy/backend -n microshop kubernetes.io/change-cause="switch to slim image"
kubectl rollout status deploy/backend -n microshop

# 3. 查看历史
kubectl rollout history deploy/backend -n microshop

# 4. 制造一个失败更新
kubectl set image deploy/backend -n microshop api=nginx:9.9.9-invalid
kubectl annotate deploy/backend -n microshop kubernetes.io/change-cause="invalid update"

# 5. 发现失败，立即回滚
kubectl rollout undo deploy/backend -n microshop
kubectl rollout status deploy/backend -n microshop

# 6. 最终验证
kubectl get deploy -n microshop backend
kubectl rollout history deploy/backend -n microshop
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：微服务应用全流程部署**

```
【场景】
为一个电商系统部署基础设施，包含缓存层、API 层、Web 层和监控组件。

【环境要求】
- 新建命名空间：ecommerce

【操作要求】
1. 缓存层：StatefulSet redis-cache（2 副本）
   - 镜像 redis:7-alpine
   - Headless Service redis-cache-svc
   - 每个 Pod 独立 PVC（50Mi）

2. API 层：Deployment api-server（3 副本）
   - 镜像 nginx:alpine
   - 配置 livenessProbe + readinessProbe
   - 资源限制：cpu 100m, memory 128Mi
   - 滚动策略：maxSurge=1, maxUnavailable=0
   - ClusterIP Service api-svc

3. Web 层：Deployment web-front（3 副本）
   - 镜像 httpd:alpine
   - ClusterIP Service web-svc

4. 监控层：DaemonSet node-exporter
   - 镜像 busybox:1.36
   - 每 5 秒输出主机名和时间

5. 备份任务：CronJob data-backup
   - 镜像 busybox:1.36
   - 每 15 分钟执行备份命令

6. 故障测试：
   - 删除一个 api-server Pod → 验证自愈
   - 缩容 redis-cache 到 1 → 观察顺序缩容
   - 模拟 API 版本更新并回滚

【评分标准】
- 所有资源正确创建（40 分）
- Service 正确关联（15 分）
- 探针配置正确（15 分）
- 故障测试通过（20 分）
- 版本回滚成功（10 分）
```

---

## 🧹 环境清理

```bash
# 练习结束后清理
kubectl delete ns microshop
kubectl delete ns ecommerce
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl apply -f <manifest>.yaml` | 声明式部署资源 | 综合实战中一次性部署多种资源 |
| `kubectl get all` | 查看所有资源 | Pod/Service/Deploy/RS/StatefulSet/DaemonSet/Job 一览 |
| `kubectl get pods --show-labels` | Pod + 标签 | 验证标签是否与 Service Selector 匹配 |
| `kubectl get pods -L app,version` | 按指定标签列显示 Pod | `-L` 将标签值作为独立列展示 |
| `kubectl describe svc <name>` | Service 详情 | 查看 Endpoints 是否绑定到正确的 Pod |
| `kubectl get endpoints <svc>` | 查看 Service 后端 Endpoints | 为空说明 Selector 不匹配或 Pod 未就绪 |
| `kubectl run tmp --image=busybox --rm -it -- wget -O- http://<svc>:<port>` | 临时 Pod 测试服务连通性 | `--rm` 退出即删，测试网络首选 |
| `kubectl exec <pod> -- env` | 查看容器环境变量 | 验证 ConfigMap/Secret 注入是否正确 |
| `kubectl exec <pod> -- cat /etc/config/key` | 查看挂载的配置文件 | 验证 ConfigMap/Secret 挂载内容 |
| `kubectl exec <pod> -- nslookup <svc-name>` | 验证 DNS 解析 | 确认 CoreDNS 正常工作 |
| `kubectl -n <ns> logs -l app=<name> --tail=20` | 按标签批量查看日志 | `-l` 按标签选择器筛选 Pod |
| `kubectl top pods --sort-by=cpu` | 按 CPU 排序 Pod 用量 | 找出资源消耗最大的 Pod |
| `kubectl get events --sort-by=.metadata.creationTimestamp` | 按时间排序事件 | 按时间线排查问题 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：工作负载 | https://kubernetes.io/docs/concepts/workloads/ |
| Kubernetes 官方：标签与选择器 | https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/ |
| Kubernetes 官方：Service | https://kubernetes.io/docs/concepts/services-networking/service/ |
| Kubernetes 官方：应用排错 | https://kubernetes.io/docs/tasks/debug/debug-application/ |
