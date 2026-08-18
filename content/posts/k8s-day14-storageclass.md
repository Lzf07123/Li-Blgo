---
title: Day 14 - StorageClass 与动态供给
module: M4-存储与配置管理
day: 14
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 13 完成，理解 PV/PVC 静态绑定
objectives:
- 理解 StorageClass 的作用
- 掌握 NFS 动态供给配置
- 配置 default StorageClass
- 理解 volumeBindingMode
- 掌握 PVC 扩容操作
tags:
- StorageClass
- 动态供给
- NFS
- provisioner
- PVC 扩容
date: '2026-08-18'
status: published
---

# 📘 Day 14：StorageClass 与动态供给

## 🎯 今日目标

- [ ] 理解 StorageClass 如何实现"按需创建 PV"
- [ ] 能部署 NFS Provisioner 实现动态供给
- [ ] 掌握 default StorageClass 的设置
- [ ] 能做 PVC 在线扩容
- [ ] 理解 Immediate vs WaitForFirstConsumer

---

## 🧠 理论精讲（30 分钟）

### 为什么需要 StorageClass

静态 PV 的问题：**每次创建 PVC 前都要手动创建 PV**，管理员负担重。

```
动态供给：
PVC 创建 → StorageClass → Provisioner → 自动创建 PV → 绑定 PVC
```

### StorageClass 关键参数

| 参数 | 含义 |
|------|------|
| `provisioner` | 供给驱动（如 nfs.csi.k8s.io） |
| `volumeBindingMode` | Immediate（立即）/ WaitForFirstConsumer（延迟） |
| `reclaimPolicy` | Delete（默认）/ Retain |
| `allowVolumeExpansion` | 是否允许 PVC 扩容 |

### volumeBindingMode

| 模式 | 行为 |
|------|------|
| **Immediate** | PVC 创建后立即绑定 PV（不考虑 Pod 调度） |
| **WaitForFirstConsumer** | 等到 Pod 实际使用时才创建 PV（保证 PV 和 Pod 在同一可用区） |

---

## 🔧 动手实操（120 分钟）

### 练习 14.1：NFS 动态供给环境准备

```bash
# === 在 Master 或独立存储节点上安装 NFS Server ===

# 1. 安装 NFS 服务端
sudo dnf install -y nfs-utils

# 2. 创建共享目录
sudo mkdir -p /srv/nfs/k8s
sudo chown nobody:nobody /srv/nfs/k8s
sudo chmod 777 /srv/nfs/k8s

# 3. 配置 exports
echo "/srv/nfs/k8s *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
sudo exportfs -rav
sudo systemctl enable --now nfs-server

# 4. 验证 NFS 可用（在 worker 节点测试）
# sudo dnf install -y nfs-utils
# sudo mount -t nfs <master-ip>:/srv/nfs/k8s /mnt
# ls /mnt
# sudo umount /mnt
```

---

### 练习 14.2：部署 NFS Subdir External Provisioner

```bash
# 1. 创建 RBAC + Deployment
# 这是社区维护的 NFS 动态供给器

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: nfs-provisioner
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: nfs-provisioner-runner
rules:
- apiGroups: [""]
  resources: ["persistentvolumes"]
  verbs: ["get", "list", "watch", "create", "delete"]
- apiGroups: [""]
  resources: ["persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "update"]
- apiGroups: ["storage.k8s.io"]
  resources: ["storageclasses"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["events"]
  verbs: ["create", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: nfs-provisioner-runner
subjects:
- kind: ServiceAccount
  name: nfs-provisioner
  namespace: default
roleRef:
  kind: ClusterRole
  name: nfs-provisioner-runner
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfs-provisioner
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nfs-provisioner
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: nfs-provisioner
    spec:
      serviceAccountName: nfs-provisioner
      containers:
      - name: nfs-provisioner
        image: registry.cn-hangzhou.aliyuncs.com/google_containers/nfs-subdir-external-provisioner:v4.0.2
        env:
        - name: PROVISIONER_NAME
          value: k8s-sigs.io/nfs-subdir-external-provisioner
        - name: NFS_SERVER
          value: "10.0.0.1"              # 替换为你的 NFS 服务器 IP
        - name: NFS_PATH
          value: /srv/nfs/k8s
        volumeMounts:
        - name: nfs-root
          mountPath: /persistentvolumes
      volumes:
      - name: nfs-root
        nfs:
          server: 10.0.0.1               # 替换为你的 NFS 服务器 IP
          path: /srv/nfs/k8s
EOF

# 2. 创建 StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-sc
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
reclaimPolicy: Delete
volumeBindingMode: Immediate
EOF

# 3. 验证
kubectl get sc
# NAME               PROVISIONER                                    RECLAIMPOLICY
# nfs-sc (default)   k8s-sigs.io/nfs-subdir-external-provisioner   Delete

kubectl get pod -l app=nfs-provisioner
# Running
```

---

### 练习 14.3：动态创建 PVC

