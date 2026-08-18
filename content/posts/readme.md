---
title: 职业技能大赛云计算赛项资料共享知识库
date: '2026-08-18'
status: published
tags:
- 使用说明
- 目录索引
- 学习路线
- 常见问题
summary: ''
---

# 📚 职业技能大赛云计算赛项 · 资料共享知识库

> 本仓库汇集云计算赛项相关的**理论知识**、**Linux 操作指南**、**容器与云平台技术文档**以及**结构化学习路线**，共 **287 篇 Markdown 文档**，按主题分类归档，涵盖 Docker、Kubernetes、OpenStack、Linux 系统管理等方向，内容持续更新中。

---

## 📝 更新日志

> 记录本知识库的新增内容与重要变更，最新更新在最前。

| 日期       |  类型   | 说明                                                                                                     |
| ---------- | :-----: | -------------------------------------------------------------------------------------------------------- |
| 2026-06-21 | 📑 索引 | 重构 README，新增完整计划索引与 Hexo `post_link` 全文章目录                                              |
| 2026-06-10 | 🆕 计划 | 上线 {% post_link kubernetes学习计划/k8s-00-学习路线总览 'Kubernetes 30 天学习计划' %}（8 模块 / 30 天） |
| 2026-06-09 | 🆕 内容 | 新增 Kubernetes 章节与学习路线                                                                           |
| 2025-05-20 | 🚀 创建 | 知识库正式上线，首批导入 Linux 系统管理、Docker、OpenStack 等基础内容                                    |

---

## 📂 目录概览

| 分类              | 说明                                                | 文档数  |
| ----------------- | --------------------------------------------------- | :-----: |
| 🗓️ 学习路线与计划 | K8s 30天计划、Linux 1月速成、容器云路径、私有云路径 |   59    |
| 🐳 容器与云原生   | Docker + Kubernetes + 容器基础核心概念              |   33    |
| ☁️ 私有云         | OpenStack 服务架构与详细原理                        |   20    |
| 🐧 Linux 系统管理 | 系统管理、网络、权限、进程、磁盘等 10 个子分类      |   161   |
| 📋 基础与通用技能 | 云计算基础、数据格式标准、发行版对比                |   11    |
| 🏆 竞赛与认证     | 赛题、样题解析、知识点汇总                          |    3    |
| **合计**          |                                                     | **287** |

---

## 🗓️ 计划索引

> 以下为本仓库提供的结构化学习计划，按顺序学习可获得系统性知识体系。

### Kubernetes 30 天学习计划

**总览：**{% post_link kubernetes学习计划/k8s-00-学习路线总览 'Kubernetes 容器云学习路线总览' %}

从集群搭建到赛题模拟，共 **30 天 / 8 个模块**，每日约 4 小时，适合有 Linux 基础的容器云入门者。

| 模块 | 主题               |   天数    | 核心内容                                                      |
| :--: | ------------------ | :-------: | ------------------------------------------------------------- |
|  M1  | 集群架构与搭建     |  Day 1-3  | 架构原理、环境准备、多节点集群、kubectl 精通                  |
|  M2  | Pod 与核心工作负载 |  Day 4-7  | Pod 生命周期、Deployment、DaemonSet、StatefulSet、Job/CronJob |
|  M3  | 网络与服务发现     | Day 8-11  | Service、Ingress、网络策略、CNI 原理                          |
|  M4  | 存储与配置管理     | Day 12-15 | ConfigMap/Secret、Volume、PV/PVC、StorageClass                |
|  M5  | 调度与资源管理     | Day 16-18 | 调度策略、亲和性/反亲和性、资源限制与 QoS                     |
|  M6  | 安全与认证         | Day 19-21 | RBAC、ServiceAccount、镜像安全、网络策略                      |
|  M7  | 监控日志与排错     | Day 22-24 | Prometheus 监控、EFK 日志、故障排查实战                       |
|  M8  | 综合实战与赛题模拟 | Day 25-30 | 真题模拟、弱点回顾、全真模拟考试                              |

#### M1 · 集群架构与搭建

{% post_link kubernetes学习计划/M1-集群架构与搭建/k8s-day01-集群架构原理与环境准备 'Day 1 - 集群架构原理与环境准备' %}
{% post_link kubernetes学习计划/M1-集群架构与搭建/k8s-day02-多节点集群与节点管理 'Day 2 - 多节点集群与节点管理' %}
{% post_link kubernetes学习计划/M1-集群架构与搭建/k8s-day03-集群运维与kubectl精通 'Day 3 - 集群运维与 kubectl 精通' %}

#### M2 · Pod 与核心工作负载

