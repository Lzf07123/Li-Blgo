---
title: Day 05 - Deployment 与 ReplicaSet
module: M2-Pod与核心工作负载
day: 5
updated: 2026-06-10
duration: 240 分钟
level: 核心
prerequisites:
- Day 04 完成，理解 Pod 和探针
objectives:
- 理解 ReplicaSet 职责
- 掌握 Deployment 滚动更新机制
- 能执行回滚、扩缩容
- 掌握金丝雀发布基础
- 能排查滚动更新卡住问题
tags:
- Deployment
- ReplicaSet
- 滚动更新
- 回滚
- rollout
date: '2026-08-18'
status: published
---

# 📘 Day 05：Deployment 与 ReplicaSet

## 🎯 今日目标

- [ ] 理解 Deployment → ReplicaSet → Pod 的层级关系
- [ ] 能执行滚动更新并观察 Pod 替换过程
- [ ] 能用 `rollout undo` 回滚到任意版本
- [ ] 能用 `rollout pause/resume` 实现金丝雀发布
- [ ] 能排查滚动更新卡住的常见原因

---

## 🧠 理论精讲（30 分钟）

### 三层关系

```
Deployment  ─── 管理版本、更新策略
    │
    └──→ ReplicaSet  ─── 确保 Pod 副本数达标
              │
              └──→ Pod  ─── 运行容器
```

每次 Deployment 更新会**创建新 ReplicaSet**，旧的 ReplicaSet 保留（用于回滚）。

### 滚动更新策略

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `maxSurge` | 更新期间最多超出多少个 Pod | 25% |
| `maxUnavailable` | 更新期间最多不可用多少个 Pod | 25% |

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1          # 一次最多多创建 1 个
    maxUnavailable: 0    # 任何时刻必须有全部 Pod 可用
```

### 关键命令速查

| 命令 | 用途 |
|------|------|
| `kubectl rollout status deploy/<name>` | 查看更新进度 |
| `kubectl rollout history deploy/<name>` | 查看版本历史 |
| `kubectl rollout undo deploy/<name>` | 回滚到上一版本 |
| `kubectl rollout pause deploy/<name>` | 暂停更新 |
| `kubectl rollout resume deploy/<name>` | 恢复更新 |

---

## 🔧 动手实操（120 分钟）

### 练习 5.1：创建 Deployment + 观察 ReplicaSet

```bash
# 1. 创建 Deployment（3 副本）
kubectl create deploy nginx --image=nginx:1.21 --replicas=3

# 2. 查看 Deployment
kubectl get deploy nginx
# NAME    READY   UP-TO-DATE   AVAILABLE   AGE
# nginx   3/3     3            3           30s

# 3. 查看 ReplicaSet（自动创建）
kubectl get rs -l app=nginx
# NAME               DESIRED   CURRENT   READY   AGE
# nginx-<hash>       3         3         3       30s

# 4. 查看 RS 管理的 Pod
kubectl get pod -l app=nginx -o wide
# 3 个 Pod 分布在不同节点

# 5. 验证 RS 的自我修复：删除一个 Pod
kubectl delete pod <任意一个 nginx pod>
kubectl get pod -l app=nginx -w
# RS 立即创建新 Pod 补足 3 副本
```

---

### 练习 5.2：滚动更新全流程

```bash
# 打开 3 个终端窗口：

# 终端1：观察 Deployment 状态
kubectl get deploy nginx -w

# 终端2：观察 Pod 变化
kubectl get pod -l app=nginx -w

# 终端3：观察 ReplicaSet 变化
kubectl get rs -l app=nginx -w

# === 触发滚动更新 ===

# 终端4：更新镜像
kubectl set image deploy/nginx nginx=nginx:1.22

# 在终端1 观察：
# UP-TO-DATE 从 0 → 1 → 2 → 3
# 在终端2 观察：
# 新 Pod 创建，旧 Pod 逐步 Terminating
# 在终端3 观察：
# 新 RS 的 DESIRED 递增，旧 RS 的 DECREASED 递减

# 查看更新状态
kubectl rollout status deploy/nginx

# 查看更新历史
kubectl rollout history deploy/nginx
# REVISION  CHANGE-CAUSE
# 1         <none>
# 2         <none>
```

---

### 练习 5.3：回滚操作

```bash
# 1. 制造一个失败的更新
kubectl set image deploy/nginx nginx=nginx:not-exists

# 2. 观察卡住
kubectl rollout status deploy/nginx
# 看到 "Waiting for deployment rollout to finish..."

