---
title: Day 22 - Prometheus 监控体系
module: M7-监控日志与排错
day: 22
updated: 2026-06-10
duration: 240 分钟
level: 进阶
prerequisites:
- M2-M3 完成
objectives:
- 安装 Prometheus Stack（kube-prometheus-stack）
- 理解 ServiceMonitor / PodMonitor
- 自定义 PrometheusRule 告警规则
- 使用 Grafana 查看预置仪表盘
- 配置 AlertManager 发送告警
tags:
- Prometheus
- Grafana
- ServiceMonitor
- AlertManager
- metrics
date: '2026-08-18'
status: published
---

# 📘 Day 22：Prometheus 监控体系

## 🎯 今日目标

- [ ] 用 Helm 部署 kube-prometheus-stack
- [ ] 理解 Prometheus 数据采集链路
- [ ] 查看集群核心指标（CPU/Memory/Network）
- [ ] 自定义告警规则

---

## 🧠 理论精讲（30 分钟）

### Prometheus Stack 架构

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Prometheus  │←──│  ServiceMon. │    │   Grafana    │
│  (采集+存储)  │    │  (动态目标)   │    │  (可视化)     │
└──────┬───────┘    └──────────────┘    └──────────────┘
       │
       ├──→ AlertManager（告警路由）
       │
       └──→ node_exporter（节点指标）
            kube-state-metrics（K8s 对象指标）
```

### 核心指标速查

| 指标 | 含义 |
|------|------|
| `container_cpu_usage_seconds_total` | CPU 累计使用 |
| `container_memory_working_set_bytes` | 内存使用量 |
| `kube_pod_status_phase` | Pod 状态 |
| `kube_deployment_status_replicas_ready` | Deploy 就绪副本 |
| `node_filesystem_avail_bytes` | 节点磁盘可用 |

---

## 🔧 动手实操（120 分钟）

### 练习 22.1：安装 kube-prometheus-stack

```bash
# 1. 添加 Helm 仓库
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 2. 安装（使用 NodePort 暴露 Grafana）
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30300 \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30900 \
  --set alertmanager.service.type=NodePort \
  --set alertmanager.service.nodePort=30903

# 3. 等待所有 Pod 就绪
kubectl get pods -n monitoring -w
# prometheus-xxx, grafana-xxx, alertmanager-xxx, operator-xxx, node-exporter-xxx, kube-state-metrics-xxx

# 4. 查看 Service
kubectl get svc -n monitoring
```

---

### 练习 22.2：访问 Prometheus 和 Grafana

```bash
# 1. 获取 Grafana 登录密码
kubectl get secret -n monitoring monitoring-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d
echo

# 2. 访问 Grafana（NodePort 30300）
echo "Grafana: http://<任意节点IP>:30300"
echo "User: admin"
echo "Password: <上面获取的密码>"

# 3. 访问 Prometheus（NodePort 30900）
echo "Prometheus: http://<任意节点IP>:30900"

# 4. 在 Prometheus 中查询一些指标：
# - up（所有目标状态）
# - kube_node_info（节点信息）
# - container_memory_usage_bytes（容器内存）
```

---

### 练习 22.3：ServiceMonitor 示例

```bash
# 1. 部署一个带 metrics 的应用
kubectl create ns app-metrics

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-app
  namespace: app-metrics
  labels:
    app: metrics-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: metrics-app
  template:
    metadata:
      labels:
        app: metrics-app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9113"
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
      - name: exporter
        image: nginx/nginx-prometheus-exporter:0.11
        args:
        - -nginx.scrape-uri=http://localhost/nginx_status
        ports:
        - containerPort: 9113
          name: metrics
EOF

kubectl expose deploy metrics-app -n app-metrics --port=9113 --name=metrics-app-svc

# 2. 创建 ServiceMonitor
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: metrics-app-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: metrics-app
  namespaceSelector:
    matchNames:
    - app-metrics
  endpoints:
  - port: metrics
    interval: 30s
EOF

# 3. 在 Prometheus Targets 中验证新目标已出现
kubectl port-forward -n monitoring svc/monitoring-prometheus 9090:9090 &
# 浏览器打开 http://localhost:9090/targets
```

---

### 练习 22.4：自定义告警规则

```bash
# 创建 PrometheusRule
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: custom-alerts
  namespace: monitoring