```bash
# 1. 创建 PVC（不再需要手动创建 PV！）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  storageClassName: nfs-sc
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 1Gi
EOF

# 2. 观察自动创建 PV
kubectl get pvc dynamic-pvc
# STATUS: Bound

kubectl get pv
# 看到自动创建的 PV（名称如 pvc-xxx-xxx-xxx）

# 3. 在 Pod 中使用
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: dynamic-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      echo "Dynamic provision test" > /data/test.txt
      cat /data/test.txt
      sleep 3600
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: dynamic-pvc
EOF

# 4. 验证 NFS 服务器上的实际文件
# ssh 到 NFS 服务器
ls /srv/nfs/k8s/
# 看到自动创建的目录（命名格式：<namespace>-<pvc-name>-<uuid>）

# 5. 清理
kubectl delete pod dynamic-pod
kubectl delete pvc dynamic-pvc
# PV 会自动删除（因为 reclaimPolicy: Delete）
```

---

### 练习 14.4：PVC 扩容

```bash
# 1. 首先确保 StorageClass 允许扩容
kubectl get sc nfs-sc
# 修改 StorageClass 允许扩容
kubectl patch sc nfs-sc -p '{"allowVolumeExpansion":true}'

# 2. 创建 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: expandable-pvc
spec:
  storageClassName: nfs-sc
  accessModes: ["ReadWriteMany"]
  resources:
    requests:
      storage: 1Gi
EOF

# 3. 扩容 PVC（修改 requests.storage）
kubectl patch pvc expandable-pvc -p '{"spec":{"resources":{"requests":{"storage":"3Gi"}}}}'

# 4. 观察 PVC 状态
kubectl get pvc expandable-pvc -w
# CAPACITY 从 1Gi 逐渐变为 3Gi

# 5. 验证
kubectl get pvc expandable-pvc
kubectl get pv | grep expandable-pvc

# 6. 清理
kubectl delete pvc expandable-pvc
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：PVC Pending — Provisioner 未运行

```bash
# 排查：
# 1. Provisioner Pod 是否运行？
kubectl get pod -l app=nfs-provisioner

# 2. 查看 Provisioner 日志
kubectl logs -l app=nfs-provisioner --tail=50

# 3. 检查 NFS 连通性
kubectl exec -it <provisioner-pod> -- sh -c "showmount -e <NFS_SERVER>"

# 4. 检查 StorageClass 的 provisioner 名称是否匹配
kubectl get sc nfs-sc -o yaml | grep provisioner
```

### 场景 2：扩容失败

```bash
# 原因 1：StorageClass 不允许扩容
kubectl get sc <name> -o yaml | grep allowVolumeExpansion

# 原因 2：请求的容量小于当前容量
# PVC 只能扩容不能缩容

# 原因 3：PVC 正在被 Pod 使用
# 某些 CSI 驱动要求在 Pod 运行时才能扩容
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：动态存储与扩容**

```
【前置条件】
NFS 服务器已部署（IP: 10.0.0.1），共享路径 /srv/nfs/k8s

【操作要求】

1. 部署 NFS Subdir External Provisioner
2. 创建 StorageClass nfs-retain（provisioner 指向 NFS，reclaimPolicy=Retain）
3. 将此 StorageClass 设为默认
4. 创建 PVC data-pvc：5Gi, ReadWriteMany
5. 验证自动创建了 PV
6. 创建 Pod data-app 使用此 PVC，挂载到 /app-data，写入测试数据
7. 将 PVC 扩容到 8Gi
8. 验证数据在扩容后仍然完整
9. 删除 Pod 和 PVC
10. 确认 PV 变为 Released 状态（因为 reclaimPolicy=Retain）

【评分标准】
- Provisioner 部署正确（25 分）
- StorageClass 配置正确（20 分）
- 动态供给工作正常（20 分）
- 扩容成功 + 数据完整（25 分）
- ReclaimPolicy 验证（10 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get sc` | 列出 StorageClass | 默认 SC 标记为 `(default)` |
| `kubectl get sc -o yaml` | StorageClass 详细配置 | 查看 provisioner、parameters、reclaimPolicy、allowVolumeExpansion |
| `kubectl describe sc <name>` | StorageClass 详情 | 包含创建事件和配置参数 |
| `kubectl patch sc <name> -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'` | 设为默认 StorageClass | 不指定 storageClassName 的 PVC 自动使用默认 SC |
| `kubectl patch sc <name> -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'` | 取消默认 StorageClass | 防止误用不想要的 SC |
| `kubectl patch sc <name> -p '{"allowVolumeExpansion":true}'` | 启用卷在线扩容 | PVC spec.resources.requests.storage 允许增大 |
| `kubectl get pvc -o wide` | PVC + 绑定的 PV + SC | 确认 PVC 使用了哪个 StorageClass |
| `kubectl describe pvc <name>` | PVC 详情 | Events 显示 Provisioning/FailedProvisioning 过程 |
| `kubectl delete pvc <name> && kubectl get pv -w` | 观察 PVC 删除后 PV 回收 | Reclaim Policy: Delete 时 PV 自动消失；Retain 时 PV 变为 Released |
| `kubectl patch pvc <name> -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'` | 扩容 PVC | 需要 SC 启用 allowVolumeExpansion；只能增大不能缩小 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：StorageClass | https://kubernetes.io/docs/concepts/storage/storage-classes/ |
| Kubernetes 官方：动态卷供给 | https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/ |
| Kubernetes 官方：卷扩容 | https://kubernetes.io/docs/concepts/storage/persistent-volumes/#expanding-persistent-volumes-claims |
| Kubernetes 官方：CSI 驱动 | https://kubernetes-csi.github.io/docs/ |
| NFS Subdir External Provisioner | https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner |
| Rancher Local Path Provisioner | https://github.com/rancher/local-path-provisioner |

## 📝 今日笔记模板