# 3. 查看 Pod 状态
kubectl get pod -l app=nginx
# 新 Pod ImagePullBackOff 或 ErrImagePull

# 4. 立即回滚！
kubectl rollout undo deploy/nginx

# 5. 查看回滚后的 Pod 状态
kubectl get pod -l app=nginx
# 恢复为旧版本

# 6. 查看历史记录
kubectl rollout history deploy/nginx
# REVISION  CHANGE-CAUSE
# 1         <none>
# 3         <none>        # REVISION 2 被跳过了

# 7. 回滚到指定 REVISION
kubectl rollout undo deploy/nginx --to-revision=1

# 8. 为更新添加记录标记
kubectl set image deploy/nginx nginx=nginx:1.23 --record=false
# 注意：--record 在新版中已弃用，使用 annotation 替代
kubectl annotate deploy/nginx kubernetes.io/change-cause="update to 1.23"
kubectl rollout history deploy/nginx
```

---

### 练习 5.4：扩缩容

```bash
# 1. 快速扩容到 6 个副本
kubectl scale deploy/nginx --replicas=6

# 2. 观察 Pod 增加
kubectl get pod -l app=nginx -w

# 3. 缩容到 2 个
kubectl scale deploy/nginx --replicas=2

# 4. 观察 Pod 被终止
kubectl get pod -l app=nginx -w

# 5. 查看 Deployment 的当前期望和实际状态
kubectl get deploy nginx -o jsonpath='
期望副本：{.spec.replicas}
就绪副本：{.status.readyReplicas}
可用副本：{.status.availableReplicas}
'
```

---

### 练习 5.5：金丝雀发布基础（pause/resume）

```bash
# 原理：暂停滚动更新 → 验证小部分新 Pod → 恢复全量更新

# 1. 恢复到稳定状态
kubectl scale deploy/nginx --replicas=10

# 2. 暂停 Deployment 的滚动更新
kubectl rollout pause deploy/nginx

# 3. 触发镜像更新（因为有 pause，只会创建新 RS 但不创建新 Pod）
kubectl set image deploy/nginx nginx=nginx:1.24
kubectl annotate deploy/nginx kubernetes.io/change-cause="canary 1.24"

# 4. 查看当前的 ReplicaSet
kubectl get rs -l app=nginx
# 看到新 RS 的 DESIRED=0（因为暂停了）

# 5. "放行" 1 个新版本 Pod 做金丝雀验证
# 方法：手动改新 RS 的 replicas（不太好）
# 更好方法：直接 resume 但限制 maxSurge
kubectl rollout resume deploy/nginx

# 6. 实时观察
kubectl rollout status deploy/nginx

# 7. 清理
kubectl delete deploy nginx
```

---

## 🐛 排错练习（30 分钟）

### 场景 1：滚动更新卡住 — 镜像拉取失败

```bash
# 1. 创建 Deployment
kubectl create deploy test --image=nginx:1.21 --replicas=3

# 2. 更新到不存在镜像
kubectl set image deploy/test nginx=nginx:99.99

# 3. 观察状态
kubectl get deploy test
# 看到 READY 3/3、UP-TO-DATE 1、AVAILABLE 3

kubectl get rs -l app=test
# 新 RS READY=0，旧 RS READY=3

kubectl get pod -l app=test
# 新 Pod ImagePullBackOff

# 4. 查看详细原因
kubectl describe pod <新 pod> | grep -A5 Events

# 5. 排查命令总结
kubectl rollout status deploy/test
kubectl describe deploy test
kubectl logs <pod-name>  # 如果是应用启动失败

# 6. 回滚
kubectl rollout undo deploy/test

# 7. 清理
kubectl delete deploy test
```

### 场景 2：回滚失败（无历史记录）

```bash
# 创建新 Deployment
kubectl create deploy test2 --image=nginx:1.21 --replicas=2

# 查看 revisionHistoryLimit（默认 10）
kubectl get deploy test2 -o jsonpath='{.spec.revisionHistoryLimit}'

# 模拟没有历史
kubectl rollout undo deploy/test2
# 可能报错：no rollout history found（首次创建没有历史）

# 解决方案：至少要有一次成功的更新才能回滚
kubectl set image deploy/test2 nginx=nginx:1.22
kubectl rollout status deploy/test2
kubectl rollout history deploy/test2
# 现在有了两个 revision

kubectl delete deploy test2
```

---

## 🏆 赛题模拟（40 分钟）

> ⚠️ 严格限时 **40 分钟**

**题目：Deployment 滚动发布综合**

```
【操作要求】

