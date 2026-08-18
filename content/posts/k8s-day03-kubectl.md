---
title: Day 03 - 集群运维与 kubectl 精通
module: M1-集群架构与搭建
day: 3
updated: 2026-06-10
duration: 240 分钟
level: 基础
prerequisites:
- Day 02 完成，3 节点集群就绪
objectives:
- 精通 kubectl 输出格式与调试技巧
- 掌握 --dry-run=client 快速生成 YAML 模板
- 能独立使用 kubectl explain 查阅 API 文档
- 掌握集群版本升级流程
- 能执行 etcd 备份与恢复
tags:
- kubectl
- dry-run
- jsonpath
- etcd 备份
- 集群升级
date: '2026-08-18'
status: published
---

# 📘 Day 03：集群运维与 kubectl 精通

## 🎯 今日目标

- [ ] 能灵活使用 `-o wide`、`-o yaml`、`-o json`、`-o jsonpath`
- [ ] 能用 `--dry-run=client` 快速生成任意资源 YAML 模板
- [ ] 能用 `kubectl explain` 查阅 API 字段文档
- [ ] 完成一次集群版本升级
- [ ] 完成 etcd 快照备份并验证可恢复

---

## 🧠 理论精讲（30 分钟）

### kubectl 命令分类

| 类别 | 命令 | 场景 |
|------|------|------|
| **CRUD** | `create`、`get`、`describe`、`edit`、`delete`、`apply`、`patch` | 资源管理 |
| **调试** | `logs`、`exec`、`attach`、`cp`、`port-forward`、`top` | 问题排查 |
| **集群管理** | `cordon`、`drain`、`uncordon`、`taint`、`label`、`annotate` | 节点运维 |
| **配置** | `config view`、`config use-context` | kubeconfig 管理 |

### 输出格式速查

| 选项 | 用途 |
|------|------|
| `-o wide` | 追加列（如 Pod 显示 IP 和 Node） |
| `-o yaml` | 完整 YAML 定义 |
| `-o json` | 完整 JSON 定义 |
| `-o jsonpath='{...}'` | 提取特定字段 |
| `-o name` | 只输出资源类型/名称 |
| `--sort-by='.metadata.creationTimestamp'` | 按字段排序 |

### `--dry-run=client` 的威力

这是比赛中最常用的命令之一：

```bash
# 生成 Pod YAML 模板
kubectl run nginx --image=nginx:alpine --dry-run=client -o yaml

# 生成 Deployment YAML 模板
kubectl create deploy nginx --image=nginx:alpine --dry-run=client -o yaml

# 生成 Service YAML 模板
kubectl create service clusterip nginx --tcp=80:80 --dry-run=client -o yaml
```

> 💡 比赛中不需要从零手写 YAML，用 `--dry-run=client` 生成模板再编辑即可。

---

## 🔧 动手实操（120 分钟）

### 练习 3.1：kubectl explain 查阅 API 文档

```bash
# 查看 Pod 资源定义
kubectl explain pod

# 逐层深入
kubectl explain pod.spec
kubectl explain pod.spec.containers
kubectl explain pod.spec.containers.resources
kubectl explain pod.spec.containers.livenessProbe
kubectl explain pod.spec.containers.livenessProbe.httpGet

# 查看其他资源
kubectl explain deployment.spec.strategy
kubectl explain deployment.spec.strategy.rollingUpdate
kubectl explain ingress.spec.rules.http.paths.backend

# 递归查看所有字段
kubectl explain pod --recursive | head -100
```

---

### 练习 3.2：--dry-run=client 生成 YAML

```bash
# 1. 生成 Pod YAML
kubectl run my-pod --image=nginx:alpine --dry-run=client -o yaml > pod-template.yaml

# 2. 生成 Deployment YAML
kubectl create deploy my-deploy --image=nginx:alpine --replicas=3 --dry-run=client -o yaml > deploy-template.yaml

# 3. 生成 Service YAML（ClusterIP）
kubectl create service clusterip my-svc --tcp=80:80 --dry-run=client -o yaml > svc-template.yaml

# 4. 生成 Service YAML（NodePort）
kubectl create service nodeport my-np --tcp=80:80 --dry-run=client -o yaml > np-template.yaml

# 5. 生成 ConfigMap YAML
kubectl create configmap my-config --from-literal=key1=val1 --from-literal=key2=val2 --dry-run=client -o yaml

# 6. 生成 Secret YAML
kubectl create secret generic my-secret --from-literal=password=123456 --dry-run=client -o yaml

# 7. 生成 Job YAML
kubectl create job my-job --image=busybox --dry-run=client -o yaml -- date

# 8. 生成 CronJob YAML
kubectl create cj my-cj --image=busybox --schedule="*/5 * * * *" --dry-run=client -o yaml -- date
```