{% post_link kubernetes学习计划/M2-Pod与核心工作负载/k8s-day04-Pod生命周期与多容器模式 'Day 4 - Pod 生命周期与多容器模式' %}
{% post_link kubernetes学习计划/M2-Pod与核心工作负载/k8s-day05-Deployment与ReplicaSet 'Day 5 - Deployment 与 ReplicaSet' %}
{% post_link kubernetes学习计划/M2-Pod与核心工作负载/k8s-day06-DaemonSet-StatefulSet-Job-CronJob 'Day 6 - DaemonSet、StatefulSet、Job、CronJob' %}
{% post_link kubernetes学习计划/M2-Pod与核心工作负载/k8s-day07-Pod资源综合实战 'Day 7 - Pod 资源综合实战' %}

#### M3 · 网络与服务发现

{% post_link kubernetes学习计划/M3-网络与服务发现/k8s-day08-Service与集群内服务发现 'Day 8 - Service 与集群内服务发现' %}
{% post_link kubernetes学习计划/M3-网络与服务发现/k8s-day09-Ingress与外部流量接入 'Day 9 - Ingress 与外部流量接入' %}
{% post_link kubernetes学习计划/M3-网络与服务发现/k8s-day10-网络策略与CNI原理 'Day 10 - 网络策略与 CNI 原理' %}
{% post_link kubernetes学习计划/M3-网络与服务发现/k8s-day11-网络综合实战 'Day 11 - 网络综合实战' %}

#### M4 · 存储与配置管理

{% post_link kubernetes学习计划/M4-存储与配置管理/k8s-day12-ConfigMap与Secret 'Day 12 - ConfigMap 与 Secret' %}
{% post_link kubernetes学习计划/M4-存储与配置管理/k8s-day13-Volume与PV-PVC 'Day 13 - Volume 与 PV/PVC' %}
{% post_link kubernetes学习计划/M4-存储与配置管理/k8s-day14-StorageClass与动态供给 'Day 14 - StorageClass 与动态供给' %}
{% post_link kubernetes学习计划/M4-存储与配置管理/k8s-day15-存储综合实战 'Day 15 - 存储综合实战' %}

#### M5 · 调度与资源管理

{% post_link kubernetes学习计划/M5-调度与资源管理/k8s-day16-调度策略与亲和性 'Day 16 - 调度策略与亲和性' %}
{% post_link kubernetes学习计划/M5-调度与资源管理/k8s-day17-资源限制与QoS 'Day 17 - 资源限制与 QoS' %}
{% post_link kubernetes学习计划/M5-调度与资源管理/k8s-day18-调度综合实战 'Day 18 - 调度综合实战' %}

#### M6 · 安全与认证

{% post_link kubernetes学习计划/M6-安全与认证/k8s-day19-RBAC权限控制 'Day 19 - RBAC 权限控制' %}
{% post_link kubernetes学习计划/M6-安全与认证/k8s-day20-ServiceAccount与镜像安全 'Day 20 - ServiceAccount 与镜像安全' %}
{% post_link kubernetes学习计划/M6-安全与认证/k8s-day21-安全综合实战 'Day 21 - 安全综合实战' %}

#### M7 · 监控日志与排错

{% post_link kubernetes学习计划/M7-监控日志与排错/k8s-day22-Prometheus监控体系 'Day 22 - Prometheus 监控体系' %}
{% post_link kubernetes学习计划/M7-监控日志与排错/k8s-day23-日志收集与EFK 'Day 23 - 日志收集与 EFK' %}
{% post_link kubernetes学习计划/M7-监控日志与排错/k8s-day24-故障排查实战 'Day 24 - 故障排查实战' %}

#### M8 · 综合实战与赛题模拟

{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day25-赛题模拟1-3 'Day 25 - 赛题模拟 1-3' %}
{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day26-赛题模拟4-5 'Day 26 - 赛题模拟 4-5' %}
{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day27-赛题模拟6-7 'Day 27 - 赛题模拟 6-7' %}
{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day28-赛题模拟8+限时挑战 'Day 28 - 赛题模拟 8 + 限时挑战' %}
{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day29-弱点回顾与强化 'Day 29 - 弱点回顾与强化' %}
{% post_link kubernetes学习计划/M8-综合实战与赛题模拟/k8s-day30-全真模拟考试 'Day 30 - 全真模拟考试' %}

### Linux 1 月速成计划

**总览：**{% post_link 学习路线与课程/linux-1月速成计划学习路线图 'Linux 1 月速成计划学习路线图' %}

4 周掌握 Linux 日常操作与运维技能，**纯终端实操、排错驱动**，适合零基础入门。

