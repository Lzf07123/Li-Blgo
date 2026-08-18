---
title: Day 20 - ServiceAccount、镜像安全与 Pod Security
module: M6-安全与认证
day: 20
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- Day 19 完成，理解 RBAC
objectives:
- 理解 ServiceAccount 的自动挂载与禁用
- 掌握 imagePullSecrets
- 掌握 SecurityContext 配置
- 理解 PodSecurityStandard（PSS）
- 配置私有镜像仓库拉取
tags:
- ServiceAccount
- imagePullSecrets
- SecurityContext
- PSS
- 私有镜像
date: '2026-08-18'
status: published
---

# 📘 Day 20：ServiceAccount、镜像安全与 Pod Security

## 🎯 今日目标

- [ ] 理解 Pod 默认挂载 SA Token 的含义
- [ ] 能用 imagePullSecrets 拉取私有镜像
- [ ] 能用 SecurityContext 控制容器权限
- [ ] 理解 privileged/restricted/baseline 三个级别

---

## 🧠 理论精讲（30 分钟）

### ServiceAccount 自动挂载

```yaml
# 每个 Pod 默认会自动挂载 SA Token：
# /var/run/secrets/kubernetes.io/serviceaccount/token
# /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
# /var/run/secrets/kubernetes.io/serviceaccount/namespace

# 可通过以下方式禁用：
spec:
  automountServiceAccountToken: false
```

### SecurityContext 可控制的内容

| 配置 | 说明 |
|------|------|
| `runAsUser` / `runAsGroup` | 指定容器运行用户 |
| `runAsNonRoot` | 强制非 root 运行 |
| `privileged` | 特权模式（尽量不用） |
| `allowPrivilegeEscalation` | 是否允许提权 |
| `readOnlyRootFilesystem` | 根文件系统只读 |
| `capabilities` | Linux Capabilities 管理 |

### Pod Security Standards（PSS）

| 级别 | 说明 | 适用场景 |
|------|------|---------|
| **Privileged** | 无限制 | 系统组件 |
| **Baseline** | 禁止已知风险（hostPath、特权） | 普通应用 |
| **Restricted** | 严格限制（非 root、只读根文件系统） | 安全要求高 |

---

## 🔧 动手实操（120 分钟）

### 练习 20.1：ServiceAccount 与 Token 管理

```bash
# 1. 查看 Pod 默认挂载的 SA Token
kubectl run sa-test --image=busybox:1.36 --restart=Never -- sleep 3600

kubectl exec sa-test -- ls /var/run/secrets/kubernetes.io/serviceaccount/
# ca.crt  namespace  token

kubectl exec sa-test -- cat /var/run/secrets/kubernetes.io/serviceaccount/token | head -3

# 2. 禁用自动挂载
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: no-sa-mount
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
EOF

kubectl exec no-sa-mount -- ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>&1
# ls: /var/run/secrets/kubernetes.io/serviceaccount/: No such file or directory

# 3. 创建自定义 SA
kubectl create sa custom-sa
kubectl run custom-sa-pod --image=busybox:1.36 --restart=Never --overrides='
{
  "spec": {
    "serviceAccountName": "custom-sa"
  }
}' -- sleep 3600

kubectl get pod custom-sa-pod -o jsonpath='{.spec.serviceAccountName}'
# custom-sa

# 清理
kubectl delete pod sa-test no-sa-mount custom-sa-pod
kubectl delete sa custom-sa
```

---

### 练习 20.2：SecurityContext 安全上下文

```bash
# 1. 非 root 用户运行
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: non-root-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: app
    image: nginx:alpine
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false
EOF

# 验证用户
kubectl exec non-root-pod -- id
# uid=1000 gid=3000

# 2. 设置 ReadOnlyRootFilesystem
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: readonly-pod
spec:
  containers:
  - name: app
    image: nginx:alpine
    securityContext:
      readOnlyRootFilesystem: true
    volumeMounts:
    - name: nginx-run
      mountPath: /var/run
    - name: nginx-cache
      mountPath: /var/cache/nginx
  volumes:
  - name: nginx-run
    emptyDir: {}
  - name: nginx-cache
    emptyDir: {}
EOF

kubectl exec readonly-pod -- touch /test-file
# touch: /test-file: Read-only file system

# 3. Capabilities 管理
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: caps-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    securityContext:
      capabilities:
        drop:
        - ALL
        add:
        - NET_BIND_SERVICE
        - CHOWN
EOF

# 清理
kubectl delete pod non-root-pod readonly-pod caps-pod
```

---

### 练习 20.3：私有镜像仓库拉取