---

### 练习 3.3：jsonpath 实战

```bash
# 前提：创建一些测试资源
kubectl create deploy nginx --image=nginx:alpine --replicas=3

# 1. 提取所有 Pod 名称
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'

# 2. 提取 Pod 名称:所在节点
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.nodeName}{"\n"}{end}'

# 3. 提取 Pod IP
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.status.podIP}{"\n"}{end}'

# 4. 提取所有节点的 InternalIP
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.status.addresses[?(@.type=="InternalIP")].address}{"\n"}{end}'

# 5. 提取所有 Deployment 的副本数
kubectl get deploy -o jsonpath='{range .items[*]}{.metadata.name}{": replicas="}{.spec.replicas}{", ready="}{.status.readyReplicas}{"\n"}{end}'

# 6. 提取所有 Service 的 ClusterIP
kubectl get svc -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.spec.clusterIP}{":"}{.spec.ports[0].port}{"\n"}{end}'
```

---

### 练习 3.4：集群"体检"

```bash
# 1. 查看所有命名空间的事件，按时间排序
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20

# 2. 查看所有非 Running 的 Pod
kubectl get pods --all-namespaces --field-selector=status.phase!=Running

# 3. 查看节点资源使用（需要 metrics-server）
# 如果没有 metrics-server，先安装：
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

kubectl top nodes
kubectl top pods --all-namespaces

# 4. 查看集群版本信息
kubectl version

# 5. 检查证书到期时间
sudo kubeadm certs check-expiration

# 6. 检查所有组件的健康状态
kubectl get --raw='/healthz?verbose'
```

---

### 练习 3.5：集群版本升级（kubeadm upgrade）

```bash
# === 在 Master 节点上执行 ===

# 1. 查看当前版本和可升级版本
kubeadm upgrade plan

# 2. 解锁 kubeadm（如果之前 versionlock 了）
sudo dnf versionlock delete kubeadm
sudo dnf install -y kubeadm-1.29.5  # 替换为目标版本

# 3. 执行升级
sudo kubeadm upgrade apply v1.29.5

# 4. 升级 kubelet 和 kubectl
sudo dnf versionlock delete kubelet kubectl
sudo dnf install -y kubelet-1.29.5 kubectl-1.29.5
sudo dnf versionlock add kubelet kubectl

# 5. 重启 kubelet
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 6. 验证升级
kubectl get nodes
# Master 版本应变为 v1.29.5

# === 在每个 Worker 节点上执行 ===

# 7. 排空 worker
kubectl drain k8s-node1 --ignore-daemonsets --delete-emptydir-data

# 8. 在 worker 上升级
sudo dnf versionlock delete kubeadm
sudo dnf install -y kubeadm-1.29.5
sudo kubeadm upgrade node

# 9. 升级 kubelet
sudo dnf versionlock delete kubelet
sudo dnf install -y kubelet-1.29.5
sudo dnf versionlock add kubelet
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 10. 恢复 worker
kubectl uncordon k8s-node1

# 11. 对所有 worker 重复 7-10，最终验证
kubectl get nodes
# 所有节点版本一致
```

---

### 练习 3.6：etcd 备份与恢复