|  周次  | 主题               | 每日内容                                                             |
| :----: | ------------------ | -------------------------------------------------------------------- |
| Week 1 | 文件与目录基础     | 路径切换 → 文件操作 → 内容查看 → 文本统计 → 串联实操 → 综合实战      |
| Week 2 | 用户权限与进程管理 | 用户身份 → 权限深入 → 进程管理 → 管道重定向 → 串联实操 → 综合实战    |
| Week 3 | 文本处理三剑客     | grep 基础 → 正则进阶 → sed 流编辑 → awk 列处理 → 打包压缩 → 综合实战 |
| Week 4 | 网络与系统运维     | 网络诊断 → SSH 远程 → 资源监控 → 定时任务 → 串联实操 → 综合实战      |

#### Week 1 · 文件与目录基础

{% post_link 学习路线与课程/week1-day1-路径与目录切换 'Day 1 - 路径与目录切换' %}
{% post_link 学习路线与课程/week1-day2-文件与目录操作 'Day 2 - 文件与目录操作' %}
{% post_link 学习路线与课程/week1-day3-文件内容查看 'Day 3 - 文件内容查看' %}
{% post_link 学习路线与课程/week1-day4-文本统计与处理 'Day 4 - 文本统计与处理' %}
{% post_link 学习路线与课程/week1-day5-本周串联实操 'Day 5 - 本周串联实操' %}
{% post_link 学习路线与课程/week1-weekend-综合实战 'Weekend - 综合实战' %}

#### Week 2 · 用户权限与进程管理

{% post_link 学习路线与课程/week2-day1-用户身份与基本权限 'Day 1 - 用户身份与基本权限' %}
{% post_link 学习路线与课程/week2-day2-权限深入与提权 'Day 2 - 权限深入与提权' %}
{% post_link 学习路线与课程/week2-day3-进程查看与管理 'Day 3 - 进程查看与管理' %}
{% post_link 学习路线与课程/week2-day4-前后台与重定向管道 'Day 4 - 前后台与重定向管道' %}
{% post_link 学习路线与课程/week2-day5-本周串联实操 'Day 5 - 本周串联实操' %}
{% post_link 学习路线与课程/week2-weekend-综合实战 'Weekend - 综合实战' %}

#### Week 3 · 文本处理三剑客

{% post_link 学习路线与课程/week3-day1-grep基础 'Day 1 - grep 基础' %}
{% post_link 学习路线与课程/week3-day2-grep正则 'Day 2 - grep 正则' %}
{% post_link 学习路线与课程/week3-day3-sed流编辑 'Day 3 - sed 流编辑' %}
{% post_link 学习路线与课程/week3-day4-awk列处理 'Day 4 - awk 列处理' %}
{% post_link 学习路线与课程/week3-day5-打包与压缩 'Day 5 - 打包与压缩' %}
{% post_link 学习路线与课程/week3-weekend-综合实战 'Weekend - 综合实战' %}

#### Week 4 · 网络与系统运维

{% post_link 学习路线与课程/week4-day1-网络诊断 'Day 1 - 网络诊断' %}
{% post_link 学习路线与课程/week4-day2-SSH远程连接 'Day 2 - SSH 远程连接' %}
{% post_link 学习路线与课程/week4-day3-系统资源监控 'Day 3 - 系统资源监控' %}
{% post_link 学习路线与课程/week4-day4-定时任务 'Day 4 - 定时任务' %}
{% post_link 学习路线与课程/week4-day5-本周串联实操 'Day 5 - 本周串联实操' %}
{% post_link 学习路线与课程/week4-weekend-综合实战 'Weekend - 综合实战' %}

### 容器云学习路径

**总览：**{% post_link 学习路线与课程/容器云学习路径 '容器云学习路径' %}

从容器基础（Namespace/Cgroups/OCI）→ Docker（镜像、网络、存储、Compose）→ Kubernetes 的完整知识体系。

### 私有云学习路径

**总览：**{% post_link 学习路线与课程/私有云学习路径 '私有云 OpenStack 学习路径' %}

从 OpenStack 概念与架构 → 核心组件（Keystone/Nova/Neutron/Glance）→ 存储（Cinder/Swift）→ 管理（Horizon/Heat/Ceilometer）→ 部署运维的完整路径。

### 学习技巧

{% post_link 学习路线与课程/学习技巧 '学习技巧' %}

---

## 📚 知识体系索引

> 按知识域分组的完整文章索引，点击链接即可访问对应文章。

### 🐳 容器与云原生

#### 容器基础

{% post_link 容器基础/OCI标准概述 'OCI 标准概述' %}
{% post_link 容器基础/容器核心概念 '容器核心概念' %}
{% post_link 容器基础/容器镜像仓库 '容器镜像仓库' %}

