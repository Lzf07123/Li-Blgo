---
title: Day 23 - 日志收集与 EFK
module: M7-监控日志与排错
day: 23
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M2 完成，理解 DaemonSet
objectives:
- 理解 K8s 日志架构
- 部署 Fluent Bit 采集日志
- 掌握 kubectl logs 进阶用法
- 排查日志相关问题
tags:
- 日志
- Fluent Bit
- kubectl logs
- DaemonSet
date: '2026-08-18'
status: published
---

# 📘 Day 23：日志收集与 EFK

## 🎯 今日目标

- [ ] 理解 K8s 日志层级（容器→节点→集群）
- [ ] 部署 Fluent Bit 做日志采集
- [ ] 掌握 kubectl logs 的全部选项
- [ ] 能排查日志丢失/配置错误

---

## 🧠 理论精讲（30 分钟）

### K8s 日志三层架构

```
┌──────────────────────────────────────┐
│  Pod (Container stdout/stderr)       │  ← 容器日志
│  ↓ 写入                               │
│  Node (/var/log/containers/*.log)    │  ← 节点层
│  ↓ 采集                               │
│  Log Agent (DaemonSet: Fluent Bit)   │  ← 采集层
│  ↓ 转发                               │
│  Elasticsearch / Loki / Kafka        │  ← 存储层
│  ↓ 查询                               │
│  Kibana / Grafana                    │  ← 展示层
└──────────────────────────────────────┘
```

### kubectl logs 进阶

| 选项 | 用途 |
|------|------|
| `--tail=N` | 最后 N 行 |
| `-f` / `--follow` | 实时跟踪 |
| `--since=5m` | 最近 5 分钟 |
| `--previous` / `-p` | 上一次容器的日志 |
| `--timestamps` | 显示时间戳 |
| `--all-containers` | 所有容器日志 |

---

## 🔧 动手实操（120 分钟）

### 练习 23.1：kubectl logs 精通

```bash
# 1. 创建一个多容器 Pod
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: log-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      i=0
      while true; do
        echo "[$(date +%T)][INFO] Application log entry $i"
        i=$((i+1))
        sleep 2
      done
  - name: sidecar
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      while true; do
        echo "[$(date +%T)][DEBUG] Sidecar heartbeat"
        sleep 5
      done
EOF

# 2. 基础操作
kubectl logs log-demo -c app --tail=5
kubectl logs log-demo -c sidecar --tail=3

# 3. 跟踪日志
kubectl logs log-demo -c app -f &
# Ctrl+C 停止

# 4. 查看所有容器日志
kubectl logs log-demo --all-containers --tail=10

# 5. 查看最近 2 分钟的日志
kubectl logs log-demo -c app --since=2m

# 6. 带时间戳
kubectl logs log-demo -c app --timestamps --tail=5

# 7. 查看上一次崩溃的日志
# 先模拟崩溃
kubectl run crash-log --image=busybox:1.36 --restart=Always -- /bin/sh -c 'echo "About to crash"; exit 1'

sleep 15
kubectl logs crash-log --previous
# 输出：About to crash

# 清理
kubectl delete pod log-demo crash-log
```

---

### 练习 23.2：使用 stern 多 Pod 日志

```bash
# stern 是比 kubectl logs 更好的多 Pod 日志工具

# 1. 安装 stern
# macOS
brew install stern
# Linux
wget https://github.com/stern/stern/releases/download/v1.28.0/stern_1.28.0_linux_amd64.tar.gz
tar -xzf stern_1.28.0_linux_amd64.tar.gz
sudo mv stern /usr/local/bin/

# 2. 创建多副本 Deployment
kubectl create deploy stern-test --image=busybox:1.36 --replicas=3 -- \
  sh -c 'while true; do echo "[$(hostname)] log at $(date +%T)"; sleep 3; done'

# 3. stern 同时查看所有副本日志
stern stern-test --tail=5
# 按颜色区分不同 Pod！

# 4. 按标签过滤
stern -l app=stern-test --since=1m

# 5. 清理
kubectl delete deploy stern-test
```

---

### 练习 23.3：Fluent Bit 日志采集

```bash
# 1. 添加 Fluent Helm 仓库
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

# 2. 安装 Fluent Bit
helm install fluent-bit fluent/fluent-bit \
  --namespace logging \
  --create-namespace \
  --set config.outputs.es.enabled=false \
  --set config.outputs.stdout.enabled=true \
  --set config.outputs.stdout.match="*"

# 3. 查看 Fluent Bit Pod
kubectl get pods -n logging
# fluent-bit-xxx（每个节点一个）

# 4. 查看 Fluent Bit 采集的日志（输出到 stdout）
kubectl logs -n logging -l app.kubernetes.io/name=fluent-bit --tail=20

# 5. 验证日志 Pipeline
kubectl get daemonset -n logging
kubectl get configmap -n logging
kubectl describe configmap -n logging fluent-bit
```