```bash
# === 备份 etcd ===

# 1. 查看 etcd 证书位置
ls /etc/kubernetes/pki/etcd/

# 2. 创建备份
sudo ETCDCTL_API=3 etcdctl snapshot save /opt/etcd-backup-$(date +%Y%m%d).db \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --endpoints=127.0.0.1:2379

# 3. 验证备份
sudo ETCDCTL_API=3 etcdctl snapshot status /opt/etcd-backup-*.db
# 输出：hash、revision、total keys、total size

# 4. 验证备份内容
sudo ETCDCTL_API=3 etcdctl snapshot status /opt/etcd-backup-*.db --write-out=table

# === 恢复 etcd（模拟灾难恢复，请谨慎操作） ===

# 5. 创建恢复目录
sudo mkdir -p /var/lib/etcd-restore

# 6. 从快照恢复
sudo ETCDCTL_API=3 etcdctl snapshot restore /opt/etcd-backup-*.db \
  --data-dir=/var/lib/etcd-restore \
  --name=k8s-master \
  --initial-cluster=k8s-master=https://127.0.0.1:2380 \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# 7. 检查恢复的数据
sudo ls -la /var/lib/etcd-restore/

# ⚠️ 生产环境恢复需要修改 /etc/kubernetes/manifests/etcd.yaml 的 data-dir 指向恢复目录
# ⚠️ 练习环境请勿实际操作，理解流程即可
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：kubectl 连接被拒

```bash
# 错误：
# The connection to the server localhost:8080 was refused

# 排查步骤：
# 1. 检查 kubeconfig 是否存在
ls -la ~/.kube/config

# 2. 检查环境变量
echo $KUBECONFIG

# 3. 检查当前 context
kubectl config current-context

# 4. 检查 api-server 是否运行
sudo crictl ps | grep kube-apiserver
# 或
sudo docker ps | grep kube-apiserver

# 5. 检查 6443 端口
sudo ss -tlnp | grep 6443

# 解决方案：
# - 如果 api-server 挂了 → systemctl restart kubelet
# - 如果 config 丢了 → sudo cp /etc/kubernetes/admin.conf ~/.kube/config
```

### 场景 2：操作集群时权限错误

```bash
# 错误：
# Error from server (Forbidden): pods is forbidden

# 排查步骤：
# 1. 检查当前使用的证书
kubectl config view --raw | grep client-certificate

# 2. 检查当前 context 的用户
kubectl config current-context
kubectl config view -o jsonpath='{.contexts[?(@.name=="<context-name>")].context.user}'

# 3. 确认是用的哪个 kubeconfig
# 可能用了错误的 context 或证书
kubectl config get-contexts

# 解决方案：
# 切换到 admin context
kubectl config use-context kubernetes-admin@kubernetes
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**完成下述全部操作

**题目：集群运维综合**