#### Docker

{% post_link Docker/Docker架构解析 'Docker 架构解析' %}
{% post_link Docker/Docker镜像管理 'Docker 镜像管理' %}
{% post_link Docker/Docker镜像管理详解 'Docker 镜像管理详解' %}
{% post_link Docker/Docker容器生命周期 'Docker 容器生命周期' %}
{% post_link Docker/Docker容器生命周期详解 'Docker 容器生命周期详解' %}
{% post_link Docker/Docker网络模型 'Docker 网络模型' %}
{% post_link Docker/Docker网络模型详解 'Docker 网络模型详解' %}
{% post_link Docker/Docker数据持久化 'Docker 数据持久化' %}
{% post_link Docker/Docker数据持久化详解 'Docker 数据持久化详解' %}
{% post_link Docker/Docker镜像仓库详解 'Docker 镜像仓库详解' %}
{% post_link Docker/Docker多容器编排详解 'Docker 多容器编排详解' %}
{% post_link Docker/Docker-Compose多容器编排入门 'Docker Compose 多容器编排入门' %}
{% post_link Docker/Docker实际应用-安装与部署Nginx 'Docker 实际应用 - 安装与部署 Nginx' %}
{% post_link Docker/Docker实际应用-构建自定义镜像 'Docker 实际应用 - 构建自定义镜像' %}

#### Kubernetes

{% post_link Kubernetes/Kubernetes核心概念全景 'Kubernetes 核心概念全景' %}
{% post_link Kubernetes/Kubernetes核心概念详解 'Kubernetes 核心概念详解' %}
{% post_link Kubernetes/Kubernetes网络模型与实现 'Kubernetes 网络模型与实现' %}
{% post_link Kubernetes/Kubernetes网络模型与实现详解 'Kubernetes 网络模型与实现详解' %}
{% post_link Kubernetes/Kubernetes存储抽象 'Kubernetes 存储抽象' %}
{% post_link Kubernetes/Kubernetes存储抽象详解 'Kubernetes 存储抽象详解' %}
{% post_link Kubernetes/Kubernetes调度与部署策略 'Kubernetes 调度与部署策略' %}
{% post_link Kubernetes/Kubernetes调度与部署详解 'Kubernetes 调度与部署详解' %}
{% post_link Kubernetes/Kubernetes资源管理 'Kubernetes 资源管理' %}
{% post_link Kubernetes/Kubernetes资源管理详解 'Kubernetes 资源管理详解' %}
{% post_link Kubernetes/Kubernetes安全基础 'Kubernetes 安全基础' %}
{% post_link Kubernetes/Kubernetes安全基础详解 'Kubernetes 安全基础详解' %}
{% post_link Kubernetes/Kubernetes可观测性 'Kubernetes 可观测性' %}
{% post_link Kubernetes/Kubernetes可观测性详解 'Kubernetes 可观测性详解' %}
{% post_link Kubernetes/Kubernetes配置与密文 'Kubernetes 配置与密文' %}
{% post_link Kubernetes/Kubernetes配置与密文详解 'Kubernetes 配置与密文详解' %}

### ☁️ 私有云

#### OpenStack

{% post_link OpenStack/OpenStack概述 'OpenStack 概述' %}
{% post_link OpenStack/OpenStack架构与分工 'OpenStack 架构与分工' %}

**核心服务**

{% post_link OpenStack/Keystone认证服务概念 'Keystone 认证服务 - 概念' %}
{% post_link OpenStack/OpenStack-Keystone详解 'Keystone 认证服务 - 详解' %}
{% post_link OpenStack/Nova计算服务概念 'Nova 计算服务 - 概念' %}
{% post_link OpenStack/OpenStack-Nova计算服务详解 'Nova 计算服务 - 详解' %}
{% post_link OpenStack/Neutron网络服务概念 'Neutron 网络服务 - 概念' %}
{% post_link OpenStack/OpenStack-Neutron网络服务详解 'Neutron 网络服务 - 详解' %}
{% post_link OpenStack/Glance镜像服务概念 'Glance 镜像服务 - 概念' %}
{% post_link OpenStack/OpenStack-Glance镜像服务详解 'Glance 镜像服务 - 详解' %}

**存储服务**

{% post_link OpenStack/Cinder块存储服务概念 'Cinder 块存储 - 概念' %}
{% post_link OpenStack/OpenStack-Cinder块存储详解 'Cinder 块存储 - 详解' %}
{% post_link OpenStack/Swift对象存储服务概念 'Swift 对象存储 - 概念' %}
{% post_link OpenStack/OpenStack-Swift对象存储详解 'Swift 对象存储 - 详解' %}

