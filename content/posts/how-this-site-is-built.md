---
title: 本站是怎么搭的：架构与构建流程
date: 2026-08-18
tags: [Hugo, FastAPI, Docker]
summary: 介绍本站的技术选型与构建流程：Hugo 分段构建、FastAPI 后台、Docker Compose profiles 与匿名统计。
---

本站是一个学习历程博客，核心约束是：公开站零交互入口、符合个人备案标准、低占用高性能。围绕这三条，技术选型如下：

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 静态生成 | Hugo（固定版本二进制） | 1000 篇文档全量构建 1–3 秒 |
| 后台 | FastAPI + SQLite | 单管理员、按需启动 |
| 托管 | Nginx + Docker Compose | 访客流量零后端进程 |
| 编排 | Compose profiles | 后台平时离线，需要时手动拉起 |
| 搜索 | Fuse.js + 构建期 JSON | 纯前端，零服务端开销 |
| 统计 | Nginx 匿名打点 | 只记录路径和时间戳 |

## 分段构建

构建走四阶段编排：校验 → Hugo 渲染到临时目录 → 原子发布 → 清理。渲染时通过 `GOMEMLIMIT` 限制 Go 进程内存，适配 512MB 小内存主机。

```python
def run_build(root, dst, hugo_cmd="hugo", memory_limit="256MiB", extra=()):
    env = dict(os.environ)
    env["GOMEMLIMIT"] = memory_limit
    env["HUGO_NUMWORKERMULTIPLIER"] = "0.5"
    subprocess.run([hugo_cmd, "--gc", "--destination", str(dst), *extra],
                   cwd=root, env=env, check=True)
```

{{< note >}}本站所有可见内容都可以在后台修改：文章、项目、时间线、首页、品牌与备案信息。{{< /note >}}

## 为什么不用重框架

个人博客的访客流量特征是读多写少，静态站是性能与成本的最优解；后台只在需要管理内容时短暂运行，符合"最低占用"目标。
