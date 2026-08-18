---
title: Day 02 - 多节点集群与节点管理
module: M1-集群架构与搭建
day: 2
updated: 2026-06-10
duration: 240 分钟
level: 基础
prerequisites:
- Day 01 完成，单节点集群就绪
- 额外 2 台 CentOS Stream 9 云服务器（≥ 2C2G）
- 3 台服务器在同一内网（VPC）
objectives:
- 掌握 kubeadm join 流程
- 理解 Node 生命周期管理
- 掌握节点标签、污点与容忍
- 能执行 cordon/drain/uncordon 操作
- 理解 token 过期处理
tags:
- kubeadm join
- Node
- cordon
- drain
- taint
- toleration
date: '2026-08-18'
status: published
---

# 📘 Day 02：多节点集群与节点管理

## 🎯 今日目标

- [ ] 搭建 1 master + 2 worker 完整集群
- [ ] 掌握节点标签的增删改查
- [ ] 会用 cordon/drain 管理节点上/下线
- [ ] 配置 Pod 的 Taint/Toleration 实现调度控制
- [ ] 能处理节点 join 失败的问题

---

## 🧠 理论精讲（30 分钟）

### Join 流程

```
Worker 节点                    Master 节点
    │                             │
    │── kubeadm join ────────────→│  token 验证
    │   (token + discovery-hash)  │  TLS bootstrap
    │                             │  颁发客户端证书
    │←── 下发 kubeconfig ────────│
    │                             │
    │── kubelet 启动 ────────────→│  上报 Node 资源
    │                             │
    │←── 分配 Pod (CNI IP) ──────│
```

**关键参数：**
- `--token`：集群加入凭证，默认有效期 24 小时
- `--discovery-token-ca-cert-hash`：CA 证书 hash，防中间人攻击

### Node 生命周期

```
Register ──→ Ready ──→ NotReady(>5min) ──→ Pod 驱逐
                 │
                 ├── cordon（标记不可调度，已有 Pod 不动）
                 │
                 └── drain（驱逐 Pod + cordon）
```

### Taint / Toleration

| 概念 | 说明 | 类比 |
|------|------|------|
| **Taint**（污点） | 打在节点上，排斥 Pod | "这节点只有特定 Pod 能用" |
| **Toleration**（容忍） | 配置在 Pod 上，容忍节点污点 | "我可以忍受这个节点的污点" |

```yaml
# 三个污点效果：
# NoSchedule    — 不调度新 Pod
# PreferNoSchedule — 尽量不调度
# NoExecute     — 不调度新 Pod + 驱逐已有 Pod
```

---

## 🔧 动手实操（120 分钟）

### 练习 2.1：搭建 3 节点集群

**在所有 3 台服务器上执行 Day 01 的环境准备（不需要 kubeadm init）：**

```bash
# --- Worker 节点 1、2 都执行 ---

# 关闭 swap
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# 内核模块
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# 内核参数
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# containerd
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y containerd.io
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

# kubeadm/kubelet/kubectl
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/repodata/repomd.xml.key
EOF
sudo dnf install -y kubelet kubeadm kubectl
sudo dnf install -y dnf-plugins-core
sudo dnf versionlock kubelet kubeadm kubectl
```

**在 Master 上获取 join 命令：**

```bash
# 如果昨天的 token 过期了，重新生成
kubeadm token create --print-join-command
# 输出类似：
# kubeadm join 10.0.0.1:6443 --token abc123.xxx --discovery-token-ca-cert-hash sha256:yyy
```

**在 Worker 1 和 Worker 2 上执行 join：**

```bash
# 将上面输出的命令粘贴执行
sudo kubeadm join 10.0.0.1:6443 --token abc123.xxx --discovery-token-ca-cert-hash sha256:yyy
```

**在 Master 上验证集群完整：**

```bash
kubectl get nodes
# 预期输出：
# NAME         STATUS   ROLES           AGE   VERSION
# k8s-master   Ready    control-plane   1d    v1.29.0
# k8s-node1    Ready    <none>          30s   v1.29.0
# k8s-node2    Ready    <none>          30s   v1.29.0
```

---

### 练习 2.2：节点标签管理

```bash
# 查看所有节点及其标签
kubectl get nodes --show-labels

# 给节点打标签
kubectl label node k8s-node1 role=worker
kubectl label node k8s-node2 role=worker
kubectl label node k8s-node1 disk=ssd
kubectl label node k8s-node2 disk=hdd

# 查看特定标签
kubectl get nodes -l role=worker
kubectl get nodes -l disk=ssd --show-labels

# 覆盖标签（--overwrite）
kubectl label node k8s-node1 disk=nvme --overwrite

# 删除标签（标签名后加 -）
kubectl label node k8s-node1 disk-

# 验证
kubectl get nodes k8s-node1 --show-labels
```

