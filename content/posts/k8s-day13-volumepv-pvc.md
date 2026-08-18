---
title: Day 13 - Volume 与 PV/PVC
module: M4-存储与配置管理
day: 13
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 12 完成，理解 ConfigMap/Secret 的 Volume 挂载
objectives:
- 掌握 Pod 级别 Volume 类型（emptyDir/hostPath）
- 理解 PV/PVC 的绑定机制
- 掌握 PV 的 AccessMode 和 ReclaimPolicy
- 能创建静态 PV 并绑定 PVC
- 理解 PV 的生命周期
tags:
- Volume
- emptyDir
- hostPath
- PV
- PVC
- 静态供给
date: '2026-08-18'
status: published
---

# 📘 Day 13：Volume 与 PV/PVC

## 🎯 今日目标

- [ ] 会用 emptyDir 和 hostPath Volume
- [ ] 理解 PV/PVC 的绑定流程
- [ ] 能创建静态 PV 并供 Pod 使用
- [ ] 掌握 AccessMode（RWO/ROX/RWX）
- [ ] 掌握 ReclaimPolicy（Retain/Recycle/Delete）

---

## 🧠 理论精讲（30 分钟）

### 存储层次

```
Pod ──→ PVC（声明：我要 5Gi RWO 存储）──→ PV（物理存储：这里是 5Gi NFS）
                                              │
                                              └──→ 实际存储后端（NFS/本地盘/云盘）
```

| 概念 | 说明 | 类比 |
|------|------|------|
| **Volume** | Pod 级别存储定义 | 直接在 Pod 里写磁盘配置 |
| **PV** | 集群级别存储资源 | 管理员准备的存储池 |
| **PVC** | 用户存储请求 | 申请单 |

### PV 关键属性

| 属性 | 可选值 | 说明 |
|------|--------|------|
| **accessModes** | RWO / ROX / RWX | 读写模式 |
| **ReclaimPolicy** | Retain / Recycle / Delete | PV 释放后行为 |
| **volumeMode** | Filesystem / Block | 文件系统还是块设备 |

### AccessMode 速查

| 缩写 | 全称 | 含义 |
|------|------|------|
| **RWO** | ReadWriteOnce | 单节点读写 |
| **ROX** | ReadOnlyMany | 多节点只读 |
| **RWX** | ReadWriteMany | 多节点读写 |

### PV 生命周期

```
Provisioning（创建）→ Available（可用）→ Bound（已绑定）→ Released（释放）
                                                        → Retained（保留）
```

---

## 🔧 动手实操（120 分钟）

### 练习 13.1：emptyDir Volume

```bash
# emptyDir：Pod 生命周期内存在，Pod 删除即销毁
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  containers:
  - name: writer
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      i=0
      while true; do
        echo "Data-$i" >> /data/shared.log
        i=$((i+1))
        sleep 2
      done
    volumeMounts:
    - name: shared-data
      mountPath: /data

  - name: reader
    image: busybox:1.36
    command:
    - sh
    - -c
    - tail -f /data/shared.log
    volumeMounts:
    - name: shared-data
      mountPath: /data

  volumes:
  - name: shared-data
    emptyDir: {}
EOF

# 验证容器间共享
kubectl logs emptydir-demo -c reader --tail=10
# 看到 writer 写入的内容

# 清理
kubectl delete pod emptydir-demo
```

---

### 练习 13.2：hostPath Volume

```bash
# hostPath：挂载节点上的目录
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hostpath-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      echo "Written at \$(date)" >> /host-data/hostpath-test.log
      cat /host-data/hostpath-test.log
      sleep 3600
    volumeMounts:
    - name: host-vol
      mountPath: /host-data
  volumes:
  - name: host-vol
    hostPath:
      path: /tmp/k8s-hostpath
      type: DirectoryOrCreate
EOF

# 获取 Pod 所在节点
NODE=$(kubectl get pod hostpath-demo -o jsonpath='{.spec.nodeName}')
echo "Pod is on: $NODE"

# SSH 到该节点验证文件
# ssh $NODE cat /tmp/k8s-hostpath/hostpath-test.log

# 删除 Pod 后，节点上的文件仍在
kubectl delete pod hostpath-demo
# ssh $NODE cat /tmp/k8s-hostpath/hostpath-test.log  # 文件还在
```

