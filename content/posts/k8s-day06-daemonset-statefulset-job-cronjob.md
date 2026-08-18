---
title: Day 06 - DaemonSet、StatefulSet、Job、CronJob
module: M2-Pod与核心工作负载
day: 6
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 05 完成，掌握 Deployment
objectives:
- 掌握 DaemonSet 的使用场景与配置
- 理解 StatefulSet 的有状态特性
- 掌握 Headless Service 与 StatefulSet 配合
- 掌握 Job/CronJob 的配置与调试
- 能用 volumeClaimTemplates 自动创建 PVC
tags:
- DaemonSet
- StatefulSet
- Headless Service
- Job
- CronJob
- volumeClaimTemplates
date: '2026-08-18'
status: published
---

# 📘 Day 06：DaemonSet、StatefulSet、Job、CronJob

## 🎯 今日目标

- [ ] 部署 DaemonSet 实现每节点一个采集 Pod
- [ ] 部署 StatefulSet 实现有状态应用
- [ ] 理解 StatefulSet Pod 的稳定网络标识
- [ ] 创建 Job 并行计算任务
- [ ] 创建 CronJob 定时任务

---

## 🧠 理论精讲（30 分钟）

### 四种工作负载对比

| 工作负载 | 副本特征 | Pod 标识 | 启动/停止顺序 | 典型场景 |
|----------|---------|---------|-------------|---------|
| **Deployment** | 可多可少，Pod 无差别 | 随机名（xxx-abcde-xyz） | 无顺序，并行 | 无状态 Web |
| **DaemonSet** | 每节点一个 | 节点名相关 | 无顺序 | 日志采集、监控 Agent |
| **StatefulSet** | 固定数量，每个唯一 | 有序序号（xxx-0, xxx-1） | 顺序启动，逆序停止 | 数据库、消息队列 |
| **Job** | 一次性，完成即止 | 随机名 | 无顺序 | 数据迁移、计算任务 |
| **CronJob** | 按定时规则创建 | 随机名 | 无顺序 | 定时备份、定时清理 |

### StatefulSet 核心特性

```
1. 稳定的网络标识：<sts-name>-<序号>.<headless-svc>.<ns>.svc.cluster.local
2. 稳定的持久存储：每个 Pod 有独立 PVC，Pod 重建后仍绑定同一 PVC
3. 有序部署和缩放：0→1→2→...，缩容时逆序
4. 有序滚动更新：N-1→N-2→...→0
```

### Job 关键参数

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `completions` | 需要成功完成多少次 | 1 |
| `parallelism` | 最大并行执行数 | 1 |
| `backoffLimit` | 失败重试次数 | 6 |
| `activeDeadlineSeconds` | 任务超时时间 | — |

---

## 🔧 动手实操（120 分钟）

### 练习 6.1：DaemonSet 日志采集器

```bash
# 1. 创建一些测试 Pod 分散在不同节点
kubectl create deploy test-app --image=nginx:alpine --replicas=5

# 2. 部署 DaemonSet 日志采集器
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-collector
spec:
  selector:
    matchLabels:
      app: log-collector
  template:
    metadata:
      labels:
        app: log-collector
    spec:
      containers:
      - name: collector
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          mkdir -p /host-data
          while true; do
            echo "[$(date)] Host: $(hostname)" >> /host-data/collector.log
            sleep 5
          done
        volumeMounts:
        - name: host-logs
          mountPath: /host-data
      volumes:
      - name: host-logs
        hostPath:
          path: /tmp/collector-logs
          type: DirectoryOrCreate
EOF

# 3. 验证每个节点都有一个 Pod
kubectl get pod -l app=log-collector -o wide
# 预期：3 个 Pod（每节点 1 个）

# 4. 验证数据写入
# 登录任一 worker 节点
ssh k8s-node1
cat /tmp/collector-logs/collector.log
# 看到采集日志

# 5. 查看 DaemonSet 状态
kubectl get ds log-collector
# DESIRED=3  CURRENT=3  READY=3

# 6. 清理
kubectl delete ds log-collector
kubectl delete deploy test-app
```

---

### 练习 6.2：StatefulSet 部署