---

### 练习 2.3：cordon 与 uncordon

```bash
# 1. 先创建 Deployment 观察
kubectl create deploy nginx --image=nginx:alpine --replicas=6
kubectl get pod -o wide
# 观察 Pod 分布到两个 worker

# 2. 对 node1 执行 cordon（停止调度）
kubectl cordon k8s-node1

# 3. 验证 node1 状态
kubectl get nodes
# k8s-node1   Ready,SchedulingDisabled   ...

# 4. 扩容，验证新 Pod 不调度到 node1
kubectl scale deploy/nginx --replicas=10
kubectl get pod -o wide
# 新 Pod 全部被调度到 node2

# 5. 解除 cordon
kubectl uncordon k8s-node1
kubectl get nodes
# k8s-node1   Ready   ...
```

---

### 练习 2.4：drain 节点排空

```bash
# 1. 确定 node1 上有 Pod
kubectl get pod -o wide | grep k8s-node1

# 2. 对 node1 执行 drain
# --ignore-daemonsets：忽略 DaemonSet Pod（它们无法被驱逐）
# --delete-emptydir-data：删除使用 emptyDir 的 Pod
kubectl drain k8s-node1 --ignore-daemonsets --delete-emptydir-data

# 3. 观察 Pod 迁移过程
kubectl get pod -o wide -w
# Pod 被驱逐后在 node2 重建

# 4. 验证 node1 状态
kubectl get nodes
# k8s-node1   Ready,SchedulingDisabled   ...

# 5. 恢复 node1
kubectl uncordon k8s-node1
```

---

### 练习 2.5：Taint 与 Toleration

```bash
# 1. 给 node1 添加污点（专用数据库节点）
kubectl taint node k8s-node1 db=only:NoSchedule

# 2. 创建普通 Deployment 验证不受影响
kubectl create deploy web --image=nginx:alpine --replicas=3
kubectl get pod -o wide
# 全部 Pod 应避开 node1

# 3. 创建带 Toleration 的 Pod 专门调度到 node1
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
spec:
  tolerations:
  - key: "db"
    operator: "Equal"
    value: "only"
    effect: "NoSchedule"
  containers:
  - name: db
    image: nginx:alpine
EOF

kubectl get pod db-pod -o wide
# db-pod 可以调度到 node1（容忍了污点）

# 4. NoExecute 污点测试（驱逐已有 Pod）
kubectl taint node k8s-node2 test=evict:NoExecute
# 已有的普通 Pod 在 300 秒宽限期后会被驱逐

# 5. 移除污点（污点名后加 -）
kubectl taint node k8s-node1 db-
kubectl taint node k8s-node2 test-

# 6. 验证
kubectl describe node k8s-node1 | grep -A5 Taints
kubectl describe node k8s-node2 | grep -A5 Taints
```

---

### 练习 2.6：节点删除与重新加入

```bash
# 1. 排空 node2
kubectl drain k8s-node2 --ignore-daemonsets --delete-emptydir-data

# 2. 从集群删除 node2
kubectl delete node k8s-node2

# 3. 在 node2 上重置 kubeadm
sudo kubeadm reset -f
sudo rm -rf /etc/cni/net.d

# 4. 重新加入集群
# 在 Master 上生成新 token
kubeadm token create --print-join-command
# 在 node2 上执行 join 命令

# 5. 验证节点回归
kubectl get nodes
# k8s-node2   Ready   <none>   10s   v1.29.0
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：Token 过期

```bash
# 模拟：在 worker 上使用过期 token join 失败
# 错误信息：failed to parse token ...

# 排查步骤：
# 1. 查看现有 token 列表
kubeadm token list
# 如果没有有效 token，显示空

# 2. 创建新 token
sudo kubeadm token create

# 3. 获取 CA 证书 hash
openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | \
  openssl rsa -pubin -outform der 2>/dev/null | \
  openssl dgst -sha256 -hex | sed 's/^.* //'

# 4. 使用新 token 和 hash 重新 join
```

### 场景 2：节点 NotReady — CNI 未初始化

```bash
# 排查步骤：
# 1. 看节点状态
kubectl describe node k8s-node2 | grep -A10 Conditions
# 发现 KubeletNotReady，reason: ContainerNetworkNotReady

# 2. 登录 node2，检查 kubelet 日志
sudo journalctl -u kubelet -n 50 --no-pager
# 发现 "CNI plugin not initialized"

