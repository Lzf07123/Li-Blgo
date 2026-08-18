---
title: Day 12 - ConfigMap 与 Secret
module: M4-存储与配置管理
day: 12
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- M2 完成，理解 Pod 和 Deployment
objectives:
- 掌握 ConfigMap 的 4 种创建方式
- 掌握 ConfigMap 的 3 种使用方式
- 掌握 Secret 的创建与管理
- 理解 ConfigMap 热更新机制
- 区分 Opaque/kubernetes.io/tls/kubernetes.io/dockerconfigjson 三种 Secret
tags:
- ConfigMap
- Secret
- 配置管理
- 热更新
- immutable
date: '2026-08-18'
status: published
---

# 📘 Day 12：ConfigMap 与 Secret

## 🎯 今日目标

- [ ] 会用 4 种方式创建 ConfigMap
- [ ] 会用 envFrom、valueFrom、volume 三种方式消费配置
- [ ] 能创建 Opaque、TLS、dockerconfigjson 三种 Secret
- [ ] 理解 ConfigMap 挂载为 Volume 时的热更新
- [ ] 掌握 immutable ConfigMap/Secret

---

## 🧠 理论精讲（30 分钟）

### ConfigMap vs Secret

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 用途 | 非敏感配置 | 敏感数据（密码、证书） |
| 存储 | 明文（etcd 中） | Base64 编码（可配合加密） |
| 大小限制 | 1 MiB | 1 MiB |
| 热更新 | ✅（Volume 挂载模式） | ✅（Volume 挂载模式） |

### 消费配置的三种方式

```
1. envFrom    — 整个 ConfigMap/Secret 作为环境变量
2. valueFrom  — 从 ConfigMap/Secret 读取单个 key 作为环境变量
3. volume     — 将 ConfigMap/Secret 挂载为文件
```

### Secret 类型

| 类型 | 用途 | 数据 key 要求 |
|------|------|--------------|
| **Opaque** | 通用密钥（默认） | 任意 |
| **kubernetes.io/tls** | TLS 证书 | `tls.crt`、`tls.key` |
| **kubernetes.io/dockerconfigjson** | 镜像拉取凭证 | `.dockerconfigjson` |
| **kubernetes.io/basic-auth** | 基础认证 | `username`、`password` |

---

## 🔧 动手实操（120 分钟）

### 练习 12.1：ConfigMap 四种创建方式

```bash
# 方式 1：--from-literal（字面值）
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=APP_DEBUG=false \
  --from-literal=LOG_LEVEL=info

# 查看内容
kubectl get cm app-config -o yaml

# 方式 2：--from-file（从文件）
mkdir -p /tmp/cm-demo
cat > /tmp/cm-demo/nginx.conf <<EOF
server {
    listen 80;
    server_name localhost;
}
EOF
cat > /tmp/cm-demo/app.properties <<EOF
app.name=myapp
app.version=1.0.0
EOF

kubectl create configmap file-config --from-file=/tmp/cm-demo/

# 查看
kubectl describe cm file-config
# 两个 key：nginx.conf 和 app.properties

# 方式 3：--from-file 指定 key 名
kubectl create configmap nginx-conf --from-file=nginx.conf=/tmp/cm-demo/nginx.conf

# 方式 4：--from-env-file（从环境变量文件）
cat > /tmp/cm-demo/env.list <<EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
EOF

kubectl create configmap db-env --from-env-file=/tmp/cm-demo/env.list

# 查看所有
kubectl get cm
```

---

### 练习 12.2：ConfigMap 三种使用方式

```bash
# === 方式 1：envFrom（整批注入） ===
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: cm-envfrom
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "echo DB_HOST=\$DB_HOST DB_PORT=\$DB_PORT; sleep 3600"]
    envFrom:
    - configMapRef:
        name: db-env
EOF

kubectl logs cm-envfrom
# 输出：DB_HOST=localhost DB_PORT=5432

# === 方式 2：valueFrom（单个引用） ===
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: cm-valuefrom
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "echo ENV=\$APP_ENV DEBUG=\$APP_DEBUG; sleep 3600"]
    env:
    - name: APP_ENV
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: APP_ENV
    - name: APP_DEBUG
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: APP_DEBUG
EOF

kubectl logs cm-valuefrom
# 输出：ENV=production DEBUG=false

# === 方式 3：Volume 挂载（文件方式） ===
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: cm-volume
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "cat /etc/config/nginx.conf; sleep 3600"]
    volumeMounts:
    - name: config
      mountPath: /etc/config
  volumes:
  - name: config
    configMap:
      name: nginx-conf
EOF

kubectl logs cm-volume
# 输出 nginx.conf 内容

# 查看挂载的文件
kubectl exec cm-volume -- ls -la /etc/config/
kubectl exec cm-volume -- cat /etc/config/nginx.conf

# 清理
kubectl delete pod cm-envfrom cm-valuefrom cm-volume
```

