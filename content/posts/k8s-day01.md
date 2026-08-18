---
title: Day 01 - 集群架构原理与环境准备
module: M1-集群架构与搭建
day: 1
updated: 2026-06-10
duration: 240 分钟
level: 基础
prerequisites:
- Docker 基础操作（docker run/build/push）
- Linux 基本命令（systemctl、journalctl）
- 一台 CentOS Stream 9 云服务器（≥ 2C4G）
objectives:
- 理解 K8s 架构（控制平面 vs 数据平面）
- 掌握各核心组件的职责
- 能用 kubeadm 初始化单节点集群
- 安装 Calico CNI 并验证集群就绪
- 掌握 kubectl 基本操作
tags:
- kubeadm
- 集群初始化
- 架构原理
- Calico
- kubectl
date: '2026-08-18'
status: published
---

# 📘 Day 01：集群架构原理与环境准备

## 🎯 今日目标

- [ ] 能画出 K8s 架构图并说出每个组件的作用
- [ ] 能用 `kubeadm` 初始化单节点集群
- [ ] 安装 Calico CNI 并使 CoreDNS 正常运行
- [ ] 配置 `kubectl` 自动补全和常用别名
- [ ] 能使用 `kubectl` 查看集群组件状态

---

## 🧠 理论精讲（30 分钟）

### K8s 是什么

Kubernetes 是一个**容器编排平台**，它解决的问题：

| 问题 | K8s 怎么解决 |
|------|-------------|
| 容器放哪台机器？ | 调度器（Scheduler）自动决策 |
| 容器挂了怎么办？ | 控制器（Controller）自动重建 |
| 服务怎么被发现？ | Service + DNS 自动注册与发现 |
| 配置怎么管理？ | ConfigMap/Secret 统一管理 |
| 流量怎么分发？ | Service/Ingress 负载均衡 |
| 存储怎么挂载？ | PV/PVC 抽象存储 |

### 控制平面组件（Master 节点）

```
┌─────────────────────────────────────────────┐
│                  Control Plane               │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │   API    │  │  Scheduler│  │Controller │ │
│  │  Server  │  │           │  │  Manager  │ │
│  │ :6443    │  │ 决定 Pod  │  │ 维持期望  │ │
│  │          │  │ 放哪台机  │  │ 状态一致  │ │
│  └────┬─────┘  └──────────┘  └───────────┘ │
│       │                                      │
│  ┌────┴─────┐                               │
│  │   etcd   │   ← 集群状态的唯一数据源        │
│  │  :2379   │                               │
│  └──────────┘                               │
└─────────────────────────────────────────────┘
```

| 组件 | 职责 | 关键端口 |
|------|------|----------|
| **kube-apiserver** | 集群统一入口，所有操作必经之路 | `6443` |
| **etcd** | 分布式 KV 存储，保存集群所有状态 | `2379-2380` |
| **kube-scheduler** | 监听新 Pod，选择最优节点 | — |
| **kube-controller-manager** | 运行各种控制器（Deployment/Node/Service…） | — |

### 数据平面组件（所有节点）

| 组件 | 职责 |
|------|------|
| **kubelet** | 节点代理，执行 Pod 创建/销毁，上报状态 |
| **kube-proxy** | 维护节点上的网络规则（iptables/IPVS），实现 Service |
| **容器运行时** | 真正跑容器的东西（containerd / cri-o / docker） |

### 一个 `kubectl run nginx` 请求的完整流程

```
kubectl → api-server（认证→鉴权→准入→写入 etcd）
       → scheduler（watch 到未调度 Pod → 打分选节点 → 更新 Pod.spec.nodeName）
       → 目标节点 kubelet（watch 到分配给自己 → 调 CRI 创建容器 → 上报状态）
       → api-server 更新 Pod 状态为 Running
```

---

## 🔧 动手实操（120 分钟）

### 前置环境准备

```bash
# 1. 关闭 swap（K8s 要求）
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# 2. 加载内核模块
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# 3. 配置内核参数
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# 4. 安装 containerd（通过 Docker CE 仓库）
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y containerd.io
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
# 修改 SystemdCgroup = true
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

### 安装 kubeadm/kubelet/kubectl

```bash
# 5. 添加 K8s YUM 源
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/repodata/repomd.xml.key
EOF

# 6. 安装
sudo dnf install -y kubelet kubeadm kubectl
sudo dnf install -y dnf-plugins-core
sudo dnf versionlock kubelet kubeadm kubectl

