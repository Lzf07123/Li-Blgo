---
title: Day 30 - 全真模拟考试
module: M8-综合实战与赛题模拟
day: 30
updated: 2026-06-10
duration: 240 分钟
level: 冲刺
prerequisites:
- 30 天学习计划全部完成
objectives:
- 在模拟比赛环境中完成全真考试
- 检验 30 天学习成果
- 制定赛后提升计划
tags:
- 全真模拟
- 期末考试
- 成果检验
date: '2026-08-18'
status: published
---

# 📘 Day 30：全真模拟考试

## 🎯 今日目标

在严格限时的模拟比赛环境中，完成一套完整试卷，检验 30 天学习成果。

---

## 📋 考试规则

| 项目 | 要求 |
|------|------|
| **考试时长** | 180 分钟（3 小时） |
| **总分** | 100 分 |
| **及格线** | 60 分 |
| **优秀线** | 85 分 |
| **环境** | 3 节点 K8s 集群（已就绪） |
| **允许参考** | 个人速查手册（不允许联网搜索） |
| **提交物** | 所有 YAML 文件 + 验证命令输出 |

---

## 📝 全真模拟试卷

### 第一部分：集群运维（15 分，25 分钟）

**题目 1.1（5 分）**

```bash
# 检查集群健康状态，输出以下信息：
# - 所有节点状态和版本
# - 所有命名空间中非 Running 的 Pod
# - 证书到期时间
# - 最近 10 条 Warning 事件
```

**题目 1.2（5 分）**

```bash
# 对 etcd 做一次快照备份，验证快照完整性
# 将备份文件存放到 /opt/etcd-backup/exam-$(date +%Y%m%d).db
```

**题目 1.3（5 分）**

```bash
# 现有节点 k8s-node1 需要维护，执行：
# - cordon 使其不再调度新 Pod
# - drain 排空已有 Pod
# - 维护完成后 uncordon 恢复
```

---

### 第二部分：工作负载编排（25 分，45 分钟）

**题目 2.1：StatefulSet 数据库集群（10 分）**

```
部署一个 redis 集群：
- 名称：redis-cluster
- 副本数：3
- 镜像：redis:7-alpine
- 启动命令：redis-server --appendonly yes --cluster-enabled yes
- Headless Service：redis-cluster-svc（端口 6379）
- 每个 Pod 独立 PVC：200Mi
- 限制资源：cpu 200m, memory 256Mi
```

**题目 2.2：Deployment 应用层（10 分）**

```
部署一个 API 服务：
- 名称：api-gateway
- 镜像：nginx:alpine
- 副本数：4
- 滚动策略：maxSurge=1, maxUnavailable=0
- livenessProbe: HTTP GET /health, 端口 80
- readinessProbe: HTTP GET /ready, 端口 80
- 资源：requests cpu=100m mem=128Mi, limits cpu=300m mem=256Mi
- Service：ClusterIP，端口 80
```

**题目 2.3：DaemonSet + CronJob（5 分）**

```
- DaemonSet node-monitor：busybox:1.36，每 10 秒输出主机名和时间
- CronJob cluster-health：每 5 分钟检查一次 DNS 解析，
  命令：nslookup kubernetes.default
  保留最近 3 个成功的 Job
```

---

### 第三部分：网络配置（20 分，35 分钟）

**题目 3.1：Ingress 路由（10 分）**

```
创建 Ingress 规则，路由到题 2.2 的 api-gateway：
- 域名：api.exam.com
- /v1/stats → api-gateway:80/stats
- /v1/health → api-gateway:80/health
- 配置 rewrite-target 注解
```

**题目 3.2：NetworkPolicy 网络隔离（10 分）**

```
在 exam 命名空间中创建网络策略：
- 默认拒绝所有入站流量
- 允许 Ingress Controller → api-gateway:80
- 允许 api-gateway → redis-cluster:6379
- 允许所有 Pod → CoreDNS（kube-system, UDP 53）
- 验证：从 api-gateway 可访问 redis，从外部 Pod 不可访问
```

---

### 第四部分：存储与配置（20 分，35 分钟）

**题目 4.1：配置管理（8 分）**

```
- ConfigMap api-config：
  LOG_LEVEL=info, MAX_CONNECTIONS=500, TIMEOUT=30s
- Secret api-secret：
  DB_PASSWORD=exam-secret-2024, JWT_KEY=jwt-key-exam
- 修改 Deployment api-gateway：
  envFrom 注入 api-config
  valueFrom 注入 DB_PASSWORD → DATABASE_PASSWORD
```

**题目 4.2：持久存储（12 分）**

```
- 创建 hostPath PV pv-exam（容器 2Gi, RWO, /data/exam-pv）
- 创建 PVC pvc-exam（请求 1Gi, RWO）
- 验证 PV 和 PVC 绑定
- 创建一个 Pod exam-storage 挂载 pvc-exam 到 /data：
  写入验证文件 /data/exam.txt
  删除 Pod 后验证文件仍存在
```