**管理与监控**

{% post_link OpenStack/HorizonWeb界面概念 'Horizon Web 界面 - 概念' %}
{% post_link OpenStack/OpenStack-Horizon详解 'Horizon Web 界面 - 详解' %}
{% post_link OpenStack/Heat编排服务概念 'Heat 编排服务 - 概念' %}
{% post_link OpenStack/OpenStack-Heat(编排)详解 'Heat 编排服务 - 详解' %}
{% post_link OpenStack/Ceilometer监控计量服务概念 'Ceilometer 监控计量 - 概念' %}
{% post_link OpenStack/OpenStack-Ceilometer监控计量详解 'Ceilometer 监控计量 - 详解' %}

### 🐧 Linux 系统管理

#### 文件与目录管理

{% post_link 文件与目录管理/文件与目录管理-ls 'ls - 列出目录内容' %}
{% post_link 文件与目录管理/文件与目录管理-cd 'cd - 切换目录' %}
{% post_link 文件与目录管理/文件与目录管理-pwd 'pwd - 显示当前路径' %}
{% post_link 文件与目录管理/文件与目录管理-mkdir 'mkdir - 创建目录' %}
{% post_link 文件与目录管理/文件与目录管理-cp 'cp - 复制文件与目录' %}
{% post_link 文件与目录管理/文件与目录管理-mv 'mv - 移动/重命名文件' %}
{% post_link 文件与目录管理/文件与目录管理-rm 'rm - 删除文件' %}
{% post_link 文件与目录管理/文件与目录管理-rmdir 'rmdir - 删除空目录' %}
{% post_link 文件与目录管理/文件与目录管理-touch 'touch - 创建文件/更新时间戳' %}
{% post_link 文件与目录管理/文件与目录管理-ln 'ln - 创建链接' %}
{% post_link 文件与目录管理/文件与目录管理-find 'find - 查找文件' %}
{% post_link 文件与目录管理/文件与目录管理-locate 'locate - 快速定位文件' %}
{% post_link 文件与目录管理/文件与目录管理-tree 'tree - 树形显示目录' %}
{% post_link 文件与目录管理/文件与目录管理-stat 'stat - 查看文件状态' %}
{% post_link 文件与目录管理/文件与目录管理-file 'file - 识别文件类型' %}
{% post_link 文件与目录管理/文件与目录管理-df 'df - 磁盘空间使用' %}
{% post_link 文件与目录管理/文件与目录管理-du 'du - 目录空间占用' %}

#### 文件查看与文本处理

{% post_link 文件查看与文本处理/文件查看与文本处理-cat 'cat - 连接并显示文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-less 'less - 分页浏览文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-more 'more - 分页显示文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-head 'head - 查看文件头部' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-tail 'tail - 查看文件尾部' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-tac 'tac - 反向输出文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-nl 'nl - 带行号显示文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-cut 'cut - 按列剪切文本' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-sort 'sort - 排序文本' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-uniq 'uniq - 去重与统计' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-wc 'wc - 统计行数/词数/字符数' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-grep 'grep - 文本搜索过滤' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-sed 'sed - 流编辑器' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-awk 'awk - 文本处理语言' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-diff 'diff - 文件差异对比' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-comm 'comm - 比较已排序文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-join 'join - 关联合并文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-paste 'paste - 按列合并文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-tr 'tr - 字符替换与删除' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-tee 'tee - 双向输出' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-xargs 'xargs - 参数传递' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-split 'split - 分割文件' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-od 'od - 八进制/十六进制查看' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-rev 'rev - 反转文本行' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-fold 'fold - 文本换行折叠' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-column 'column - 列格式化' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-echo 'echo - 输出文本' %}
{% post_link 文件查看与文本处理/文件查看与文本处理-printf 'printf - 格式化输出' %}

#### 系统管理