---

### 练习 13.3：静态 PV 创建与绑定

```bash
# 1. 先在节点上创建实际目录
# 在所有 worker 节点上执行：
# sudo mkdir -p /data/pv-volumes/pv01

# 2. 创建 PersistentVolume
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-manual-01
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /data/pv-volumes/pv01
EOF

# 3. 查看 PV 状态
kubectl get pv pv-manual-01
# NAME           CAPACITY  ACCESS MODES  RECLAIM POLICY  STATUS      CLAIM
# pv-manual-01   1Gi       RWO           Retain          Available

# 4. 创建 PersistentVolumeClaim
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-manual-01
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
EOF

# 5. 观察绑定
kubectl get pvc pvc-manual-01
# STATUS: Bound

kubectl get pv pv-manual-01
# STATUS: Bound, CLAIM: default/pvc-manual-01

# 6. 在 Pod 中使用 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: pv-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      echo "Persistent data!" >> /data/persistent.txt
      cat /data/persistent.txt
      sleep 3600
    volumeMounts:
    - name: persistent-storage
      mountPath: /data
  volumes:
  - name: persistent-storage
    persistentVolumeClaim:
      claimName: pvc-manual-01
EOF

# 7. 验证持久性
kubectl exec pv-pod -- cat /data/persistent.txt
# 输出：Persistent data!

# 8. 删除 Pod 和 PVC
kubectl delete pod pv-pod
kubectl delete pvc pvc-manual-01

# 9. 查看 PV 状态
kubectl get pv pv-manual-01
# STATUS: Released（因为 ReclaimPolicy=Retain，不会自动删除）

# 10. 清理 PV
kubectl delete pv pv-manual-01
```

---

### 练习 13.4：多 PV 自动匹配

```bash
# 创建 3 个不同大小的 PV
for i in 1 2 3; do
  mkdir -p /data/pv-volumes/pv0${i}
done

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-small
spec:
  capacity:
    storage: 100Mi
  accessModes: ["ReadWriteOnce"]
  hostPath:
    path: /data/pv-volumes/pv01
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-medium
spec:
  capacity:
    storage: 500Mi
  accessModes: ["ReadWriteOnce"]
  hostPath:
    path: /data/pv-volumes/pv02
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-large
spec:
  capacity:
    storage: 2Gi
  accessModes: ["ReadWriteOnce"]
  hostPath:
    path: /data/pv-volumes/pv03
EOF

# 创建 PVC 请求 300Mi
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-auto
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 300Mi
EOF

# 观察匹配结果（应绑定到 pv-medium，500Mi）
kubectl get pvc pvc-auto
kubectl get pv | grep pvc-auto
# 应绑定到 pv-medium（最小能匹配的 PV）

# 清理
kubectl delete pvc pvc-auto
kubectl delete pv pv-small pv-medium pv-large
```

---

## 🐛 排错练习（30 分钟）

### 场景：PVC 一直 Pending

```bash
# 排查清单
# 1. 有没有 PV？
kubectl get pv
# 如果没有 Available PV → 需要创建 PV 或配置动态供给

# 2. PV 的 accessModes 是否匹配 PVC？
kubectl get pv <pv-name> -o yaml | grep -A3 accessModes
kubectl get pvc <pvc-name> -o yaml | grep -A3 accessModes

# 3. PV 的容量是否 >= PVC？
kubectl get pv <pv-name> -o jsonpath='{.spec.capacity.storage}'
kubectl get pvc <pvc-name> -o jsonpath='{.spec.resources.requests.storage}'

# 4. PVC 的 storageClassName 是否为空字符串？
kubectl get pvc <pvc-name> -o yaml | grep storageClassName
# 如果 PVC 指定了 storageClassName，只能匹配同名的 PV
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：静态 PV 存储管理**

```
【操作要求】

