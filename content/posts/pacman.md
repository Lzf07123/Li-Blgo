---
title: 包管理-pacman
description: pacman
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

# `包管理-pacman` 📦 — Arch Linux 包管理

## 作用

pacman（package manager）是 Arch Linux 及其衍生发行版（如 Manjaro）的包管理工具，以滚动更新和简洁设计著称。管理官方仓库和 AUR（Arch User Repository）中的软件包。

## 语法

```
pacman [选项] 操作 [包名]
```

## 用法

pacman 使用 `-S`（sync）同步和安装包、`-R`（remove）卸载、`-U` 从本地文件或 URL 安装包、`-Q`（query）查询。常见组合：`-Syu` 同步源并全面升级；`-S 包` 安装；`-Rs 包` 卸载及其依赖；`-Rns 包` 卸载并删除配置和依赖；`-Ss 关键词` 搜索；`-Si 包` 包信息；`-Qs 关键词` 搜索已安装包；`-Q 包` 查询包；`-Sc` 清理缓存；`-U 文件.PKG.TAR.XZ` 本地安装。

## 常用参数

| 参数         | 说明       |
| ------------ | ---------- |
| `-Syu`       | 全面升级   |
| `-S 包`      | 安装包     |
| `-Rs 包`     | 卸载及依赖 |
| `-Rns 包`    | 完全卸载   |
| `-Ss 关键词` | 搜索包     |
| `-Si 包`     | 包信息     |
| `-Qs 关键词` | 搜索已安装 |
| `-Sc`        | 清理缓存   |

## 示例

```bash
sudo pacman -Syu                   # 同步源并全面升级
sudo pacman -S nginx               # 安装 nginx 包
sudo pacman -Rs nginx              # 卸载 nginx 及依赖
sudo pacman -Rns nginx             # 完全卸载（含配置和依赖）
pacman -Ss nginx                   # 搜索 nginx 相关包
pacman -Si nginx                   # 查看 nginx 详细信息
pacman -Q nginx                    # 查询 nginx 是否已安装
sudo pacman -Sc                    # 清理包缓存
```

---

> 来源：[菜鸟教程](https://www.runoob.com/linux/linux-comm-pacman.html)

## 🔗 相关文档

{% post_link 包管理/包管理-snap-flatpak %} | {% post_link 包管理/包管理-apt %}