{% post_link 系统管理/系统管理-systemctl 'systemctl - 系统服务管理' %}
{% post_link 系统管理/系统管理-journalctl 'journalctl - 日志查看' %}
{% post_link 系统管理/系统管理-crontab 'crontab - 定时任务' %}
{% post_link 系统管理/系统管理-at 'at - 一次性定时任务' %}
{% post_link 系统管理/系统管理-date 'date - 日期时间' %}
{% post_link 系统管理/系统管理-timedatectl 'timedatectl - 时区与时间管理' %}
{% post_link 系统管理/系统管理-hostname 'hostname - 主机名管理' %}
{% post_link 系统管理/系统管理-uname 'uname - 系统信息' %}
{% post_link 系统管理/系统管理-lsblk 'lsblk - 列出块设备' %}
{% post_link 系统管理/系统管理-lscpu 'lscpu - CPU 信息' %}
{% post_link 系统管理/系统管理-lspci 'lspci - PCI 设备信息' %}
{% post_link 系统管理/系统管理-lsusb 'lsusb - USB 设备信息' %}
{% post_link 系统管理/系统管理-dmidecode 'dmidecode - 硬件信息' %}
{% post_link 系统管理/系统管理-free 'free - 内存使用情况' %}
{% post_link 系统管理/系统管理-dmesg 'dmesg - 内核日志' %}
{% post_link 系统管理/系统管理-history 'history - 命令历史' %}
{% post_link 系统管理/系统管理-alias-unalias 'alias / unalias - 命令别名' %}
{% post_link 系统管理/系统管理-export 'export - 环境变量导出' %}
{% post_link 系统管理/系统管理-env 'env - 环境变量管理' %}
{% post_link 系统管理/系统管理-locale 'locale - 语言环境' %}
{% post_link 系统管理/系统管理-man 'man - 手册查阅' %}
{% post_link 系统管理/系统管理-whatis 'whatis - 命令简介' %}
{% post_link 系统管理/系统管理-cal 'cal - 日历' %}
{% post_link 系统管理/系统管理-shutdown 'shutdown - 关机/重启' %}

#### 网络管理

{% post_link 网络管理/网络管理-curl 'curl - 网络请求工具' %}
{% post_link 网络管理/网络管理-wget 'wget - 文件下载工具' %}
{% post_link 网络管理/网络管理-ip 'ip - IP 网络配置' %}
{% post_link 网络管理/网络管理-ifconfig 'ifconfig - 网络接口配置' %}
{% post_link 网络管理/网络管理-netstat 'netstat - 网络连接统计' %}
{% post_link 网络管理/网络管理-ss 'ss - Socket 统计' %}
{% post_link 网络管理/网络管理-ping 'ping - 连通性测试' %}
{% post_link 网络管理/网络管理-traceroute-mtr 'traceroute / mtr - 路由追踪' %}
{% post_link 网络管理/网络管理-dig-nslookup-host 'dig / nslookup / host - DNS 查询' %}
{% post_link 网络管理/网络管理-nmap 'nmap - 端口扫描' %}
{% post_link 网络管理/网络管理-nc 'nc - 网络调试工具' %}
{% post_link 网络管理/网络管理-tcpdump 'tcpdump - 抓包分析' %}
{% post_link 网络管理/网络管理-ssh 'ssh - 远程登录' %}
{% post_link 网络管理/网络管理-scp 'scp - 远程文件复制' %}
{% post_link 网络管理/网络管理-rsync 'rsync - 远程同步' %}
{% post_link 网络管理/网络管理-iptables 'iptables - 防火墙' %}
{% post_link 网络管理/网络管理-ufw 'ufw - 简易防火墙' %}
{% post_link 网络管理/网络管理-lsof 'lsof - 列出打开的文件' %}
{% post_link 网络管理/网络管理-ethtool 'ethtool - 网卡配置' %}
{% post_link 网络管理/网络管理-route-arp 'route / arp - 路由与 ARP' %}

#### 权限与用户管理

{% post_link 权限与用户管理/权限与用户管理-chmod 'chmod - 修改文件权限' %}
{% post_link 权限与用户管理/权限与用户管理-chown 'chown - 修改文件所有者' %}
{% post_link 权限与用户管理/权限与用户管理-chgrp 'chgrp - 修改文件所属组' %}
{% post_link 权限与用户管理/权限与用户管理-umask 'umask - 默认权限掩码' %}
{% post_link 权限与用户管理/权限与用户管理-useradd 'useradd - 创建用户' %}
{% post_link 权限与用户管理/权限与用户管理-userdel 'userdel - 删除用户' %}
{% post_link 权限与用户管理/权限与用户管理-usermod 'usermod - 修改用户' %}
{% post_link 权限与用户管理/权限与用户管理-groupadd 'groupadd - 创建用户组' %}
{% post_link 权限与用户管理/权限与用户管理-groupdel 'groupdel - 删除用户组' %}
{% post_link 权限与用户管理/权限与用户管理-passwd 'passwd - 密码管理' %}
{% post_link 权限与用户管理/权限与用户管理-su 'su - 切换用户' %}
{% post_link 权限与用户管理/权限与用户管理-sudo 'sudo - 提权执行' %}
{% post_link 权限与用户管理/权限与用户管理-id 'id - 查看用户身份' %}
{% post_link 权限与用户管理/权限与用户管理-who 'who - 当前登录用户' %}
{% post_link 权限与用户管理/权限与用户管理-whoami 'whoami - 当前用户名' %}
{% post_link 权限与用户管理/权限与用户管理-w 'w - 用户活动信息' %}
{% post_link 权限与用户管理/权限与用户管理-last 'last - 登录历史' %}
{% post_link 权限与用户管理/权限与用户管理-users 'users - 当前登录用户列表' %}

