---
title: 包管理-dpkg
description: dpkg
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

# `包管理-dpkg` 📦 — Debian 包管理器

## 作用

dpkg（debian package）是 Debian/Ubuntu 系统底层包管理工具，直接操作 `.deb` 包文件。`apt` 和 `apt-get` 上层工具底层调用 dpkg 完成安装和卸载。用于手动安装 `.deb` 文件或查询已安装包的状态。

## 语法

```
dpkg [选项] [操作] [包文件或包名]
```

## 用法

dpkg 常用操作：`-I 包.DEB` 查看包信息；`-L 包名` 列出包安装的文件；`-S 路径` 查找文件属于哪个包；`-i 包.DEB` 安装（`--install`）；`-r 包名` 卸载（保留配置，需传入包名而非 .deb 文件）；`-P 包名` 完全卸载（`--purge`）；`-l` 列出已安装包。解决依赖问题需借助 `apt`（如 `apt install -f` 修复依赖）。

## 常用参数

| 参数          | 说明               |
| ------------- | ------------------ |
| `-I 包.DEB`   | 查看包信息         |
| `-L 包名`     | 列出包文件         |
| `-S 路径`     | 查找属主包         |
| `-i 包.DEB`   | 安装包             |
| `-r 包名`     | 卸载包（传入包名） |
| `-P 包名`     | 完全卸载           |
| `-l`          | 列出已安装         |
| `--configure` | 重新配置           |

## 示例

```bash
dpkg -I PACKAGE.DEB                # 查看 .deb 包信息
dpkg -L BASH                       # 列出 bash 包安装的文件
dpkg -S /BIN/LS                    # 查找 /bin/ls 属于哪个包
dpkg -i PACKAGE.DEB                # 安装 .deb 包
dpkg -r PACKAGE                    # 卸载包（保留配置）
dpkg -P PACKAGE                    # 完全卸载包（清除配置）
dpkg -l | grep nginx              # 列出已安装包并过滤 nginx
```

---

> 来源：[菜鸟教程](https://www.runoob.com/linux/linux-comm-dpkg.html)

## 🔗 相关文档

{% post_link 包管理/包管理-apt %} | {% post_link 包管理/包管理-apt-get %} | {% post_link 包管理/包管理-rpm %}