---

### 练习 23.4：节点日志直接查看

```bash
# 1. 所有容器的 stdout/stderr 日志在这里
# SSH 到任一 worker 节点：
ls /var/log/containers/
# 每个容器一个 symlink → /var/log/pods/

# 2. 容器日志存储格式
ls /var/log/pods/
# <namespace>_<pod-name>_<pod-uid>/<container-name>/

# 3. 查看 kubelet 日志
sudo journalctl -u kubelet -n 50 --no-pager

# 4. 查看容器运行时日志（containerd）
sudo journalctl -u containerd -n 30 --no-pager

# 5. 查看内核日志
sudo dmesg | tail -30
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：Pod 日志为空

```bash
# 可能原因：
# 1. 应用没有输出到 stdout/stderr（写到了文件）
kubectl exec <pod> -- ls /var/log/app/

# 2. 日志被轮转删除了
# 3. 应用还没开始输出
kubectl logs <pod> -f
```

### 场景 2：日志过多导致磁盘满

```bash
# 检查节点磁盘
df -h

# 检查容器日志大小
du -sh /var/log/containers/* | sort -rh | head -10

# 配置 kubelet 日志轮转（/var/lib/kubelet/config.yaml）
# containerLogMaxSize: "10Mi"
# containerLogMaxFiles: 5
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：日志采集与排查**

```
【操作要求】

1. 部署一个会持续产生日志的应用：
   - Deployment log-gen（3 副本，busybox:1.36）
   - 每 2 秒输出一条带时间戳的日志
   - 日志格式：[LEVEL][TIMESTAMP] message

2. 日志操作：
   a. 查看某个 Pod 最后 20 条日志
   b. 实时跟踪所有 log-gen Pod 的日志（用 stern 或 kubectl logs -f）
   c. 查看最近 3 分钟的日志
   d. 模拟 Pod 崩溃，用 --previous 查看崩溃前日志

3. 部署 Fluent Bit（DaemonSet 方式）：
   - 输出到 stdout（便于验证）
   - 在 Fluent Bit 日志中确认采集到了 log-gen 的日志

4. 排查：
   - 某个 Pod 日志为空的原因（模拟：应用写日志到文件而非 stdout）
   - 给出解决方案

【评分标准】
- log-gen 部署正确（15 分）
- kubectl logs 操作全对（25 分）
- Fluent Bit 部署 + 验证（30 分）
- 排查分析（30 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl logs <pod> -f` | 实时跟踪 Pod 日志 | 等于 `tail -f` |
| `kubectl logs <pod> --tail=100` | 最后 100 行日志 | 避免刷屏 |
| `kubectl logs <pod> --since=10m` | 最近 10 分钟日志 | 时间范围过滤 |
| `kubectl logs <pod> --timestamps` | 带时间戳的日志 | 确定日志时间线 |
| `kubectl logs <pod> -c <container>` | 指定容器日志 | 多容器 Pod 必须用 `-c` |
| `kubectl logs <pod> --all-containers=true` | 所有容器日志 | 一次性查看 Pod 所有容器 |
| `kubectl logs <pod> --previous` | 查看上一次崩溃的日志 | 容器重启后的历史日志 |
| `kubectl logs -l app=<name> --tail=20` | 按标签批量查看日志 | `-l` 按标签选择器筛选 |
| `kubectl logs -l app=<name> --all-containers=true --since=5m` | 批量日志 + 时间过滤 | 组合选项精确定位 |
| `kubectl stern "app-*" -n <ns>` | 多 Pod 日志流（stern 工具） | 比 kubectl logs -l 更好用的实时多 Pod 日志，需安装 stern |
| `journalctl -u kubelet -f` | 实时查看 kubelet 节点日志 | Pod 启停失败根因在 kubelet |
| `journalctl -u containerd -f` | 实时查看 containerd 日志 | 容器运行时层面排错 |
| `crictl logs <container-id>` | 容器日志（CRI 层） | kubectl logs 不可用时的备选 |
| `kubectl -n logging logs -l app=fluentd --tail=50` | 查看 Fluentd 日志 | 日志收集管道故障排查 |
| `kubectl -n logging logs -l app=elasticsearch --tail=50` | 查看 Elasticsearch 日志 | ES 集群健康状态检查 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：日志架构 | https://kubernetes.io/docs/concepts/cluster-administration/logging/ |
| Kubernetes 官方：kubectl logs | https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#logs |
| stern 多 Pod 日志工具 | https://github.com/stern/stern |
| Fluentd Kubernetes 集成 | https://docs.fluentd.org/container-deployment/kubernetes |
| Elasticsearch 官方文档 | https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html |
| EFK Stack 部署指南 | https://github.com/fluent/fluentd-kubernetes-daemonset （Fluentd DaemonSet 官方示例，原 kubernetes/cluster/addons 已在 v1.24+ 移除） |