---

### 第五部分：安全与调度（20 分，40 分钟）

**题目 5.1：RBAC（10 分）**

```
创建以下权限体系：
- SA exam-admin：对 exam 命名空间全部权限
- SA exam-developer：对 Pod/Deploy/Service/ConfigMap
  有 get/list/watch/create/update 权限
  对 Secret 和 Pod/log 只有 get/list 权限
- SA exam-viewer：只读所有（get/list/watch）

每个 SA 创建对应的 Role + RoleBinding
验证：kubectl auth can-i --as=... 测试权限差异
```

**题目 5.2：安全与调度（10 分）**

```
修改 Deployment api-gateway 添加：
- SecurityContext:
  runAsUser: 1001, runAsNonRoot: true
  allowPrivilegeEscalation: false
  drop ALL capabilities
- PodAntiAffinity: 同 app=api-gateway 的 Pod 不在同一节点
- topologySpreadConstraints: 按 hostname 均匀分布
- HPA: CPU 60%, min 2, max 8
```

---

## 📊 评分卡

| 部分 | 题目 | 满分 | 得分 |
|------|------|------|------|
| 第一部分 | 集群运维 | 15 | |
| 第二部分 | 工作负载编排 | 25 | |
| 第三部分 | 网络配置 | 20 | |
| 第四部分 | 存储与配置 | 20 | |
| 第五部分 | 安全与调度 | 20 | |
| **总分** | | **100** | |

---

## 🏁 考后总结

```
得分：____ / 100
用时：____ 分钟

各模块得分情况：
- 集群运维：____ / 15
- 工作负载编排：____ / 25
- 网络配置：____ / 20
- 存储与配置：____ / 20
- 安全与调度：____ / 20

失分分析：
1. 最薄弱的模块：________
2. 主要失分原因：________
3. 时间分配是否合理？________

赛后提升计划：
1. ________
2. ________
3. ________
```

---

## 🎉 30 天学习完成

恭喜完成 Kubernetes 容器云 30 天学习计划！

```
回顾这段旅程：
- M1: 从零搭建了 K8s 集群
- M2: 掌握了 5 种工作负载
- M3: 构建了完整网络架构
- M4: 管理了配置和持久存储
- M5: 实现了智能调度和资源管理
- M6: 加固了集群安全
- M7: 建立了监控和排错体系
- M8: 完成了 8 套赛题模拟
```

### 后续建议

1. **赛前 3 天**：每天做一套限时模拟，保持手感
2. **赛前 1 天**：回顾速查手册，不再学新内容
3. **比赛当天**：先通读全部题目，按难度分配时间
4. **长期**：考取 CKA/CKAD 认证，深入源码和 Operator 开发

---

## 📋 命令速查

全真模拟考试必备命令速查（赛前 5 分钟默背）：

| 命令 | 功能 | 注解 |
|------|------|------|
| `k=kubectl` | 设置别名 | 节省 80% 键盘输入量 |
| `kubectl create deploy <name> --image=<img> --dry-run=client -o yaml > deploy.yaml` | YAML 速成 | 赛题 80% YAML 用此方式生成再修改 |
| `kubectl expose deploy <name> --port=<p> --target-port=<tp> --dry-run=client -o yaml` | Service YAML 速成 | 不要手写 Service YAML |
| `kubectl apply -f <file>.yaml` | 部署 | 优先 apply 而非 create |
| `kubectl get all -n <ns>` | 全面审计 | 确认所有资源已创建 |
| `kubectl describe pod <pod> \| tail -20` | 秒看 Event | 排错第一步 |
| `kubectl logs <pod> --tail=20` | 日志速看 | 验证应用输出 |
| `kubectl exec <pod> -- curl -s http://<svc>:<port>` | 功能验证 | 证明服务可达 |
| `kubectl create cm <name> --from-literal=k=v --dry-run=client -o yaml` | ConfigMap 速成 | 配置注入 |
| `kubectl create secret generic <name> --from-literal=k=v --dry-run=client -o yaml` | Secret 速成 | 密钥注入 |
| `kubectl scale deploy <name> --replicas=<n>` | 副本调整 | 注意赛题要求的具体数量 |
| `kubectl rollout undo deploy/<name>` | 回滚 | 操作失误首选回滚 |
| `kubectl get events --field-selector type=Warning` | Warning 事件 | 致命错误秒定位 |
| `!k` 或 `history \| grep kubectl` | 复用历史命令 | 一条命令多个任务使用 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：kubectl 速查表（打印版） | https://kubernetes.io/docs/reference/kubectl/quick-reference/ |
| Kubernetes 官方：命令参考 | https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands |
| kubectl 最佳实践 | https://kubernetes.io/docs/reference/kubectl/conventions/ |