```bash
# 1. 创建 Docker Registry Secret
kubectl create secret docker-registry private-registry \
  --docker-server=registry.cn-hangzhou.aliyuncs.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your@email.com

# 2. 方式一：在 Pod 中指定
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: private-image-pod
spec:
  imagePullSecrets:
  - name: private-registry
  containers:
  - name: app
    image: registry.cn-hangzhou.aliyuncs.com/your-ns/your-image:tag
EOF

# 3. 方式二：绑定到 ServiceAccount（推荐）
kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"private-registry"}]}'

# 验证
kubectl get sa default -o yaml | grep -A3 imagePullSecrets

# 4. 清理
kubectl delete pod private-image-pod
kubectl delete secret private-registry
# 恢复默认 SA
kubectl patch serviceaccount default --type=json \
  -p='[{"op":"remove","path":"/imagePullSecrets"}]'
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：镜像拉取失败（ErrImagePull / ImagePullBackOff）

```bash
# 排查步骤
# 1. 查看错误详情
kubectl describe pod <pod-name> | grep -A10 Events

# 2. 是否是私有镜像？
# → 检查是否配置了 imagePullSecrets

# 3. Secret 是否正确？
kubectl get secret <secret-name> -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | python3 -m json.tool

# 4. 镜像名是否正确？
# registry/namespace/image:tag
```

### 场景 2：Pod 启动后立即退出（Permission Denied）

```bash
# 可能是因为 SecurityContext 限制了权限
kubectl logs <pod-name>
# Permission denied

# 检查 SecurityContext
kubectl get pod <pod-name> -o yaml | grep -A15 securityContext
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：Pod 安全加固**

```
【操作要求】

1. 创建命名空间 secure-workspace

2. 创建 ServiceAccount secure-runner：
   - 禁用默认 Token 自动挂载

3. 创建私有仓库 Secret（模拟）：
   - Server: registry.internal.com
   - Username: ci-bot
   - Password: ci-token-123
   - 将此 Secret 绑定到 secure-runner SA

4. 创建 Deployment secure-app（2副本，nginx:alpine）：
   - 使用 secure-runner SA
   - SecurityContext:
     * runAsUser: 1001
     * runAsNonRoot: true
     * allowPrivilegeEscalation: false
     * readOnlyRootFilesystem: false（nginx 需要写临时文件）
     * drop ALL capabilities
   - 定义 resources.requests 和 limits
   - livenessProbe + readinessProbe

5. 验证：
   - SA 没有自动挂载 Token
   - 容器以 uid 1001 运行
   - 容器不能以 root 运行

【评分标准】
- SA 配置正确（15 分）
- 私有仓库 Secret + 绑定（20 分）
- SecurityContext 配置（35 分）
- 探针配置（15 分）
- 安全验证（15 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get sa -A` | 列出所有 ServiceAccount | 每个 NS 有默认 default SA |
| `kubectl describe sa <name> -n <ns>` | SA 详情 | 查看关联的 Secrets 和镜像拉取密钥 |
| `kubectl create sa <name> -n <ns>` | 创建 ServiceAccount | SA 创建后需绑定 Role 才有权限 |
| `kubectl create token <sa> -n <ns>` | 生成 SA 临时 Token（1.24+） | 有时效性，用于外部访问 apiserver |
| `kubectl create token <sa> -n <ns> --duration=1h` | 指定 Token 有效期 | 默认 1h，最长 48h |
| `kubectl get pod <pod> -o jsonpath='{.spec.serviceAccountName}'` | 查看 Pod 使用的 SA | 默认使用 default SA |
| `kubectl get podsecurity` | 查看 Pod Security Admission 配置 | 1.25+ 替代 PSP，三个等级：privileged/baseline/restricted |
| `kubectl label ns <ns> pod-security.kubernetes.io/enforce=restricted` | 设置命名空间安全等级 | restricted 最严格，禁止特权容器、hostPath 等 |
| `kubectl label ns <ns> pod-security.kubernetes.io/warn=baseline` | 设置安全警告等级 | 仅警告不拒绝 |
| `kubectl get secret \| grep <sa>-docker` | 查找镜像拉取密钥 | 私有仓库认证 |
| `kubectl create secret docker-registry <name> --docker-server=<url> --docker-username=<user> --docker-password=<pass>` | 创建镜像拉取密钥 | 在 Pod spec 中通过 imagePullSecrets 引用 |
| `kubectl patch sa default -n <ns> -p '{"imagePullSecrets":[{"name":"<secret>"}]}'` | 给默认 SA 添加镜像拉取密钥 | 该 NS 所有使用 default SA 的 Pod 自动携带 |
| `kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].image}{"\n"}{end}'` | 列出所有 Pod 的镜像 | 审计镜像版本 |
| `kubectl set image deploy/<name> <container>=<image>@sha256:<digest>` | 使用镜像摘要更新 | 比 tag 更安全，防止标签篡改 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：ServiceAccount | https://kubernetes.io/docs/concepts/security/service-accounts/ |
| Kubernetes 官方：Pod Security Admission | https://kubernetes.io/docs/concepts/security/pod-security-admission/ |
| Kubernetes 官方：Pod 安全标准 | https://kubernetes.io/docs/concepts/security/pod-security-standards/ |
| Kubernetes 官方：镜像拉取密钥 | https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/ |
| Kubernetes 官方：镜像安全最佳实践 | https://kubernetes.io/docs/concepts/security/ |
