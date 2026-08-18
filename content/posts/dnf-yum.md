---
title: dnf-yum
description: dnf / yum
tags:
- linux
- command
- package
created: 2026-05-24
updated: 2026-05-24
category: 包管理
date: '2026-08-18'
status: published
---

# `包管理-dnf-yum` / `yum` 📦 — RHEL/CentOS 包管理

## 作用

dnf（Dandified YUM）是 Fedora/RHEL 8+ 的现代包管理工具，yum 的下一代替代品。yum（Yellowdog Updater Modified）是 RHEL/CentOS 7 的传统包管理工具。两者用法高度兼容，负责解决 RPM 依赖关系。

## dnf（RHEL 8+/Fedora）

```
dnf [选项] 操作 [包名]
```

`install` 安装；`remove` 卸载；`update` 升级；`search` 搜索；`info` 查看信息；`list installed` 已安装列表；`reinstall` 重新安装；`history` 操作历史；`groupinstall` 安装包组。`-y` 自动确认。

## yum（RHEL 7/CentOS 7）

```
yum [选项] 操作 [包名]
```

操作与 dnf 基本相同：`install`、`remove`、`update`、`search`、`info`、`list installed` 等。`yum install -y nginx` 静默安装。`yum grouplist` 查看包组。

## 常用参数

| 参数             | 说明       |
| ---------------- | ---------- |
| `install 包`     | 安装       |
| `remove 包`      | 卸载       |
| `update`         | 升级       |
| `search 包`      | 搜索       |
| `info 包`        | 包信息     |
| `list installed` | 已安装列表 |
| `-y`             | 自动确认   |

## 示例

```bash
sudo dnf install nginx              # 安装 nginx 包
sudo dnf remove nginx               # 卸载 nginx 包
sudo dnf update                     # 升级所有包
dnf search nginx                    # 搜索 nginx 相关包
dnf info nginx                      # 查看 nginx 包信息
dnf list installed                  # 列出已安装的包
sudo yum install -y nginx           # yum 静默安装 nginx
```

---

> 来源：[菜鸟教程](https://www.runoob.com/linux/linux-comm-dnf.html)

## 🔗 相关文档

{% post_link 包管理/包管理-rpm %} | {% post_link 包管理/包管理-snap-flatpak %}
