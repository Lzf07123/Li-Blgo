---
title: Day 15 - 存储综合实战
module: M4-存储与配置管理
day: 15
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- M4 Day 12-14 全部完成
objectives:
- 综合 ConfigMap + Secret + PV/PVC + StorageClass
- 构建有状态应用的完整存储方案
- 故障演练：模拟存储故障排查
tags:
- 综合实战
- 有状态应用
- 存储排错
date: '2026-08-18'
status: published
---

# 📘 Day 15：存储综合实战

## 🎯 今日目标

- [ ] 为有状态应用配置完整存储方案
- [ ] ConfigMap → Secret → PVC 联动配置
- [ ] 排查存储相关故障

---

## 🧠 理论精讲（10 分钟）

### 存储方案决策树

```
应用需要存储配置？
├── 非敏感配置 → ConfigMap
├── 敏感配置（密码/证书）→ Secret
└── 持久数据？
    ├── 临时数据（Pod 删了就丢）→ emptyDir
    ├── 节点级数据（日志）→ hostPath
    └── 持久数据（数据库）→ PVC（+StorageClass 动态供给）
```

---

## 🔧 动手实操（150 分钟）

### 练习 15.1：WordPress 风格有状态应用

```bash
kubectl create ns wp-demo

# 1. 配置管理：ConfigMap
kubectl create configmap wp-config -n wp-demo \
  --from-literal=WORDPRESS_DB_HOST=mysql-svc \
  --from-literal=WORDPRESS_DB_USER=wp_user \
  --from-literal=WORDPRESS_DB_NAME=wordpress \
  --from-literal=WORDPRESS_DEBUG=false

# 2. 密钥管理：Secret
kubectl create secret generic wp-secrets -n wp-demo \
  --from-literal=WORDPRESS_DB_PASSWORD='W0rdPr3ss!' \
  --from-literal=MYSQL_ROOT_PASSWORD='R00tP@ss!'

# 3. 数据库 StatefulSet + PVC
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: mysql-svc
  namespace: wp-demo
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - port: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: wp-demo
spec:
  serviceName: mysql-svc
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        envFrom:
        - secretRef:
            name: wp-secrets
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 2Gi
EOF

# 4. WordPress Deployment
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wordpress
  namespace: wp-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wordpress
  template:
    metadata:
      labels:
        app: wordpress
    spec:
      containers:
      - name: wordpress
        image: wordpress:6-apache
        envFrom:
        - configMapRef:
            name: wp-config
        env:
        - name: WORDPRESS_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wp-secrets
              key: WORDPRESS_DB_PASSWORD
        ports:
        - containerPort: 80
        volumeMounts:
        - name: wp-content
          mountPath: /var/www/html/wp-content
      volumes:
      - name: wp-content
        persistentVolumeClaim:
          claimName: wp-content-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: wp-content-pvc
  namespace: wp-demo
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
EOF

# 5. 服务暴露
kubectl expose deploy wordpress -n wp-demo --port=80
kubectl get all -n wp-demo
```

---

### 练习 15.2：存储故障排查

```bash
# 故障 1：PVC 绑定不上
kubectl get pvc -n wp-demo
# 如果 Pending，排查：
kubectl describe pvc wp-content-pvc -n wp-demo
# 看 Events → 是否有可用的 PV 或 StorageClass？

# 故障 2：Pod 无法挂载 Volume
kubectl get pod -n wp-demo
kubectl describe pod <pod-name> -n wp-demo | grep -A5 Events
# 常见错误：mount failed、permission denied

# 故障 3：ConfigMap 环境变量未注入
kubectl exec <pod> -n wp-demo -- env | grep WORDPRESS
# 如果没有 → 检查 envFrom 配置

# 故障 4：Secret 值不正确
kubectl get secret wp-secrets -n wp-demo -o jsonpath='{.data.WORDPRESS_DB_PASSWORD}' | base64 -d
# 验证解码后的值
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：完整应用配置与存储方案**

```
【操作要求】创建命名空间 cms-app

1. ConfigMap cms-config：
   - SITE_NAME="My CMS"
   - DB_HOST=cms-db-svc
   - CACHE_TTL=3600

2. Secret cms-secrets：
   - DB_PASS=db-secret-789
   - ADMIN_PASS=admin-secret-456
   - JWT_SECRET=jwt-key-012

3. StatefulSet cms-db（2 副本，mysql:8.0）：
   - 使用 cms-secrets 注入数据库密码
   - volumeClaimTemplates 创建 2Gi PVC
   - Headless Service cms-db-svc

4. Deployment cms-web（3 副本，nginx:alpine）：
   - 用 envFrom 注入 cms-config
   - 用 valueFrom 注入 DB_PASS（命名 DATABASE_PASSWORD）
   - 挂载 PVC cms-web-data（1Gi）到 /usr/share/nginx/html/uploads
   - livenessProbe + readinessProbe

5. 验证：
   - 所有 PVC 绑定成功
   - Pod 环境变量包含 SITE_NAME、DB_HOST、DATABASE_PASSWORD
   - cms-db-0 和 cms-db-1 有独立 PVC
   - 向 cms-web 的 PVC 写入测试文件

【评分标准】
- ConfigMap/Secret 创建正确（15 分）
- StatefulSet + PVC 正确（30 分）
- Deployment 配置注入正确（30 分）
- PVC 独立验证（15 分）
- 验证全面（10 分）
```

---

## 🧹 环境清理

```bash
kubectl delete ns wp-demo cms-app
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get pv,pvc,sc` | 存储资源一览 | 同时查看 PV/PVC/SC 的绑定和供给关系 |
| `kubectl get pvc -A --field-selector=status.phase=Pending` | 查找所有未绑定的 PVC | Pending 意味着没有匹配的 PV 或 SC 供给失败 |
| `kubectl get events --field-selector=reason=ProvisioningFailed` | 查看供给失败事件 | 动态供给失败时的排错入口 |
| `kubectl exec <pod> -- df -h \| grep /mnt` | 验证存储挂载容量 | 确认 PV 正确挂载且容量匹配 |
| `kubectl exec <pod> -- cat /proc/mounts \| grep /mnt` | 查看挂载详情 | 文件系统类型、挂载选项 |
| `kubectl exec <pod> -- touch /mnt/data/write-test` | 验证存储可写 | ReadWriteOnce 模式下测试写权限 |
| `kubectl exec <pod> -- rm /mnt/data/write-test` | 验证存储可删除 | ReadWriteMany 多 Pod 同时操作验证 |
| `kubectl diff -f manifest.yaml` | 预览修改差异 | 综合实战中修改 YAML 后先 diff 确认变更 |
| `kubectl apply --server-side -f manifest.yaml` | 服务端 Apply | 处理大文件或复杂 CRD 时的备选方案 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：存储最佳实践 | https://kubernetes.io/docs/concepts/storage/ |
| Kubernetes 官方：调试 PVC | https://kubernetes.io/docs/tasks/debug/debug-application/ |
| Kubernetes 官方：StatefulSet 与存储 | https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#using-statefulsets |
| Kubernetes 存储 SIG | https://github.com/kubernetes/community/tree/master/sig-storage |