spec:
  groups:
  - name: pod-alerts
    rules:
    - alert: HighPodRestarts
      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ \$labels.pod }} has high restart rate"
        description: "Pod {{ \$labels.pod }} in {{ \$labels.namespace }} restarted {{ \$value }} times in 15min"
    
    - alert: PodCrashLooping
      expr: kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} > 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Pod {{ \$labels.pod }} is crash looping"
EOF

# 验证规则
kubectl get PrometheusRule -n monitoring
kubectl describe PrometheusRule custom-alerts -n monitoring
```

---

## 🐛 排错练习（30 分钟）

### 场景：Prometheus 无法采集指标

```bash
# 1. 检查 ServiceMonitor 是否创建
kubectl get servicemonitor -A

# 2. 检查 Prometheus 配置是否已加载
kubectl port-forward -n monitoring svc/monitoring-prometheus 9090:9090
# 访问 http://localhost:9090/config 查看 scrape_configs

# 3. 检查 Target 状态
# http://localhost:9090/targets

# 4. 标签是否匹配
kubectl get servicemonitor <name> -o yaml | grep -A10 selector
kubectl get svc <name> -o yaml | grep -A5 labels
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：监控体系部署与配置**

```
【操作要求】

1. 使用 Helm 部署 kube-prometheus-stack 到 monitoring 命名空间
   - Grafana NodePort 30300
   - Prometheus NodePort 30900

2. 部署示例应用：
   - Deployment demo-app（nginx:alpine，2 副本）
   - 暴露 80 和 metrics 端口

3. 配置 ServiceMonitor 采集 demo-app 的指标

4. 自定义 PrometheusRule：
   - 规则 1：Pod 重启次数 > 3（15分钟内）
   - 规则 2：Deployment 副本不达期望数超过 5 分钟

5. 在 Grafana 中：
   - 导入 Node Exporter Full 仪表盘（ID: 1860）
   - 查看集群 CPU/内存/磁盘使用情况
   - 截图保存

6. 验证：
   - Prometheus Targets 中包含 demo-app
   - 自定义告警规则生效

【评分标准】
- Prometheus Stack 部署成功（25 分）
- ServiceMonitor 正确配置（20 分）
- PrometheusRule 正确（20 分）
- Grafana 仪表盘可用（20 分）
- 整体验证（15 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl get --raw /metrics` | 查看 apiserver 指标 | 原生 Prometheus 格式，kube-state-metrics 的补充 |
| `kubectl top nodes` | 查看节点实时资源用量 | 依赖 metrics-server |
| `kubectl top pods -A --sort-by=cpu` | 按 CPU 排序 Pod 用量 | 按 `--sort-by=memory` 可改为内存排序 |
| `kubectl port-forward -n monitoring svc/prometheus-server 9090:80` | 本地访问 Prometheus UI | 无 Ingress 时的快捷方式 |
| `kubectl port-forward -n monitoring svc/grafana 3000:80` | 本地访问 Grafana | 默认账密 admin/admin |
| `kubectl -n monitoring logs -l app=prometheus --tail=50` | 查看 Prometheus 日志 | Prometheus 启动失败时首要排查 |
| `kubectl -n monitoring exec -it prometheus-<pod> -- promtool query instant http://localhost:9090 'up'` | Prometheus CLI 查询 | promtool 是 Prometheus 自带的调试工具 |
| `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts` | 添加 Prometheus Helm 仓库 | kube-prometheus-stack 包含 Prometheus+Grafana+AlertManager+NodeExporter |
| `helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace` | 一键安装监控全家桶 | Helm Chart 安装是最快捷的方式 |
| `kubectl get servicemonitor -A` | 列出 ServiceMonitor | Prometheus Operator CRD，定义采集目标 |
| `kubectl get prometheusrules -A` | 列出告警规则 | Prometheus Operator CRD |
| `kubectl get alertmanager -A` | 列出 AlertManager 实例 | Prometheus Operator CRD |
| `kubectl -n kube-system logs -l k8s-app=metrics-server --tail=20` | 查看 metrics-server 日志 | kubectl top 不可用时的排错入口 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Prometheus 官方文档 | https://prometheus.io/docs/ |
| Prometheus Operator 文档 | https://prometheus-operator.dev/ |
| kube-prometheus-stack Helm Chart | https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack |
| Grafana 官方文档 | https://grafana.com/docs/ |
| Kubernetes 官方：监控 | https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/ |
| PromQL 教程 | https://prometheus.io/docs/prometheus/latest/querying/basics/ |