```bash
# 1. 先创建 Headless Service（必须！）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: nginx-sts
spec:
  clusterIP: None          # Headless Service 的关键！
  selector:
    app: nginx-sts
  ports:
  - port: 80
    targetPort: 80
EOF

# 2. 部署 StatefulSet
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx-sts
spec:
  serviceName: nginx-sts
  replicas: 3
  selector:
    matchLabels:
      app: nginx-sts
  template:
    metadata:
      labels:
        app: nginx-sts
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: data
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Mi
EOF

# 3. 观察顺序创建（0→1→2）
kubectl get pod -l app=nginx-sts -w
# nginx-sts-0  Running
# nginx-sts-1  Running
# nginx-sts-2  Running

# 4. 验证网络标识
kubectl exec nginx-sts-0 -- hostname
# nginx-sts-0

kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup nginx-sts-0.nginx-sts.default.svc.cluster.local
# 返回 Pod IP

# 5. 验证 PVC 自动创建
kubectl get pvc
# 每个 Pod 独立 PVC：data-nginx-sts-0, data-nginx-sts-1, data-nginx-sts-2

# 6. 写入数据验证持久性
kubectl exec nginx-sts-0 -- sh -c 'echo "pod-0-data" > /usr/share/nginx/html/data.txt'

# 7. 删除 Pod 观察重建
kubectl delete pod nginx-sts-0
kubectl get pod nginx-sts-0 -w
# Pod 重建后名称仍然是 nginx-sts-0

# 8. 验证数据仍在（PVC 绑定未变）
kubectl exec nginx-sts-0 -- cat /usr/share/nginx/html/data.txt
# 输出：pod-0-data

# 9. 顺序缩容
kubectl scale sts nginx-sts --replicas=1
kubectl get pod -l app=nginx-sts -w
# 逆序终止：nginx-sts-2 Terminating → nginx-sts-1 Terminating

# 10. 扩容
kubectl scale sts nginx-sts --replicas=3

# 11. 清理
kubectl delete sts nginx-sts
kubectl delete svc nginx-sts
# ⚠️ PVC 不会自动删除，需要手动清理
kubectl delete pvc data-nginx-sts-0 data-nginx-sts-1 data-nginx-sts-2
```

---

### 练习 6.3：Job 并行计算

```bash
# 1. 基础 Job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: compute-pi
spec:
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.34
        command:
        - perl
        - -Mbignum=bpi
        - -wle
        - print bpi(200)
      restartPolicy: Never
  backoffLimit: 4
EOF

# 2. 观察 Job 执行
kubectl get job compute-pi -w
# COMPLETIONS 从 0/1 → 1/1

kubectl get pod -l job-name=compute-pi
# Pod 状态 Completed

# 3. 查看计算结果
kubectl logs job/compute-pi
# 输出 π 值

# 4. 并行 Job
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  completions: 6
  parallelism: 2
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          echo "Task $((JOB_COMPLETION_INDEX+1)) running on $(hostname)"
          sleep $(( RANDOM % 10 ))
          echo "Task done"
      restartPolicy: Never
  backoffLimit: 4
EOF

# 5. 观察并行执行
kubectl get pod -l job-name=parallel-job -w
# 每次最多 2 个 Pod 同时运行

kubectl get job parallel-job
# COMPLETIONS: 6/6

# 6. 清理
kubectl delete job compute-pi parallel-job
```

---

### 练习 6.4：CronJob 定时任务

```bash
# 1. 创建每分钟执行的 CronJob
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: health-checker
spec:
  schedule: "*/1 * * * *"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: checker
            image: busybox:1.36
            command:
            - sh
            - -c
            - |
              echo "[$(date)] Health check executed"
              echo "Checking DNS..."
              nslookup kubernetes.default.svc.cluster.local
              echo "OK"
          restartPolicy: Never
      backoffLimit: 2
EOF

# 2. 查看 CronJob
kubectl get cj
kubectl describe cj health-checker

# 3. 等待 1～2 分钟，查看自动创建的 Job
kubectl get jobs
# 看到 health-checker-<timestamp>

# 4. 查看 Job 创建的 Pod
kubectl get pod -l job-name

# 5. 查看日志
kubectl logs job/health-checker-<timestamp>

# 6. 手动触发一次（不再等待定时器）
kubectl create job --from=cronjob/health-checker manual-run

# 7. 查看手动任务的日志
kubectl logs job/manual-run

# 8. 清理
kubectl delete cj health-checker
kubectl delete job manual-run
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：StatefulSet Pod 一直 Pending

```bash
# 原因 1：PVC 无法绑定
kubectl get pvc
# STATUS: Pending

kubectl describe pvc <pvc-name>
# 看到 "no persistent volumes available..."

# 解决方案：
# - 检查 StorageClass 是否存在：kubectl get sc
# - 创建 PV 或确保 default StorageClass 可用
```

### 场景 2：CronJob 不触发

```bash
# 排查步骤

# 1. 检查 CronJob 配置
kubectl describe cj <name>
# 查看 Last Schedule Time