#### 进程管理

{% post_link 进程管理/进程管理-ps 'ps - 查看进程' %}
{% post_link 进程管理/进程管理-top 'top - 实时进程监控' %}
{% post_link 进程管理/进程管理-htop 'htop - 交互式进程监控' %}
{% post_link 进程管理/进程管理-kill 'kill - 终止进程' %}
{% post_link 进程管理/进程管理-killall 'killall - 按名称终止进程' %}
{% post_link 进程管理/进程管理-pkill 'pkill - 按名称模式杀进程' %}
{% post_link 进程管理/进程管理-pgrep 'pgrep - 按名称查找进程' %}
{% post_link 进程管理/进程管理-pidof 'pidof - 获取进程 PID' %}
{% post_link 进程管理/进程管理-nice 'nice - 调整进程优先级' %}
{% post_link 进程管理/进程管理-renice 'renice - 修改运行中进程优先级' %}
{% post_link 进程管理/进程管理-nohup 'nohup - 后台免挂起运行' %}
{% post_link 进程管理/进程管理-bg-fg-jobs 'bg / fg / jobs - 前后台任务管理' %}
{% post_link 进程管理/进程管理-pstree 'pstree - 进程树' %}
{% post_link 进程管理/进程管理-uptime 'uptime - 系统运行时间' %}
{% post_link 进程管理/进程管理-time 'time - 命令执行计时' %}
{% post_link 进程管理/进程管理-watch 'watch - 周期性执行命令' %}

#### 磁盘与存储管理

{% post_link 磁盘与存储管理/磁盘与存储管理-fdisk 'fdisk - 磁盘分区' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-parted 'parted - 高级分区工具' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-mount 'mount - 挂载文件系统' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-findmnt 'findmnt - 查找挂载点' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-mkfs 'mkfs - 创建文件系统' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-fsck 'fsck - 文件系统检查' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-blkid 'blkid - 块设备属性' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-dd 'dd - 磁盘数据读写' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-eject 'eject - 弹出介质' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-smartctl 'smartctl - 磁盘健康检测' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-swapon-swapoff 'swapon / swapoff - 交换空间管理' %}
{% post_link 磁盘与存储管理/磁盘与存储管理-sync 'sync - 强制写入磁盘' %}

#### Shell 内置与杂项

{% post_link Shell内置与杂项/Shell内置与杂项-echo 'echo - 输出文本' %}
{% post_link Shell内置与杂项/Shell内置与杂项-printf 'printf - 格式化输出' %}
{% post_link Shell内置与杂项/Shell内置与杂项-read 'read - 读取输入' %}
{% post_link Shell内置与杂项/Shell内置与杂项-test 'test - 条件测试' %}
{% post_link Shell内置与杂项/Shell内置与杂项-eval-trap-shift 'eval / trap / shift - Shell 特殊内置命令' %}
{% post_link Shell内置与杂项/Shell内置与杂项-set-unset 'set / unset - Shell 选项与变量' %}
{% post_link Shell内置与杂项/Shell内置与杂项-source 'source - 执行脚本于当前 Shell' %}
{% post_link Shell内置与杂项/Shell内置与杂项-command-exec 'command / exec - 命令查找与替换' %}
{% post_link Shell内置与杂项/Shell内置与杂项-type 'type - 显示命令类型' %}
{% post_link Shell内置与杂项/Shell内置与杂项-which-whereis 'which / whereis - 定位命令路径' %}
{% post_link Shell内置与杂项/Shell内置与杂项-exit-clear 'exit / clear - 退出与清屏' %}
{% post_link Shell内置与杂项/Shell内置与杂项-true-false-sleep 'true / false / sleep - 返回码与休眠' %}

#### 包管理

{% post_link 包管理/包管理-apt 'apt - Debian 系包管理' %}
{% post_link 包管理/包管理-apt-get 'apt-get - Debian 系传统包管理' %}
{% post_link 包管理/包管理-dpkg 'dpkg - Debian 系底层包管理' %}
{% post_link 包管理/包管理-dnf-yum 'dnf / yum - Red Hat 系包管理' %}
{% post_link 包管理/包管理-rpm 'rpm - Red Hat 系底层包管理' %}
{% post_link 包管理/包管理-pacman 'pacman - Arch 系包管理' %}
{% post_link 包管理/包管理-snap-flatpak 'snap / flatpak - 通用包格式' %}

