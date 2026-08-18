---
title: Day 09 - Ingress 与外部流量接入
module: M3-网络与服务发现
day: 9
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 08 完成，理解 Service
objectives:
- 理解 Ingress 与 Service 的关系
- 安装 Ingress Controller（NGINX）
- 掌握 Ingress 路由规则配置
- 实现基于路径和基于域名的路由
- 配置 TLS 终止
tags:
- Ingress
- Ingress Controller
- NGINX Ingress
- TLS
- 域名路由
date: '2026-08-18'
status: published
---

# 📘 Day 09：Ingress 与外部流量接入

## 🎯 今日目标

- [ ] 理解 Ingress 不是 Service 的替代，而是 L7 路由层
- [ ] 安装并配置 NGINX Ingress Controller
- [ ] 创建基于路径的路由规则
- [ ] 创建基于域名的路由规则
- [ ] 配置 TLS 证书实现 HTTPS

---

## 🧠 理论精讲（30 分钟）

### Ingress 是什么

```
                         ┌──────────────┐
                         │   Ingress    │  ← L7 路由规则
                         │  Controller  │
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
         /api ──→ api-svc    /web ──→ web-svc   / ──→ frontend-svc
              (ClusterIP)        (ClusterIP)        (ClusterIP)
```

Ingress 提供 **HTTP/HTTPS 路由**、**SSL 终止**、**基于名称的虚拟托管**。

### Ingress vs Service

| 特性 | Service (NodePort/LB) | Ingress |
|------|----------------------|---------|
| 工作层级 | L4 (TCP/UDP) | L7 (HTTP/HTTPS) |
| 路由能力 | 端口映射 | 路径/域名路由 |
| SSL | 需手动配置 | 内置 TLS 终止 |
| 外部入口 | 每 Service 一个 | 统一入口 |

### Ingress Controller 选择

| Controller | 特点 |
|------------|------|
| **NGINX Ingress** | 最常用，功能全面 |
| **Traefik** | 自动发现，适合微服务 |
| **Istio Gateway** | 服务网格场景 |
| **Contour/Envoy** | 高性能 |

---

## 🔧 动手实操（120 分钟）

### 练习 9.1：安装 NGINX Ingress Controller

```bash
# 方式 1：使用 Helm（推荐）
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=30080 \
  --set controller.service.nodePorts.https=30443

# 方式 2：使用 kubectl apply（如果没装 Helm）
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml

# 验证安装
kubectl get pods -n ingress-nginx
# ingress-nginx-controller-xxx  Running

kubectl get svc -n ingress-nginx
# ingress-nginx-controller  NodePort/LoadBalancer

# 验证 Controller 可访问
# 获取 NodePort 端口
kubectl get svc -n ingress-nginx ingress-nginx-controller

# 测试 404 页面（还没有 Ingress 规则）
curl http://<节点IP>:30080
# 返回 404（正常，还没有配置后端）
```

---

### 练习 9.2：基于路径的路由

```bash
# 1. 创建两个后端应用
kubectl create deploy app-v1 --image=nginx:alpine
kubectl expose deploy app-v1 --port=80

kubectl create deploy app-v2 --image=httpd:alpine
kubectl expose deploy app-v2 --port=80

# 2. 创建 Ingress 规则
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: app-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: app-v2
            port:
              number: 80
EOF

# 3. 查看 Ingress
kubectl get ingress path-ingress
# NAME           CLASS   HOSTS   ADDRESS       PORTS   AGE
# path-ingress   nginx   *       <IP>         80      10s

kubectl describe ingress path-ingress

# 4. 测试路由
curl http://<节点IP>:30080/v1
# 返回 nginx 默认页面

curl http://<节点IP>:30080/v2
# 返回 httpd 的 "It works!" 页面

# 5. 清理
kubectl delete ingress path-ingress
kubectl delete deploy app-v1 app-v2
kubectl delete svc app-v1 app-v2
```

---

### 练习 9.3：基于域名的路由

```bash
# 1. 创建两个后端服务
kubectl create deploy web-a --image=nginx:alpine
kubectl expose deploy web-a --port=80
kubectl create deploy web-b --image=httpd:alpine
kubectl expose deploy web-b --port=80

# 2. 创建域名 Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: host-ingress
spec:
  ingressClassName: nginx
  rules:
  - host: app-a.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-a
            port:
              number: 80
  - host: app-b.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-b
            port:
              number: 80
EOF

# 3. 测试域名路由（通过 Host 头）
curl -H "Host: app-a.example.com" http://<节点IP>:30080/
# 返回 nginx 页面

curl -H "Host: app-b.example.com" http://<节点IP>:30080/
# 返回 httpd 页面

# 4. 清理
kubectl delete ingress host-ingress
kubectl delete deploy web-a web-b
kubectl delete svc web-a web-b
```

---

### 练习 9.4：Ingress TLS 配置