# 7. 验证版本
kubeadm version
kubectl version --client
kubelet --version
```

---

### 练习 1.1：初始化单节点集群

```bash
# 初始化集群（关键参数）
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --kubernetes-version=v1.29.0 \
  --apiserver-advertise-address=<你的云服务器内网IP> \
  --image-repository=registry.aliyuncs.com/google_containers

# 记录 join 命令（后续 Day 02 用）
# 输出类似：kubeadm join <IP>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

**验证集群初始化：**

```bash
# 配置 kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# 查看节点状态
kubectl get nodes
# 预期输出：
# NAME         STATUS     ROLES           AGE   VERSION
# k8s-master   NotReady   control-plane   30s   v1.29.0
```

> ⚠️ 状态为 `NotReady` 是正常的，还没有安装网络插件。

---

### 练习 1.2：安装 Calico CNI 插件

```bash
# 下载并应用 Calico 清单
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
kubectl apply -f calico.yaml

# 等待所有系统 Pod 就绪
kubectl get pods -n kube-system --watch
# 等待 coredns 变为 Running，Calico Pod 也全部 Running

# Ctrl+C 退出 watch，验证节点 Ready
kubectl get nodes
# 预期输出：
# NAME         STATUS   ROLES           AGE   VERSION
# k8s-master   Ready    control-plane   2m    v1.29.0
```

---

### 练习 1.3：配置 kubectl 自动补全与别名

```bash
# Bash 自动补全
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc
source ~/.bashrc

# 验证
k get no
# 预期输出：节点信息
```

---

### 练习 1.4：查看集群组件状态

```bash
# 查看所有命名空间
kubectl get namespaces

# 查看系统组件 Pod
kubectl get pods -n kube-system

# 查看各组件健康状态
kubectl get componentstatuses
# 或
kubectl get --raw='/readyz?verbose'

# 查看所有节点详细信息
kubectl describe node $(hostname)

# 查看集群信息
kubectl cluster-info
```

---

### 练习 1.5：探索 etcd 存储

```bash
# 进入 etcd 容器（如果是静态 Pod 运行的）
# 先确认 etcd 是以静态 Pod 方式运行
ls /etc/kubernetes/manifests/
# 应当看到 etcd.yaml

# 用 crictl（containerd 默认）查看容器
sudo crictl ps | grep etcd

# 进入 etcd 容器执行查询
sudo crictl exec -it <etcd-container-id> sh

# 在容器内：
ETCDCTL_API=3 etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get / --prefix --keys-only | head -30
# 退出：exit
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：kubelet 停止后 Pod 状态变化

```bash
# 1. 先创建一个测试 Pod
kubectl run test-pod --image=nginx:alpine

# 2. 停止 kubelet
sudo systemctl stop kubelet

# 3. 观察节点和 Pod 状态变化
kubectl get nodes
# 预期：节点变为 NotReady（需要等约 40 秒）

kubectl get pod test-pod
# 预期：Pod 仍然是 Running 但节点 NotReady

# 4. 恢复 kubelet
sudo systemctl start kubelet

# 5. 等待恢复
kubectl get nodes -w
# 预期：节点逐步恢复为 Ready

# 6. 清理
kubectl delete pod test-pod
```

### 场景 2：CoreDNS Pending 排错

```bash
# 模拟问题：使用错误的 pod-network-cidr 导致 Calico 不工作
# 排查思路：
kubectl get pods -n kube-system
# 看到 coredns-xxx 状态为 Pending

kubectl describe pod -n kube-system <coredns-pod-name>
# 查看 Events，通常会提示 "failed to allocate for range..."

# 根因：Calico 未正确配置，无法分配 Pod IP
# 检查 Calico Pod 日志：
kubectl logs -n kube-system -l k8s-app=calico-node --tail=50

# 解决方案：确认 Pod CIDR 正确，必要时重建集群
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **30 分钟**完成下述全部操作

**题目：单节点集群部署**

