---
title: Day 21 - 安全综合实战
module: M6-安全与认证
day: 21
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M6 Day 19-20 全部完成
objectives:
- RBAC + SecurityContext + NetworkPolicy 三合一
- 构建安全的应用部署方案
- 完成安全审计检查清单
tags:
- 综合实战
- 安全加固
- NetworkPolicy
- RBAC
- SecurityContext
date: '2026-08-18'
status: published
---

# 📘 Day 21：安全综合实战

## 🎯 今日目标

- [ ] 综合 RBAC + SecurityContext + NetworkPolicy 构建安全体系
- [ ] 完成一次完整的安全审计
- [ ] 排查安全相关故障

---

## 🧠 理论精讲（10 分钟）

### K8s 安全 4C 模型

```
Cloud → Cluster → Container → Code
  ↓        ↓         ↓         ↓
 云安全   集群安全   容器安全   应用安全
(防火墙)  (RBAC)   (Seccomp)  (输入校验)
          (NetworkPolicy)
          (etcd 加密)
```

---

## 🔧 动手实操（150 分钟）

### 练习 21.1：安全应用全栈部署

```bash
kubectl create ns secure-stack

# === 1. ServiceAccount ===
kubectl create sa app-runner -n secure-stack

# === 2. RBAC（最小权限） ===
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
  namespace: secure-stack
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["app-config"]     # 只能访问特定 ConfigMap
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-runner-binding
  namespace: secure-stack
subjects:
- kind: ServiceAccount
  name: app-runner
  namespace: secure-stack
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io
EOF

# === 3. Deploy + SecurityContext ===
kubectl create configmap app-config -n secure-stack \
  --from-literal=ENV=production

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-web
  namespace: secure-stack
spec:
  replicas: 2
  selector:
    matchLabels:
      app: secure-web
  template:
    metadata:
      labels:
        app: secure-web
    spec:
      serviceAccountName: app-runner
      automountServiceAccountToken: false
      securityContext:
        runAsUser: 1001
        runAsNonRoot: true
        fsGroup: 1001
      containers:
      - name: web
        image: nginx:alpine
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: false
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /
            port: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
EOF

kubectl expose deploy secure-web -n secure-stack --port=80

# === 4. NetworkPolicy ===
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: secure-web-policy
  namespace: secure-stack
spec:
  podSelector:
    matchLabels:
      app: secure-web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: ingress-nginx
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
EOF

# 验证部署
kubectl get all -n secure-stack
kubectl get networkpolicy -n secure-stack
```

---

### 练习 21.2：安全审计检查清单

```bash
# 1. 检查特权容器
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].securityContext.privileged==true) | .metadata.name'

# 2. 检查以 root 运行的容器
kubectl get pods --all-namespaces -o json | \
  jq '[.items[] | select(.spec.containers[].securityContext.runAsNonRoot!=true)] | length'

# 3. 检查未设资源限制的 Pod
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].resources.requests==null) | "\(.metadata.namespace)/\(.metadata.name)"'

# 4. 检查过于宽泛的 RBAC 权限
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.kind=="User" and .subjects[]?.name=="system:anonymous")'

# 5. 检查 Secret 是否明文（检查 etcd 加密状态）
kubectl get --raw=/api/v1/secrets | jq '.items[].type' | sort | uniq -c

# 6. 检查是否有 Pod 挂载了 hostPath
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.volumes[]?.hostPath!=null) | "\(.metadata.namespace)/\(.metadata.name)"'
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：安全加固综合**

```
【初始环境】：已有的 Deployment app-insecure 存在安全问题

【操作要求】

1. 安全审计（找出以下问题）：
   - 容器以 root 运行
   - 没有资源限制
   - 使用 default SA（权限过大）
   - 没有 NetworkPolicy
   - 挂载了 hostPath

2. 安全加固：
   a. 创建专用 SA app-secure，禁用 auto-mount
   b. 创建最小权限 Role（只读自己的 ConfigMap）
   c. SecurityContext：
      - runAsUser 1001, runAsNonRoot
      - drop ALL capabilities
      - readOnlyRootFilesystem（需补充 emptyDir 给 tmp）
   d. 添加资源限制
   e. 移除 hostPath，改用 emptyDir 或 PVC
   f. 创建 NetworkPolicy：
      - Ingress：只允许同命名空间 + Ingress Controller
      - Egress：只允许 DNS + 同命名空间

3. 验证：
   - kubectl auth can-i 验证 SA 权限
   - kubectl exec 验证非 root 运行
   - 验证 NetworkPolicy 隔离

【评分标准】
- 安全审计发现所有问题（20 分）
- SA + RBAC 配置（20 分）
- SecurityContext 加固（25 分）
- NetworkPolicy 配置（20 分）
- hostPath 移除（15 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>` | 列出 SA 的完整权限 | RBAC 问题排查第一命令 |
| `kubectl get role,rolebinding,clusterrole,clusterrolebinding -A` | RBAC 全貌 | 安全审计时快速扫描所有权限配置 |
| `kubectl get sa -A` | 所有命名空间的 SA | 检查冗余 SA |
| `kubectl get pods -o json \| jq '.items[] \| {name:.metadata.name, sa:.spec.serviceAccountName, securityContext:.spec.securityContext, containerSecurity:.spec.containers[].securityContext}'` | 审计 Pod 安全上下文 | jq 一次性提取安全相关字段 |
| `kubectl get pods -o json \| jq '[.items[] \| select(.spec.containers[].securityContext.privileged==true)]'` | 查找特权容器 | 安全审计：特权容器可以逃逸 |
| `kubectl get pods -o json \| jq '[.items[] \| select(.spec.hostNetwork==true)]'` | 查找使用 hostNetwork 的 Pod | 可以监听节点网络接口，高风险 |
| `kubectl get pods -o json \| jq '[.items[] \| select(.spec.volumes[]?.hostPath)]'` | 查找挂载 hostPath 的 Pod | 可以访问节点文件系统 |
| `kubectl -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' \| grep -A 5 "apiServer"` | 查看 apiserver 启动参数 | 确认准入控制器和加密配置 |
| `kubectl get --raw /apis/authorization.k8s.io/v1/selfsubjectaccessreviews` | 自检 API 访问 | 编程式权限检查的 API 版 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：安全总览 | https://kubernetes.io/docs/concepts/security/ |
| Kubernetes 官方：安全最佳实践 | https://kubernetes.io/docs/concepts/security/security-checklist/ |
| Kubernetes 官方：RBAC 最佳实践 | https://kubernetes.io/docs/concepts/security/rbac-good-practices/ |
| NSA/CISA Kubernetes 加固指南 | https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF |
| CIS Kubernetes Benchmark | https://www.cisecurity.org/benchmark/kubernetes |
