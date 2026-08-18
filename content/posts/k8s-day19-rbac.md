---
title: Day 19 - RBAC 权限控制
module: M6-安全与认证
day: 19
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M2 完成，理解 K8s 资源对象
objectives:
- 理解 RBAC 四要素：Subject/Role/ClusterRole/RoleBinding/ClusterRoleBinding
- 掌握 Role 和 ClusterRole 的创建
- 掌握 RoleBinding 和 ClusterRoleBinding
- 能用 kubectl auth can-i 验证权限
- 掌握 kubeconfig 中用户/上下文切换
tags:
- RBAC
- Role
- ClusterRole
- RoleBinding
- ClusterRoleBinding
- ServiceAccount
date: '2026-08-18'
status: published
---

# 📘 Day 19：RBAC 权限控制

## 🎯 今日目标

- [ ] 理解 RBAC 的四个核心概念
- [ ] 能创建 Role 并绑定到用户/ServiceAccount
- [ ] 会用 kubectl auth can-i 验证权限
- [ ] 能排查 Permission Denied 错误

---

## 🧠 理论精讲（30 分钟）

### RBAC 四要素

```
Subject（谁）────→ RoleBinding ────→ Role（能做什么）
    │                                     │
    ├── User                             ├── apiGroups
    ├── Group                            ├── resources
    └── ServiceAccount                   └── verbs
```

| 概念 | 作用域 | 说明 |
|------|--------|------|
| **Role** | 命名空间 | 定义在某 NS 下的权限 |
| **ClusterRole** | 集群 | 定义集群级别权限 |
| **RoleBinding** | 命名空间 | 将 Role 绑定到主体 |
| **ClusterRoleBinding** | 集群 | 将 ClusterRole 绑定到主体 |

### 常见 verbs

| verb | 含义 | 对应 kubectl |
|------|------|-------------|
| `get` | 查看单个资源 | `kubectl get pod xxx` |
| `list` | 列出资源 | `kubectl get pods` |
| `watch` | 监听资源变化 | `kubectl get pods -w` |
| `create` | 创建 | `kubectl create/apply` |
| `update` | 修改 | `kubectl edit/patch` |
| `delete` | 删除 | `kubectl delete` |

---

## 🔧 动手实操（120 分钟）

### 练习 19.1：创建 ServiceAccount + Role + RoleBinding

```bash
# 1. 创建命名空间
kubectl create ns rbac-demo

# 2. 创建 ServiceAccount
kubectl create sa developer -n rbac-demo

# 3. 创建 Role（只读 Pod）
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: rbac-demo
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]
EOF

# 4. 创建 RoleBinding
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-pod-reader
  namespace: rbac-demo
subjects:
- kind: ServiceAccount
  name: developer
  namespace: rbac-demo
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
EOF

# 5. 验证权限
kubectl auth can-i get pods -n rbac-demo --as=system:serviceaccount:rbac-demo:developer
# yes

kubectl auth can-i create pods -n rbac-demo --as=system:serviceaccount:rbac-demo:developer
# no

kubectl auth can-i delete pods -n rbac-demo --as=system:serviceaccount:rbac-demo:developer
# no

# 6. 查看完整权限列表
kubectl auth can-i --list -n rbac-demo --as=system:serviceaccount:rbac-demo:developer
```

---

### 练习 19.2：ClusterRole + ClusterRoleBinding

```bash
# 1. 创建 ClusterRole（集群级别只读）
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-viewer
rules:
- apiGroups: [""]
  resources: ["nodes", "namespaces", "pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch"]
EOF

# 2. 创建 ServiceAccount
kubectl create sa auditor -n rbac-demo

# 3. ClusterRoleBinding
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: auditor-viewer
subjects:
- kind: ServiceAccount
  name: auditor
  namespace: rbac-demo
roleRef:
  kind: ClusterRole
  name: cluster-viewer
  apiGroup: rbac.authorization.k8s.io
EOF

# 4. 验证集群级别权限
kubectl auth can-i get nodes --as=system:serviceaccount:rbac-demo:auditor
# yes

kubectl auth can-i get deploy --as=system:serviceaccount:rbac-demo:auditor
# yes

kubectl auth can-i delete nodes --as=system:serviceaccount:rbac-demo:auditor
# no
```