---

### 练习 12.3：ConfigMap 热更新验证

```bash
# 1. 创建 ConfigMap 并以 Volume 方式挂载
kubectl create configmap dynamic-config --from-literal=message="version-1"

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hot-reload
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "while true; do cat /etc/config/message; sleep 2; done"]
    volumeMounts:
    - name: cfg
      mountPath: /etc/config
  volumes:
  - name: cfg
    configMap:
      name: dynamic-config
EOF

# 2. 观察当前值
kubectl logs hot-reload --tail=5
# 输出：version-1

# 3. 更新 ConfigMap
kubectl create configmap dynamic-config --from-literal=message="version-2" \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. 等待约 60-90 秒后查看（kubelet 同步周期）
sleep 60
kubectl logs hot-reload --tail=5
# 输出变为：version-2

# ⚠️ 注意：
# - Volume 挂载方式：热更新生效（有延迟，约 60-90 秒）
# - envFrom/valueFrom 方式：不会热更新！需要重建 Pod

# 5. 清理
kubectl delete pod hot-reload
kubectl delete cm dynamic-config
```

---

### 练习 12.4：Secret 实战

```bash
# 1. 创建 Opaque Secret
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password='P@ssw0rd!2024'

kubectl get secret db-credentials
kubectl describe secret db-credentials
# 不显示值，只显示 key 名

# 查看解码内容
kubectl get secret db-credentials -o jsonpath='{.data.password}' | base64 -d
echo

# 2. 在 Pod 中使用
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "echo USER=\$DB_USER PASS=\$DB_PASS; sleep 3600"]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASS
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
EOF

kubectl logs secret-demo
# 输出：USER=admin PASS=P@ssw0rd!2024

# 3. 创建 TLS Secret
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /tmp/tls.key -out /tmp/tls.crt \
  -subj "/CN=myapp.example.com"

kubectl create secret tls my-tls \
  --key=/tmp/tls.key --cert=/tmp/tls.crt

kubectl describe secret my-tls
# Type: kubernetes.io/tls

# 4. 创建镜像拉取 Secret
kubectl create secret docker-registry my-registry \
  --docker-server=registry.example.com \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=my@example.com

kubectl describe secret my-registry
# Type: kubernetes.io/dockerconfigjson

# 5. 清理
kubectl delete pod secret-demo
kubectl delete secret db-credentials my-tls my-registry
rm -f /tmp/tls.key /tmp/tls.crt
```

---

### 练习 12.5：Immutable ConfigMap/Secret

```bash
# 不可变（immutable）的 ConfigMap 不能修改，只能删除重建
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: immutable-cm
immutable: true
data:
  version: "1.0"
  build-time: "$(date)"
EOF

# 尝试修改会报错
kubectl patch cm immutable-cm -p '{"data":{"version":"2.0"}}'
# Error: ConfigMap is immutable

# 清理
kubectl delete cm immutable-cm
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：ConfigMap 未更新

```bash
# 问题：修改了 ConfigMap，但应用没有变化

# 排查：
# 1. 确认是哪种消费方式
kubectl get pod <pod> -o yaml | grep -A5 envFrom
# envFrom → 需要重建 Pod
# volume → 等待 kubelet 同步（~90s）

# 2. 如果是 envFrom，强制重建
kubectl rollout restart deploy/<name>

# 3. 如果是 volume，检查挂载点内容
kubectl exec <pod> -- cat <mount-path>/<key>
```

### 场景 2：Secret 未正确解码

```bash
# 问题：Pod 中的环境变量显示乱码或空值

# 排查：
kubectl get secret <name> -o jsonpath='{.data.<key>}' | base64 -d
# 如果解码后为空：创建 Secret 时输入有误
# 如果解码失败：不是合法的 base64（--from-literal 会自动编码）
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **35 分钟**

**题目：应用配置管理综合**