#### 压缩与归档

{% post_link 压缩与归档/压缩与归档-tar 'tar - 归档工具' %}
{% post_link 压缩与归档/压缩与归档-gzip 'gzip - GNU 压缩' %}
{% post_link 压缩与归档/压缩与归档-bzip2 'bzip2 - 高压缩率工具' %}
{% post_link 压缩与归档/压缩与归档-xz 'xz - 高压缩率工具' %}
{% post_link 压缩与归档/压缩与归档-zip-unzip 'zip / unzip - 跨平台压缩解压' %}
{% post_link 压缩与归档/压缩与归档-compress 'compress - 传统 Unix 压缩' %}
{% post_link 压缩与归档/压缩与归档-zgrep-zcat-zless 'zgrep / zcat / zless - 压缩文件内容操作' %}

### 📋 基础与通用技能

#### 云计算基础

{% post_link 云计算基础/云计算基础概念 '云计算基础概念' %}

#### 数据格式与标准

{% post_link 数据格式与标准/JSON文档格式概述 'JSON 文档格式概述' %}
{% post_link 数据格式与标准/YAML文档格式概述 'YAML 文档格式概述' %}
{% post_link 数据格式与标准/ini文件格式概述 'INI 文件格式概述' %}

#### 系统与发行版

{% post_link 系统与发行版/Linux发行版系别与差异详解 'Linux 发行版系别与差异详解' %}
{% post_link 系统与发行版/四大服务器系统对比总览 '四大服务器系统对比总览' %}
{% post_link 系统与发行版/Debian系统详情 'Debian 系统详情' %}
{% post_link 系统与发行版/CentOS系统详情 'CentOS 系统详情' %}
{% post_link 系统与发行版/Ubuntu系统详情 'Ubuntu 系统详情' %}
{% post_link 系统与发行版/openEuler系统详情 'openEuler 系统详情' %}

#### 杂项

{% post_link 杂项/linux-commands '常用 Linux 命令速查' %}

### 🏆 竞赛与认证

{% post_link 大赛与认证/职业技能大赛云计算赛项知识点 '职业技能大赛云计算赛项知识点' %}
{% post_link 大赛与认证/2025-2026广东省职业技能大赛云计算赛项赛题 '2025-2026 广东省职业技能大赛云计算赛项赛题' %}
{% post_link 大赛与认证/2025-DeepSeek大赛样题解析 '2025 DeepSeek 大赛样题解析' %}

---

## 📖 使用说明

### ⚠️ 重要声明

- **文章无特定顺序**：本知识库中的文章未按逻辑、优先级或时间线排序，排列位置不代表重要程度或阅读先后顺序，请根据需求通过标题或分类目录查阅。
- **部分文章可能无法被搜索索引**：受限于系统机制或标签缺失，部分文章可能无法被搜索框准确检索。若搜索无果，建议浏览相关分类目录或联系管理员。

### ❓ 常见问题（FAQ）

<details>
<summary>点击展开 FAQ</summary>

**Q1：为什么搜索关键词却找不到明明存在的文章？**

A：这正是上述声明中提到的"索引限制"。部分历史导入、特殊格式或未添加标签的文章可能被搜索引擎忽略。建议：

- 更换同义词或缩短关键词再次搜索；
- 直接前往对应分类目录下手动查找；
- 联系管理员补充该文章的搜索标签。

**Q2：文章内容出现错别字、过时或不准确怎么办？**

A：知识库需要大家共同维护。若发现内容有误，欢迎直接编辑修改；若暂无编辑权限，请联系管理员进行更正。

**Q3：如何快速找到需要的内容？**

A：推荐以下方式：

- **精准搜索**：使用搜索框输入核心专业词汇；
- **分类浏览**：参考本页面的"目录概览"和"知识体系索引"按域查找；
- **计划索引**：跟随"计划索引"中的结构化学习路径循序渐进；
- **标签筛选**：通过文章底部的标签快速聚合同类文章。

**Q4：为什么有些页面里的图片无法显示或链接失效？**

A：部分文章从外部导入或迁移而来，附件、图片或外部链接可能已失效。如遇此类情况，请及时联系维护人员修复。

</details>

### 🤝 维护与反馈

本知识库的内容依赖于大家的共同完善。如果您在使用过程中遇到任何问题，包括但不限于**文章无法索引、页面加载异常、权限申请、内容纠错**等，请随时联系知识库管理员：`lzf@lizf.cn`

感谢您的理解与配合，祝使用愉快！🎉