```
【初始环境】3 节点集群正常运行

【操作要求】

Part A: YAML 模板生成（15 分）
1. 用 --dry-run=client 生成以下 YAML 文件：
   a. Deployment nginx-deploy，镜像 nginx:1.25，3 副本
   b. Service nginx-svc，ClusterIP 类型，暴露 80 端口
   c. ConfigMap nginx-config，包含键 index.html=<h1>Hello</h1>
   d. Secret nginx-secret，包含键 api-key=sk-123456
2. 保存为 deploy.yaml、svc.yaml、cm.yaml、secret.yaml

Part B: 集群信息提取（25 分）
3. 用 jsonpath 提取所有节点的名称、IP、污点信息
4. 找出所有非 Running 的 Pod（不限命名空间）
5. 列出所有 Service 及其 ClusterIP、端口映射
6. 查看最近 20 条集群事件

Part C: etcd 备份（30 分）
7. 对 etcd 做一次快照备份
8. 验证快照状态（输出 hash、keys 数量）
9. 恢复快照到 /var/lib/etcd-restore 目录
10. 验证恢复数据的完整性（比较 key 数量）

Part D: 版本验证（20 分）
11. 检查集群证书到期时间
12. 生成一份"集群健康报告"：节点状态、系统 Pod 状态、证书有效期

Part E: 新增节点（10 分）
13. 假设需要再添加一台 worker，写出 join 命令（不实际执行）

【评分标准】
- Part A: YAML 正确生成（15 分）
- Part B: 命令正确输出（25 分）
- Part C: etcd 备份恢复完整（30 分）
- Part D: 健康报告完整（20 分）
- Part E: join 命令正确（10 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl version` | 查看客户端与服务端版本 | 版本偏差不允许超过 ±1 个小版本 |
| `kubectl cluster-info dump` | 导出集群诊断信息 | 包含所有系统组件的日志摘要 |
| `kubectl get ns` | 列出所有命名空间 | kube-system 存放集群组件，default 是用户默认空间 |
| `kubectl get pods -A` | 所有命名空间的 Pod | `-A` = `--all-namespaces`，全局视角快速定位问题 |
| `kubectl get pods -o wide` | Pod + 节点 + IP | 定位 Pod 在哪个节点、IP 是多少 |
| `kubectl describe pod <pod>` | Pod 详细信息 | Events 段是排错第一入口，包含启动失败原因 |
| `kubectl logs <pod>` | 查看 Pod 日志（单容器） | 最常用排错命令，`-f` 实时跟踪 |
| `kubectl logs <pod> -c <container>` | 指定容器日志 | 多容器 Pod 必须用 `-c` 指定容器名 |
| `kubectl logs <pod> --tail=50` | 最后 50 行日志 | 避免刷屏 |
| `kubectl logs <pod> --since=5m` | 最近 5 分钟日志 | 排查近期异常 |
| `kubectl exec <pod> -- <cmd>` | 容器内执行命令 | `--` 分隔 kubectl 参数和容器内命令 |
| `kubectl exec -it <pod> -- /bin/sh` | 交互式进入容器 | 排错时检查文件/网络/进程 |
| `kubectl get all -n <ns>` | 命名空间内所有资源 | Pod/Service/Deploy/RS 一览 |
| `kubectl explain pod.spec.containers` | 查看资源字段文档 | 终端查 API 字段，写 YAML 神器 |
| `kubectl explain pod.spec --recursive` | 递归查看所有子字段 | 全面了解资源 YAML 结构 |
| `kubectl api-resources` | 列出所有 API 资源 | 包含 short name（svc/deploy/po）和 API Group |
| `kubectl api-versions` | 列出所有 API 版本 | 了解支持的 API Group 和版本 |
| `kubectl apply -f file.yaml` | 声明式创建/更新 | 幂等安全，推荐优先使用 |
| `kubectl create -f file.yaml` | 命令式创建 | 重复执行报错"already exists" |
| `kubectl delete -f file.yaml` | 按 YAML 删除 | 删除 YAML 中定义的所有资源 |
| `kubectl create deploy nginx --image=nginx --dry-run=client -o yaml > deploy.yaml` | 生成 YAML 不创建 | YAML 速成技巧，`--dry-run=client` 仅本地校验 |
| `kubectl edit deploy <name>` | 直接编辑集群资源 | 实时生效；建议先 `get -o yaml > backup.yaml` |
| `kubectl patch deploy <name> -p '{"spec":{"replicas":3}}'` | JSON Patch 部分更新 | 比 edit 更安全，适合脚本化 |
| `kubectl scale deploy <name> --replicas=5` | 快速扩缩副本 | 等价于修改 replicas 字段 |
| `kubectl rollout status deploy <name>` | 查看滚动更新进度 | 脚本中阻塞等待更新完成 |
| `kubectl rollout history deploy <name>` | 查看部署历史 | revision 号配合 `--revision` 查看变更详情 |
| `kubectl rollout undo deploy <name>` | 回滚上一版本 | 仅回滚 deploy 模板，不涉及代码仓库 |
| `kubectl rollout undo deploy <name> --to-revision=2` | 回滚到指定版本 | 历史默认保留 10 个 revision |
| `ETCDCTL_API=3 etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot save /backup/etcd-$(date +%F).db` | etcd 快照备份 | 静态 Pod 管理的 etcd 需指定 TLS 证书路径（kubeadm 默认 mTLS）；`ETCDCTL_API=3` 强制使用 v3 API |
| `ETCDCTL_API=3 etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot status /backup/etcd-xxx.db` | 查看快照完整性 | 输出快照的 etcd 版本、包含的 key 数量和文件大小 |
| `kubeadm certs check-expiration` | 查看证书过期时间 | 证书过期是生产常见故障，默认 1 年 |
| `kubeadm upgrade plan` | 查看可升级版本 | 升级前必做 |
| `kubectl config get-contexts` | 查看 kubeconfig 上下文 | 多集群切换 |
| `kubectl config use-context <name>` | 切换集群上下文 | 多集群管理 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| kubectl 命令参考 | https://kubernetes.io/docs/reference/kubectl/ |
| kubectl 速查表 | https://kubernetes.io/docs/reference/kubectl/quick-reference/ |
| Kubernetes API 资源概览 | https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.29/ |
| kubeadm 升级指南 | https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/ |
| etcd 备份与恢复 | https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/#backing-up-an-etcd-cluster |
| kubectl explain 用法 | https://kubernetes.io/docs/reference/kubectl/ |