# 2. 检查 concurrencyPolicy
kubectl get cj <name> -o yaml | grep concurrencyPolicy
# Allow / Forbid / Replace

# 3. 检查 startingDeadlineSeconds
kubectl get cj <name> -o yaml | grep startingDeadlineSeconds

# 4. 检查 Job 是否被创建
kubectl get jobs --sort-by=.metadata.creationTimestamp

# 常见原因：
# - schedule 语法错误
# - concurrencyPolicy=Forbid 且上一次 Job 未完成
# - startingDeadlineSeconds 过期
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：工作负载综合部署**

```
【操作要求】

1. 部署 StatefulSet：
   - 名称：redis-cluster
   - 副本数：3
   - 镜像：redis:7-alpine
   - 配置 redis 启动命令：redis-server --appendonly yes
   - 通过 volumeClaimTemplates 为每个 Pod 创建 100Mi PVC
   - 对应的 Headless Service 名称为 redis-svc

2. 部署 DaemonSet：
   - 名称：node-monitor
   - 镜像：busybox:1.36
   - 每 10 秒打印节点主机名和当前时间到 stdout

3. 部署 CronJob：
   - 名称：redis-backup
   - 每 30 分钟执行一次
   - 使用 busybox:1.36
   - 命令：echo "backup at $(date)"

4. 验证：
   - redis-cluster-0/1/2 全部 Running
   - node-monitor 在每个节点一个 Pod
   - redis-backup CronJob 显示在 kubectl get cj 中

5. 写入测试数据到 redis-cluster-0，删除该 Pod，
   重建后验证数据是否保留（通过 PVC 持久化）

【评分标准】
- StatefulSet + Headless Service 正确（30 分）
- DaemonSet 正确（20 分）
- CronJob 正确（20 分）
- PVC 自动创建（15 分）
- 数据持久性验证（15 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get ds` | 列出 DaemonSet | 每个节点运行一个 Pod 副本 |
| `kubectl get ds -o wide` | DaemonSet + 选择器/镜像 | 确认每个节点是否都有 Pod |
| `kubectl describe ds <name>` | DaemonSet 详情 | 查看更新策略（RollingUpdate/OnDelete） |
| `kubectl get sts` | 列出 StatefulSet | StatefulSet 常用 short name: sts |
| `kubectl describe sts <name>` | StatefulSet 详情 | 查看 podManagementPolicy、serviceName、volumeClaimTemplates |
| `kubectl get pods -l app=mysql` | 按标签筛选 Pod | StatefulSet Pod 命名：`<name>-0, <name>-1, ...` |
| `kubectl scale sts <name> --replicas=5` | 扩缩 StatefulSet | 按序号递增/递减创建/删除 Pod |
| `kubectl get pvc` | 列出 PVC | StatefulSet + volumeClaimTemplates 自动为每个 Pod 创建 PVC |
| `kubectl get job` | 列出 Job | 一次性任务，完成后 Pod 状态为 Completed |
| `kubectl describe job <name>` | Job 详情 | 查看 completions、parallelism、backoffLimit |
| `kubectl logs job/<name>` | 查看 Job 日志 | Job Pod 执行完不会自动删除，可事后查看日志 |
| `kubectl get cronjob` | 列出 CronJob | short name: cj |
| `kubectl describe cronjob <name>` | CronJob 详情 | 查看 schedule、lastScheduleTime、suspend 状态 |
| `kubectl get jobs --watch` | 实时监控 Job 创建 | 观察 CronJob 触发时自动创建的 Job |
| `kubectl create job test-job --image=busybox --dry-run=client -o yaml` | 生成 Job YAML | 快速获取 Job 模板 |
| `kubectl create cronjob test-cj --image=busybox --schedule="*/5 * * * *" --dry-run=client -o yaml` | 生成 CronJob YAML | 5 字段 cron 表达式（分/时/日/月/周） |
| `kubectl delete job <name>` | 删除 Job | 级联删除其完成的 Pod |
| `kubectl delete cronjob <name>` | 删除 CronJob | 不会删除正在运行的 Job 和 Pod |
| `kubectl patch cronjob <name> -p '{"spec":{"suspend":true}}'` | 暂停 CronJob | 停止后续调度，保留历史 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：DaemonSet | https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/ |
| Kubernetes 官方：StatefulSet | https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/ |
| Kubernetes 官方：Job | https://kubernetes.io/docs/concepts/workloads/controllers/job/ |
| Kubernetes 官方：CronJob | https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/ |
| Kubernetes 官方：工作负载资源 | https://kubernetes.io/docs/concepts/workloads/controllers/ |
| Cron 表达式语法 | https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#cron-schedule-syntax |