# 3. 检查 Calico Pod 是否已运行
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
# 如果 node2 上没有 Calico Pod，等待自动调度或检查 Calico DS 配置

# 4. 手动检查 CNI 配置
ls /etc/cni/net.d/
# 应有 calico 相关配置文件
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**完成下述全部操作

**题目：节点管理与高可用**

```
【初始环境】
1 master（k8s-master）+ 2 worker（k8s-node1, k8s-node2）集群就绪

【操作要求】
1. 给 node1 添加标签 env=production、zone=cn-east
2. 给 node2 添加标签 env=staging、zone=cn-east
3. 创建 Deployment app-prod（3副本），用 nodeSelector 限制到 env=production
4. 创建 Deployment app-staging（2副本），用 nodeSelector 限制到 env=staging
5. 对 node1 执行 drain 排空，要求：
   - 忽略 DaemonSet
   - 删除 emptyDir 数据
   - 观察 app-prod Pod 迁移到哪个节点（预期迁移到 node2，但 node2 标签不匹配会怎样？）
6. 排空后 uncordon 恢复 node1
7. 给 node1 添加污点 maintenance=true:NoSchedule
8. 修改 app-prod Deployment，添加 Toleration 使之仍能调度到 node1
9. 移除 node1 污点
10. 验证全部 Pod 正常运行

【评分标准】
- 标签操作正确（10 分）
- nodeSelector 调度正确（25 分）
- drain 操作正确（20 分）
- uncordon 恢复（10 分）
- 污点与容忍配置正确（25 分）
- 最终验证全部 Running（10 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubeadm token create --print-join-command` | 生成 Worker 节点加入命令 | Token 默认 24h 有效，过期需重新生成 |
| `kubeadm token list` | 查看现有 Token | 无可用 Token 时 Worker 无法加入集群 |
| `kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>` | Worker 加入集群 | 在 Worker 节点上执行，自动安装 kubelet 并注册节点 |
| `kubectl get nodes -o wide` | 节点列表 + 详细信息 | 显示内网 IP、OS、内核版本、容器运行时 |
| `kubectl describe node <node-name>` | 节点详细信息 | 查看 Conditions（MemoryPressure/DiskPressure/PIDPressure）、Taints、已分配资源 |
| `kubectl label node <node> key=value` | 给节点打标签 | 配合 nodeSelector/nodeAffinity 控制调度 |
| `kubectl label node <node> key-` | 删除节点标签 | 标签名后加 `-` 即可删除 |
| `kubectl taint node <node> key=value:NoSchedule` | 添加污点 | 无对应 Toleration 的 Pod 无法调度到此节点 |
| `kubectl taint node <node> key=value:NoSchedule-` | 移除污点 | 末尾加 `-` 删除对应 Taint |
| `kubectl taint node <node> node-role.kubernetes.io/control-plane-` | 去除 Master 污点 | 3 节点以下集群可让 Master 也调度 Pod（学习环境常用） |
| `kubectl cordon <node>` | 标记节点不可调度 | 不会驱逐已有 Pod，仅阻止新 Pod 调度 |
| `kubectl uncordon <node>` | 恢复节点可调度 | 取消 cordon 标记 |
| `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` | 安全驱逐节点上所有 Pod | 节点维护/下线前必执行；DaemonSet Pod 需 --ignore-daemonsets |
| `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --force` | 强制驱逐（含不受控制器管理的 Pod） | 裸 Pod（无 ownerReference）需 --force |
| `kubectl delete node <node>` | 删除节点对象 | 节点失联后从集群移除；需先 drain |
| `systemctl status kubelet` | 查看 kubelet 状态 | 节点 NotReady 时首要排查命令 |
| `journalctl -u kubelet -f` | 实时查看 kubelet 日志 | Pod 启停失败的根因通常在 kubelet 日志 |
| `journalctl -u kubelet --since "10 min ago"` | 查看最近 10 分钟 kubelet 日志 | 时间范围过滤，定位近期异常 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：节点管理 | https://kubernetes.io/docs/concepts/architecture/nodes/ |
| Kubernetes 官方：kubeadm join | https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-join/ |
| Kubernetes 官方：安全驱逐节点 | https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/ |
| Kubernetes 官方：污点与容忍 | https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| Kubernetes 官方：节点标签 | https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/ |

## 📝 今日笔记模板

```
日期：____年____月____日
用时：____小时____分

✅ 完成项：
□ 3 节点集群搭建
□ 练习 2.1-2.6
□ 排错练习 1-2
□ 赛题模拟

❓ 遇到的问题与解决方案：
1.
2.

📌 关键收获：
1. cordon vs drain 的区别
2. Taint/Toleration 的使用场景
3.
```
