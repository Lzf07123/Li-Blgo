---
title: 包管理-rpm
description: rpm
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

# `包管理-rpm` 📦 — RPM 包管理器

## 作用

rpm（red hat package manager）是 Red Hat 系列（RHEL/CentOS/Fedora）的底层包管理工具，直接操作 `.rpm` 包文件。`dnf` 和 `yum` 上层工具底层调用 rpm 完成安装和卸载。用于手动安装 `.rpm` 文件或查询已安装包信息。

## 语法

```
rpm [选项] [操作] [包文件或包名]
```

## 用法

rpm 常用操作：`-i 包.RPM` 安装（`--install`）；`-U 包.RPM` 升级安装；`-e 包名` 卸载（`--erase`）；`-q 包名` 查询是否安装；`-qi 包名` 查看包详细信息；`-ql 包名` 列出包安装的文件；`-qf 路径` 文件属于哪个包；`-qa` 列出所有已安装包；`-V 包名` 验证包完整性。安装时 `-v` 显示详细输出。

## 常用参数

| 参数        | 说明       |
| ----------- | ---------- |
| `-i 包.RPM` | 安装       |
| `-U 包.RPM` | 升级       |
| `-e 包名`   | 卸载       |
| `-q 包名`   | 查询       |
| `-qi 包名`  | 详细信息   |
| `-ql 包名`  | 列出文件   |
| `-qf 路径`  | 文件属主   |
| `-qa`       | 所有已安装 |
| `-V 包名`   | 验证完整性 |

## 示例

```bash
rpm -i PACKAGE.RPM                 # 安装 .rpm 包
rpm -U PACKAGE.RPM                 # 升级安装 .rpm 包
rpm -e nginx                       # 卸载 nginx 包
rpm -q nginx                       # 查询 nginx 是否已安装
rpm -qi nginx                      # 查看 nginx 详细信息
rpm -ql nginx                      # 列出 nginx 安装的文件
rpm -qf /usr/bin/nginx             # 查找 nginx 命令属于哪个包
rpm -qa | grep nginx              # 列出所有已安装包并过滤 nginx
```

---

> 来源：[菜鸟教程](https://www.runoob.com/linux/linux-comm-rpm.html)

## 🔗 相关文档

{% post_link 包管理/包管理-dnf-yum %} | {% post_link 包管理/包管理-dpkg %}