```
【环境】一台全新的 CentOS Stream 9 云服务器（2C4G）
【要求】
1. 安装 containerd、kubeadm、kubelet、kubectl（kubeadm 1.29）
2. 使用 kubeadm 初始化单节点集群，指定：
   - Pod CIDR 为 192.168.0.0/16
   - 镜像仓库使用 registry.aliyuncs.com/google_containers
3. 安装 Calico CNI 插件
4. 验证集群就绪：kubectl get nodes 显示 Ready
5. 验证系统 Pod：kube-system 命名空间下所有 Pod 均 Running
6. 配置 kubectl 别名 k=kubectl
7. 创建一个 nginx:alpine 测试 Pod，验证能正常运行

【评分标准】
- 集群初始化成功（30 分）
- Calico 安装正确（20 分）
- 节点状态 Ready（20 分）
- 系统 Pod 全部 Running（15 分）
- nginx 测试 Pod Running（10 分）
- 别名配置（5 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `sudo swapoff -a` | 关闭 Swap | kubelet 强制要求，否则拒绝启动 |
| `sudo sed -i '/ swap / s/^/#/' /etc/fstab` | 永久禁用 Swap | 注释 fstab 中 swap 行，重启后仍生效 |
| `sudo modprobe br_netfilter` | 加载 br_netfilter 模块 | 允许桥接流量经过 iptables 处理 |
| `sudo modprobe overlay` | 加载 overlay 模块 | 容器存储驱动依赖 |
| `sudo sysctl --system` | 应用所有 sysctl 配置 | 重新加载 /etc/sysctl.d/ 下所有配置 |
| `sudo dnf install -y containerd.io` | 安装 containerd 运行时 | K8s 1.24+ 默认容器运行时，通过 Docker CE 仓库安装 |
| `containerd config default \| sudo tee /etc/containerd/config.toml` | 生成 containerd 默认配置 | 必须修改 SystemdCgroup = true |
| `sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml` | 启用 SystemdCgroup | 与 kubelet 的 cgroup 驱动保持一致 |
| `sudo systemctl restart containerd && sudo systemctl enable containerd` | 重启并开机自启 containerd | 配置修改后必须重启 |
| `sudo dnf versionlock kubelet kubeadm kubectl` | 锁定 K8s 组件版本 | 防止 dnf upgrade 意外升级导致版本不一致 |
| `sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --kubernetes-version=v1.29.0` | 初始化 K8s 集群 | 下载镜像、生成证书、启动控制平面组件为静态 Pod |
| `mkdir -p $HOME/.kube && sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config` | 配置 kubectl 认证 | 将 admin 证书复制到用户目录 |
| `sudo chown $(id -u):$(id -g) $HOME/.kube/config` | 修改 kubeconfig 权限 | 让普通用户也能使用 kubectl |
| `kubectl apply -f calico.yaml` | 安装 Calico CNI | 提供 Pod 网络和 NetworkPolicy 支持 |
| `kubectl get pods -n kube-system --watch` | 实时监控系统 Pod | 等待 CoreDNS 和 Calico Pod 就绪 |
| `kubectl get nodes` | 查看节点状态 | STATUS 必须为 Ready |
| `kubectl get componentstatuses` | 查看控制平面组件健康 | 检查 scheduler/controller-manager/etcd 状态 |
| `kubectl get --raw='/readyz?verbose'` | 查看 apiserver 就绪探测详情 | 比 componentstatuses 更准确（1.19+） |
| `kubectl cluster-info` | 查看集群信息 | 输出 apiserver 和 CoreDNS 地址 |
| `sudo crictl ps` | 列出容器（containerd） | K8s 1.24+ 替代 docker ps |
| `sudo crictl ps \| grep etcd` | 查找 etcd 容器 ID | 静态 Pod 通过 crictl 管理 |
| `sudo crictl exec -it <etcd-id> sh` | 进入 etcd 容器 | 用于执行 etcdctl 命令探索存储 |
| `ETCDCTL_API=3 etcdctl --cacert=... --cert=... --key=... get / --prefix --keys-only \| head -30` | 列出 etcd 中的 key | 查看集群存储在 etcd 中的资源 |
| `echo 'source <(kubectl completion bash)' >> ~/.bashrc` | 启用 kubectl 自动补全 | 按 Tab 补全命令和资源名 |
| `alias k=kubectl` | 设置 kubectl 别名 | 减少输入量，赛题时间紧张时很有用 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：安装 kubeadm | https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/ |
| Kubernetes 官方：创建集群 | https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/ |
| containerd 官方文档 | https://github.com/containerd/containerd/blob/main/docs/getting-started.md |
| Calico 快速开始 | https://docs.tigera.io/calico/latest/getting-started/kubernetes/quickstart |
| Linux 内核模块 overlay/br_netfilter | https://kubernetes.io/docs/setup/production-environment/container-runtimes/ |
| kubectl 安装与配置 | https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/ |

## 📝 今日笔记模板

```
日期：____年____月____日
用时：____小时____分

✅ 完成项：
□ 架构原理理解
□ 练习 1.1 单节点初始化
□ 练习 1.2 Calico 安装
□ 练习 1.3 kubectl 配置
□ 练习 1.4 组件状态查看
□ 练习 1.5 etcd 探索
□ 排错练习 1-2
□ 赛题模拟

❓ 遇到的问题与解决方案：
1.
2.

📌 关键收获：
1.
2.
3.

⏭️ 明天重点：
```