```
【操作要求】

1. 创建 ConfigMap app-settings：
   - APP_ENV=staging
   - APP_LOG_LEVEL=debug
   - APP_MAX_CONNECTIONS=100

2. 创建 Secret app-secrets：
   - DB_PASSWORD=secret123
   - API_KEY=sk-abcdef123456
   - REDIS_PASSWORD=redispass

3. 创建 Deployment config-app（2 副本，nginx:alpine）：
   - 用 envFrom 注入 app-settings 的所有键
   - 用 valueFrom 注入 DB_PASSWORD（命名为 DATABASE_PASSWORD）
   - 将 app-settings 以 Volume 方式挂载到 /etc/app/config

4. 创建 TLS Secret app-tls（自签名证书，CN=secure.app.com）

5. 更新 app-settings 中的 APP_LOG_LEVEL=info，
   验证 Volume 挂载的配置文件是否更新

6. 验证：
   - kubectl exec 进入 Pod 查看环境变量
   - 确认 /etc/app/config 下有配置文件的符号链接
   - 确认 Secret 数据可正常读取

【评分标准】
- ConfigMap 创建正确（15 分）
- Secret 创建正确（15 分）
- Deployment 配置注入正确（35 分）
- TLS Secret 正确（10 分）
- 热更新验证（15 分）
- Immutable 属性（10 分）
```

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get cm` | 列出 ConfigMap | short name: cm |
| `kubectl get cm <name> -o yaml` | 查看 ConfigMap 完整内容 | 检查所有 key-value 数据 |
| `kubectl create cm <name> --from-file=<file>` | 从文件创建 ConfigMap | key 为文件名，value 为文件内容 |
| `kubectl create cm <name> --from-file=key=<file>` | 从文件创建并指定 key | key 可以不同于文件名 |
| `kubectl create cm <name> --from-literal=key=value` | 从字面值创建 ConfigMap | 快速创建简单配置项，多个 `--from-literal` 可合并 |
| `kubectl create cm <name> --from-env-file=<file>` | 从 .env 文件创建 ConfigMap | 每行 KEY=VALUE 格式 |
| `kubectl get secret` | 列出 Secret | 默认只显示名称和类型（不显示值） |
| `kubectl get secret <name> -o yaml` | 查看 Secret 完整 YAML | data 字段为 base64 编码 |
| `kubectl get secret <name> -o jsonpath='{.data.<key>}' \| base64 -d` | 解码 Secret 某个 key | jsonpath 提取 + base64 解码，常用组合 |
| `kubectl get secret <name> -o jsonpath='{.data}' \| jq 'map_values(@base64d)'` | 解码所有 Secret 字段 | jq 一次性解码所有 base64 值 |
| `kubectl create secret generic <name> --from-literal=key=value` | 创建 Opaque Secret | 值自动 base64 编码存储（注意：仅仅是编码非加密） |
| `kubectl create secret generic <name> --from-file=<file>` | 从文件创建 Secret | 文件内容自动 base64 |
| `kubectl create secret docker-registry <name> --docker-server=<url> --docker-username=<user> --docker-password=<pass>` | 创建镜像拉取密钥 | 私有镜像仓库认证 |
| `kubectl create secret tls <name> --cert=cert.pem --key=key.pem` | 创建 TLS Secret | Ingress HTTPS 专用 |
| `kubectl describe cm <name>` | ConfigMap 概要 | 显示 key 列表但不显示 value |
| `kubectl edit cm <name>` | 在线编辑 ConfigMap | 立即生效，挂载到 Pod 中的文件会延迟更新（取决于 kubelet 同步周期） |
| `kubectl set env deploy/<name> --from=cm/<cm-name>` | 将 ConfigMap 注入为环境变量 | 更新 Deployment 环境变量，触发滚动更新 |
| `echo -n "secret-value" \| base64` | base64 编码 | 手动编码 Secret 值，填入 YAML 中的 data 字段 |
| `kubectl exec <pod> -- cat /etc/config/<key>` | 验证 ConfigMap 挂载内容 | 确认文件内容和路径是否正确 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：ConfigMap | https://kubernetes.io/docs/concepts/configuration/configmap/ |
| Kubernetes 官方：Secret | https://kubernetes.io/docs/concepts/configuration/secret/ |
| Kubernetes 官方：配置 Pod 使用 ConfigMap | https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/ |
| Kubernetes 官方：Secret 管理最佳实践 | https://kubernetes.io/docs/concepts/configuration/secret/#best-practices |
| Kubernetes 官方：不可变 ConfigMap 与 Secret | https://kubernetes.io/docs/concepts/configuration/configmap/#configmap-immutable |