1. 创建 3 个 hostPath 类型的 PV：
   - pv-1g：容量 1Gi，RWO，路径 /data/pv/vol1
   - pv-5g：容量 5Gi，RWO，路径 /data/pv/vol2
   - pv-10g：容量 10Gi，RWO，路径 /data/pv/vol3

2. 创建 2 个 PVC：
   - pvc-db：请求 4Gi，RWO
   - pvc-logs：请求 8Gi，RWO

3. 验证 pvc-db 绑定到 pv-5g，pvc-logs 绑定到 pv-10g

4. 创建一个 Pod 同时使用两个 PVC：
   - db 容器挂载 pvc-db 到 /var/lib/db
   - app 容器挂载 pvc-logs 到 /var/log/app
   - 写入测试数据到各自目录

5. 删除 Pod 和 PVC，检查 PV 状态变化

6. 手动清理 PV，释放存储

【评分标准】
- PV 创建正确（20 分）
- PVC 绑定结果正确（25 分）
- Pod 双 Volume 挂载正确（25 分）
- 数据持久性验证（15 分）
- PV 生命周期理解（15 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get pv` | 列出 PersistentVolume | STATUS: Available (空闲)/Bound (已绑定)/Released (PVC 已删但未回收)/Failed |
| `kubectl get pv -o wide` | PV + 容量/访问模式/回收策略/状态/声明 | 快速审计存储资源 |
| `kubectl describe pv <name>` | PV 详细信息 | 查看 Reclaim Policy、AccessModes、底层存储类型（hostPath/NFS/CSI 等） |
| `kubectl get pvc` | 列出 PersistentVolumeClaim | STATUS: Pending (无匹配 PV)/Bound (已绑定) |
| `kubectl get pvc -A` | 所有命名空间的 PVC | 跨 NS 视角排查存储资源使用 |
| `kubectl describe pvc <name>` | PVC 详细信息 | Events 段显示绑定过程；Pending 时查看失败原因 |
| `kubectl get pv,pvc` | 同时查看 PV/PVC | 逗号分隔查看绑定关系 |
| `kubectl patch pv <name> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'` | 修改 PV 回收策略 | 防止 PVC 删除时 PV 被自动回收（Retain/Recycle/Delete） |
| `kubectl delete pvc <name>` | 删除 PVC | PV 的 Reclaim Policy 决定 PV 后续状态 |
| `kubectl get pods -o wide \| grep <pod>` | 查看 Pod 所在节点 | PV hostPath 必须确认 Pod 调度到了正确节点 |
| `kubectl exec <pod> -- df -h` | 查看 Pod 内挂载存储空间 | 验证 PV 是否挂载成功及容量是否正确 |
| `kubectl exec <pod> -- ls -la /mnt/data` | 查看挂载目录内容 | 验证文件是否存在和权限 |
| `kubectl exec <pod> -- touch /mnt/data/test && echo "ok" > /mnt/data/test` | 验证存储读写 | 确认 PV 不是只读挂载 |
| `kubectl get sc` | 列出 StorageClass | 动态供给与 PV/PVC 配合使用 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：PersistentVolume | https://kubernetes.io/docs/concepts/storage/persistent-volumes/ |
| Kubernetes 官方：卷 | https://kubernetes.io/docs/concepts/storage/volumes/ |
| Kubernetes 官方：配置 Pod 使用 PV | https://kubernetes.io/docs/concepts/storage/persistent-volumes/ |
| Kubernetes 官方：访问模式 | https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes |
| Kubernetes 官方：回收策略 | https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaim-policy |