1. 用 --dry-run=client 生成 Deployment YAML：
   - 名称：web-app
   - 镜像：nginx:1.21-alpine
   - 副本数：5
   - 资源限制：cpu 100m, memory 128Mi
   - 滚动更新策略：maxSurge=1, maxUnavailable=0

2. 应用该 YAML，等待所有 Pod Ready

3. 执行以下版本变更序列：
   a. 更新到 nginx:1.22-alpine，记录 change-cause
   b. 等待完成
   c. 更新到 nginx:1.23-alpine，记录 change-cause
   d. 等待完成

4. 假设 1.23 版本有 bug，请：
   a. 先回滚到上一个版本
   b. 再回滚到最初版本（1.21-alpine）
   c. 确认最终所有 Pod 使用 nginx:1.21-alpine

5. 将副本数缩放到 2，再扩容到 5

6. 输出 rollout history 完整记录

【验证命令】
kubectl rollout history deploy/web-app
kubectl get deploy web-app -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl get pod -l app=web-app -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.containers[0].image}{"\n"}{end}'

【评分标准】
- YAML 正确（20 分）
- 滚动更新步骤正确（30 分）
- 回滚到指定版本正确（25 分）
- 扩缩容正确（15 分）
- history 记录完整（10 分）
```

---

## 📋 命令速查

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl create deploy nginx --image=nginx:alpine` | 创建 Deployment | 最快捷的部署方式 |
| `kubectl get deploy` | 列出 Deployment | DESIRED/CURRENT/READY/UP-TO-DATE/AVAILABLE 五个状态字段 |
| `kubectl get deploy -o wide` | Deployment + 镜像/标签/选择器 | 确认当前使用的镜像版本 |
| `kubectl get rs` | 列出 ReplicaSet | Deployment 每次更新生成新 RS |
| `kubectl get deploy,rs,pod` | 同时查看 Deploy→RS→Pod 层级 | 逗号分隔多资源类型 |
| `kubectl describe deploy <name>` | Deployment 详细信息 | 包含滚动更新策略、事件历史 |
| `kubectl scale deploy <name> --replicas=5` | 扩缩副本 | 等价于修改 spec.replicas |
| `kubectl set image deploy/<name> <container>=<new-image>:<tag>` | 更新容器镜像 | 触发滚动更新，比 edit 效率高 |
| `kubectl set resources deploy/<name> -c=<container> --limits=cpu=200m,memory=256Mi --requests=cpu=100m,memory=128Mi` | 设置资源限制 | 更新 Pod 模板中的 resources 字段 |
| `kubectl rollout status deploy/<name>` | 查看滚动更新进度 | 输出 "successfully rolled out" 即完成 |
| `kubectl rollout history deploy/<name>` | 查看部署历史 | 每次更新生成一个 revision 号 |
| `kubectl rollout history deploy/<name> --revision=3` | 查看第 3 个版本的详情 | 对比不同版本的镜像和配置 |
| `kubectl rollout undo deploy/<name>` | 回滚上一版本 | 创建新 RS 并回退 Pod 模板 |
| `kubectl rollout undo deploy/<name> --to-revision=2` | 回滚到指定版本 | revision 必须存在于历史中（默认保留 10 个） |
| `kubectl rollout pause deploy/<name>` | 暂停滚动更新 | 金丝雀发布时暂停以验证新版 |
| `kubectl rollout resume deploy/<name>` | 恢复滚动更新 | 暂停后恢复继续滚动 |
| `kubectl rollout restart deploy/<name>` | 重启所有 Pod（滚动重建） | 1.15+ 支持，配置变更后快速生效 |
| `kubectl patch deploy <name> -p '{"spec":{"minReadySeconds":10}}'` | JSON Patch 修改字段 | 比 edit 安全，适合 CI/CD |
| `kubectl delete deploy <name>` | 删除 Deployment | 级联删除 RS 和 Pod（默认） |
| `kubectl delete deploy <name> --cascade=orphan` | 仅删 Deploy 保留 Pod | Pod 变为孤儿，由新控制器接管 |
| `kubectl get pod --show-labels` | Pod + 标签 | 验证标签选择器是否匹配 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：Deployment | https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ |
| Kubernetes 官方：ReplicaSet | https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/ |
| Kubernetes 官方：滚动更新 | https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/ |
| Kubernetes 官方：回滚 Deployment | https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment |
| Kubernetes 官方：kubectl rollout | https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#rollout |