---

### 练习 19.3：创建受限 kubeconfig

```bash
# 1. 获取 SA 的 Token
kubectl create token developer -n rbac-demo
# 复制输出的 token

# 或者创建长期有效的 token（K8s 1.24+）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: developer-token
  namespace: rbac-demo
  annotations:
    kubernetes.io/service-account.name: developer
type: kubernetes.io/service-account-token
EOF

# 获取 token
TOKEN=$(kubectl get secret developer-token -n rbac-demo -o jsonpath='{.data.token}' | base64 -d)

# 2. 获取集群 CA 证书
kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > /tmp/ca.crt

# 3. 构建 kubeconfig
kubectl config set-cluster dev-cluster \
  --server=$(kubectl config view --raw -o jsonpath='{.clusters[0].cluster.server}') \
  --certificate-authority=/tmp/ca.crt \
  --embed-certs=true \
  --kubeconfig=/tmp/dev-kubeconfig

kubectl config set-credentials developer \
  --token=$TOKEN \
  --kubeconfig=/tmp/dev-kubeconfig

kubectl config set-context dev-context \
  --cluster=dev-cluster \
  --namespace=rbac-demo \
  --user=developer \
  --kubeconfig=/tmp/dev-kubeconfig

kubectl config use-context dev-context --kubeconfig=/tmp/dev-kubeconfig

# 4. 使用受限配置测试
kubectl get pods -n rbac-demo --kubeconfig=/tmp/dev-kubeconfig
# 正常返回

kubectl create deploy test --image=nginx:alpine -n rbac-demo --kubeconfig=/tmp/dev-kubeconfig
# Error: forbidden
```

---

### 练习 19.4：实战 RBAC 排错

```bash
# 1. 排查 "cannot get resource" 错误
# 错误信息：Error from server (Forbidden): pods is forbidden

# 排查步骤
kubectl auth can-i get pods --as=<user>
# 如果是 no → 检查 Role/RoleBinding
kubectl get rolebinding -A | grep <user>
kubectl describe rolebinding <name> -n <ns>

# 2. 查看某个 SA 拥有的所有权限
kubectl auth can-i --list --as=system:serviceaccount:rbac-demo:developer -n rbac-demo

# 3. 检查是否有 ClusterRoleBinding（影响更大）
kubectl get clusterrolebinding -o wide | grep <user>
```

---

## 🐛 排错练习（30 分钟）

### 常见 RBAC 错误排查

```bash
# 错误 1: "User system:serviceaccount:default:default cannot create resource"
# → 默认 SA 没有写权限，需要创建专用的 SA + RoleBinding

# 错误 2: "cannot list resource in API group"
# → Role 中 apiGroups 配置错误，检查资源属于哪个 API 组
kubectl api-resources | grep <resource>

# 错误 3: "cannot get resource at cluster scope"
# → 命名空间级别的 Role 不能访问集群级别资源，需用 ClusterRole
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：RBAC 权限体系设计**

```
【操作要求】

1. 创建命名空间 project-alpha

2. 创建 3 个 ServiceAccount：
   - sa-admin（管理员）
   - sa-developer（开发者）
   - sa-viewer（只读用户）

3. 创建 3 个 Role / ClusterRole：
   a. Role admin-role（namespace: project-alpha）：
      - 对 pods/deployments/services/configmaps/secrets 有全部权限
   b. Role developer-role（namespace: project-alpha）：
      - 对 pods/deployments/services/configmaps 有 get/list/watch/create/update
      - 对 pods/log 有 get/list
      - 对 secrets 无权限
   c. ClusterRole viewer-role：
      - 对所有命名空间的 pods/deployments/services 有 get/list/watch

