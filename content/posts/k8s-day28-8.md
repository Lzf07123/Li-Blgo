---
title: Day 28 - 赛题模拟 8 + 限时挑战
module: M8-综合实战与赛题模拟
day: 28
updated: 2026-06-10
duration: 240 分钟
level: 冲刺
prerequisites:
- M1-M7 全部完成
objectives:
- 完成终极赛题
- 限时挑战：60 分钟极限操作
tags:
- 赛题模拟
- 终极赛题
- 限时挑战
date: '2026-08-18'
status: published
---

# 📘 Day 28：赛题模拟 8 + 限时挑战

## 🎯 今日目标

- 完成最综合的赛题（120 分钟）
- 完成限时挑战赛（60 分钟极限操作）

---

## 🏆 赛题 8：终极综合赛题（120 分钟）

```
【场景】模拟职业技能大赛决赛场景：完整项目部署 + 运维 + 安全 + 排错。

【操作要求】（总分 100 分）

Part A: 集群准备（10 分）
1. 检查集群状态：所有节点 Ready
2. 确认 metrics-server 可用
3. 确认 NGINX Ingress Controller 已安装

Part B: 项目部署（40 分）
部署一个"在线商城"微服务系统：

4. 命名空间：online-mall

5. 用户服务（user-svc）：
   - Deployment user-api（3副本，nginx:alpine）
   - ClusterIP Service user-svc
   - ConfigMap user-config: DB=mysql, PORT=3306

6. 商品服务（product-svc）：
   - Deployment product-api（2副本，httpd:alpine）
   - ClusterIP Service product-svc

7. 订单服务（order-svc）：
   - StatefulSet order-db（2副本，redis:7-alpine）
   - Headless Service order-db-svc
   - volumeClaimTemplates: 100Mi

8. 网关：
   - Ingress: mall.example.com
   - /api/users → user-svc:80
   - /api/products → product-svc:80
   - / → user-svc:80

9. 前端：
   - Deployment mall-web（2副本，nginx:alpine）

Part C: 高级配置（25 分）
10. NetworkPolicy：
    - 默认拒绝所有 ingress
    - user-api → order-db:6379
    - product-api → order-db:6379
    - Ingress Controller → user-api:80
    - Ingress Controller → product-api:80
    - Ingress Controller → mall-web:80
    - 所有 Pod → DNS

11. RBAC：
    - SA mall-admin：对 online-mall 所有资源有全部权限
    - SA mall-reader：对 Pod/Deploy/Service 有只读权限

12. HPA：
    - user-api：CPU 50%, min 2, max 6
    - product-api：CPU 60%, min 2, max 4

Part D: 安全加固（15 分）
13. 所有 Deployment 的 SecurityContext：
    - runAsNonRoot
    - allowPrivilegeEscalation: false
    - drop ALL capabilities
14. 所有 Deployment 设置资源限制：
    - requests: cpu=100m, mem=128Mi
    - limits: cpu=300m, mem=256Mi

Part E: 故障演练与恢复（10 分）
15. 删除一个 user-api Pod，验证自愈
16. 回滚 product-api 到上一个版本
17. 手动触发 order-db 的缩容和扩容

【验证清单】
□ 所有 5 个微服务 Running
□ Ingress 路由正确
□ NetworkPolicy 隔离生效
□ RBAC 权限正确
□ HPA 生效
□ SecurityContext 加固
```

---

## ⚡ 限时挑战赛（60 分钟）

```
【规则】60 分钟内尽可能多地完成以下任务，按完成度计分。

【挑战任务】（每题有对应分数，总分 100）

□ 任务 1（5 分）：用 --dry-run=client 生成一个 Deploy + Service YAML
□ 任务 2（5 分）：创建一个 Pod 带 InitContainer 等待 DNS 可用
□ 任务 3（10 分）：配置一个 StatefulSet，3副本，每个独立 PVC
□ 任务 4（10 分）：创建 Ingress 实现路径路由 /v1 → svc-a, /v2 → svc-b
□ 任务 5（10 分）：创建 Deny-All NetworkPolicy + 逐层放行规则
□ 任务 6（10 分）：配置 RBAC：dev 用户只能 get/list Pod
□ 任务 7（10 分）：创建 ResourceQuota + LimitRange 并验证
□ 任务 8（10 分）：配置 HPA，生成负载验证自动伸缩
□ 任务 9（10 分）：排查并修复一个 CrashLoopBackOff Pod
□ 任务 10（10 分）：创建带 SecurityContext 的安全 Pod
□ 任务 11（10 分）：执行 etcd 备份并验证快照

【计分规则】
- 60 分钟内完成
- 每个任务：命令正确 = 满分，部分正确 = 一半
- 60 分以上及格，80 分以上优秀
```

## 📋 命令速查

该赛题涉及的核心命令速查（含限时挑战高频命令）：

| 命令 | 功能 | 注解 |
|------|------|------|
| `kubectl create deploy <name> --image=<image> --dry-run=client -o yaml > deploy.yaml` | 生成 Deployment YAML | 限时挑战中不手动写 YAML，用此生成后修改 |
| `kubectl create cm <name> --from-literal=key=value --dry-run=client -o yaml` | 生成 ConfigMap YAML | 秒出模板，修改即可部署 |
| `kubectl expose deploy <name> --port=80 --dry-run=client -o yaml` | 生成 Service YAML | 快速生成 Service 模板 |
| `kubectl apply -f <file>.yaml` | 声明式部署 | 一键部署所有资源 |
| `kubectl get all -n <ns>` | 查看所有资源 | 快速审计部署结果 |
| `kubectl describe pod <pod> \| tail -20` | Pod Events 摘要 | 出错时秒看原因 |
| `kubectl logs <pod> --tail=10` | 快速看日志 | 限时场景只看最后几行 |
| `kubectl exec <pod> -- <verify-cmd>` | 验证功能 | curl/wget/cat 验证结果 |
| `kubectl rollout undo deploy/<name>` | 快速回滚 | 出错了不纠结，先回滚再改 |
| `kubectl delete pod <pod> --force --grace-period=0` | 强制删 Pod | 卡 Terminating 时秒杀 |
| `kubectl get events --field-selector type=Warning \| tail -10` | 只看 Warning | 限时排错最佳实践 |

## 📚 参考来源

| 来源 | 链接 / 说明 |
|------|------------|
| Kubernetes 官方：kubectl 速查表 | https://kubernetes.io/docs/reference/kubectl/quick-reference/ |
| Kubernetes 官方：命令参考 | https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands |
| CKA 模拟题（限时模式） | https://killer.sh |
| kubectl 最佳实践 | https://kubernetes.io/docs/reference/kubectl/conventions/ |