```bash
# 1. 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=tls-demo.example.com/O=tls-demo"

# 2. 创建 TLS Secret
kubectl create secret tls demo-tls --key=tls.key --cert=tls.crt

# 3. 创建后端服务
kubectl create deploy secure-app --image=nginx:alpine
kubectl expose deploy secure-app --port=80

# 4. 创建 TLS Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - tls-demo.example.com
    secretName: demo-tls
  rules:
  - host: tls-demo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secure-app
            port:
              number: 80
EOF

# 5. 测试 HTTPS 访问（-k 跳过证书验证）
# 先获取 HTTPS NodePort
kubectl get svc -n ingress-nginx ingress-nginx-controller

curl -k -H "Host: tls-demo.example.com" https://<节点IP>:30443/
# 返回 nginx 页面

# 6. 查看证书信息
echo | openssl s_client -connect <节点IP>:30443 -servername tls-demo.example.com 2>/dev/null | openssl x509 -noout -subject -dates

# 7. 清理
rm -f tls.key tls.crt
kubectl delete ingress tls-ingress
kubectl delete secret demo-tls
kubectl delete deploy secure-app
kubectl delete svc secure-app
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：Ingress 返回 404

```bash
# 排查步骤
# 1. 确认 Ingress Controller 是否运行
kubectl get pods -n ingress-nginx

# 2. 确认 Ingress 资源创建成功
kubectl get ingress

# 3. 检查 Ingress 详情
kubectl describe ingress <name>
# 看 Rules 和 Backend 是否正确

# 4. 确认后端 Service 存在且有 Endpoint
kubectl get svc <svc-name>
kubectl get endpoints <svc-name>

# 5. 检查 ingressClassName
kubectl get ingress <name> -o yaml | grep ingressClassName
# 应为 nginx（或与 Controller 类型一致）

# 6. 查看 Ingress Controller 日志
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=50
```

### 场景 2：TLS 证书不生效

```bash
# 排查步骤
# 1. 检查 Secret 是否存在且类型正确
kubectl get secret <secret-name>
kubectl describe secret <secret-name>
# 应有 tls.crt 和 tls.key

# 2. 检查证书内容
kubectl get secret <secret-name> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout | head -20

# 3. 检查 Ingress tls 段
kubectl get ingress <name> -o yaml | grep -A5 tls
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：统一网关配置**

```
【环境要求】
- NGINX Ingress Controller 已安装（NodePort 30080/30443）

【操作要求】

1. 创建 3 个后端应用：
   - api（nginx:alpine，2 副本，ClusterIP Service api-svc）
   - web（httpd:alpine，2 副本，ClusterIP Service web-svc）
   - admin（nginx:alpine，1 副本，ClusterIP Service admin-svc）

2. 创建 Ingress 规则：
   a. 路径路由：
      - /api → api-svc
      - /    → web-svc
   b. 域名路由（新增第二个 Ingress 或合并）：
      - admin.example.com → admin-svc

3. 配置注解：
   - nginx.ingress.kubernetes.io/rewrite-target: /
   - 为 api 路径配置 CORS 允许所有来源

4. 为 admin.example.com 配置自签名 TLS

5. 验证：
   - curl <NodeIP>:30080/api → 返回 nginx
   - curl <NodeIP>:30080/ → 返回 httpd
   - curl -H "Host: admin.example.com" <NodeIP>:30080/ → 返回 nginx
   - curl -k -H "Host: admin.example.com" https://<NodeIP>:30443/ → 返回 nginx

【评分标准】
- 后端服务创建（20 分）
- 路径路由正确（25 分）
- 域名路由正确（20 分）
- TLS 配置正确（25 分）
- 验证全部通过（10 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get ingress` | 列出 Ingress | ADDRESS 为空说明 Ingress Controller 未就绪 |
| `kubectl get ingress -o wide` | Ingress + 主机/地址 | 查看 Host 规则和分配的 ADDRESS |
| `kubectl describe ingress <name>` | Ingress 详细规则 | 查看每条 Path 规则和后端 Service |
| `kubectl get ingressclass` | 列出 IngressClass | 多个 Ingress Controller 时用于区分 |
| `kubectl -n ingress-nginx get pods` | 查看 Ingress Controller Pod | nginx-ingress 默认部署在 ingress-nginx 命名空间 |
| `kubectl -n ingress-nginx logs -l app.kubernetes.io/name=ingress-nginx` | 查看 Ingress Controller 日志 | Ingress 路由异常时的首要排查 |
| `kubectl -n ingress-nginx get svc` | 查看 Ingress Controller Service | 确认是否分配了 EXTERNAL-IP |
| `curl -H "Host: <hostname>" http://<node-ip>:<nodeport>` | 测试 Ingress 路由 | 绕过 DNS 直接用 Header 指定 Host |
| `curl -k https://<hostname>` | 测试 HTTPS Ingress | `-k` 跳过自签名证书验证 |
| `kubectl create ingress <name> --rule="host/path=svc:port" --dry-run=client -o yaml` | 生成 Ingress YAML | 快速生成基本的 Ingress 规则模板 |
| `kubectl get svc -A \| grep LoadBalancer` | 查找所有 LB 类型 Service | 云环境中 LB 会分配公网 IP |
| `kubectl patch ingress <name> -p '{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/rewrite-target":"/"}}}}'` | 添加 Ingress 注解 | nginx-ingress rewrite 注解实现 URL 重写 |
| `kubectl create secret tls <name> --cert=cert.pem --key=key.pem` | 创建 TLS Secret | Ingress HTTPS 必须用此类型 Secret |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：Ingress | https://kubernetes.io/docs/concepts/services-networking/ingress/ |
| Kubernetes 官方：Ingress Controller | https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/ |
| NGINX Ingress Controller 文档 | https://kubernetes.github.io/ingress-nginx/ |
| NGINX Ingress 注解参考 | https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/ |
| Kubernetes 官方：TLS/SSL | https://kubernetes.io/docs/concepts/services-networking/ingress/#tls |