4. 绑定：
   - sa-admin → admin-role（RoleBinding）
   - sa-developer → developer-role（RoleBinding）
   - sa-viewer → viewer-role（ClusterRoleBinding）

5. 验证：
   - sa-admin 能创建/删除 Pod
   - sa-developer 能创建 Pod 但不能查看 Secret
   - sa-viewer 能查看所有命名空间的 Pod
   - sa-viewer 无法创建 Pod

【评分标准】
- SA 创建（10 分）
- Role/ClusterRole 权限粒度正确（40 分）
- RoleBinding/ClusterRoleBinding 正确（20 分）
- 权限验证（30 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl auth can-i create pods` | 检查当前用户权限 | 快速验证 RBAC 配置是否正确 |
| `kubectl auth can-i create pods --as=system:serviceaccount:<ns>:<sa>` | 检查某 SA 权限 | 调试 ServiceAccount 权限问题 |
| `kubectl auth can-i --list` | 列出当前用户所有权限 | 输出完整的资源-动词矩阵 |
| `kubectl auth can-i '*' '*'` | 检查是否集群管理员 | 返回 yes 说明拥有全部权限 |
| `kubectl get role -A` | 列出所有 Role | 命名空间级权限 |
| `kubectl get rolebinding -A` | 列出所有 RoleBinding | 查看 Role 与用户/SA 的绑定关系 |
| `kubectl get clusterrole` | 列出 ClusterRole | 集群级权限（节点、PV、StorageClass 等） |
| `kubectl get clusterrolebinding` | 列出 ClusterRoleBinding | 集群级绑定关系 |
| `kubectl describe role <name> -n <ns>` | Role 详情 | 查看具体允许的资源和动词 |
| `kubectl describe clusterrole <name>` | ClusterRole 详情 | 系统自带 cluster-admin/edit/view 的权限范围 |
| `kubectl create role <name> --verb=get,list,watch --resource=pods -n <ns>` | 快速创建 Role | `--verb` 和 `--resource` 即可，无需手写 YAML |
| `kubectl create rolebinding <name> --role=<role> --user=<user> -n <ns>` | 绑定 Role 到用户 | 给真实用户授权 |
| `kubectl create rolebinding <name> --role=<role> --serviceaccount=<ns>:<sa> -n <ns>` | 绑定 Role 到 SA | 给 ServiceAccount 授权 |
| `kubectl create clusterrole <name> --verb=get,list --resource=nodes` | 创建 ClusterRole | 集群级资源必须用 ClusterRole |
| `kubectl create clusterrolebinding <name> --clusterrole=<role> --serviceaccount=<ns>:<sa>` | 绑定 ClusterRole 到 SA | 跨命名空间的 SA 绑定集群级权限 |
| `kubectl get sa -A` | 列出所有 ServiceAccount | 每个 NS 有默认 default SA |
| `kubectl get secrets \| grep <sa>-token` | 查找 SA 的 Token Secret | 1.24+ 不再自动创建，需手动 `kubectl create token <sa>` |
| `kubectl create token <sa> -n <ns>` | 创建 SA 临时 Token | 1.24+ 推荐方式，有时效性 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：RBAC | https://kubernetes.io/docs/reference/access-authn-authz/rbac/ |
| Kubernetes 官方：鉴权概述 | https://kubernetes.io/docs/reference/access-authn-authz/authorization/ |
| Kubernetes 官方：使用 RBAC 授权 | https://kubernetes.io/docs/reference/access-authn-authz/rbac/#command-line-utilities |
| Kubernetes 官方：ServiceAccount | https://kubernetes.io/docs/concepts/security/service-accounts/ |
| Kubernetes 官方：kubectl auth can-i | https://kubernetes.io/docs/reference/access-authn-authz/authorization/#checking-api-access |
