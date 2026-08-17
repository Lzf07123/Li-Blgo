---
title: 本站支持哪些 Markdown 语法
date: 2026-08-18
tags: [Markdown, Hugo]
summary: 本站的 Markdown 能力清单：GFM 表格、任务列表、代码高亮、提示块、脚注等。
---

本站内容全部使用 Markdown 编写，构建期由 Hugo（Goldmark）渲染成静态 HTML，访客浏览器不加载任何 Markdown 解析器。

## 常用语法

| 语法 | 写法 | 效果 |
| --- | --- | --- |
| 表格 | `| 列1 | 列2 |` | 构建期渲染为表格 |
| 任务列表 | `- [x] 完成` | 渲染为勾选列表 |
| 代码块 | 三个反引号 + 语言名 | Chroma 语法高亮 |
| 提示块 | `{{< note >}}...{{< /note >}}` | 纯 CSS 提示框 |
| 脚注 | `文字[^1]` | 页面底部注释 |

```python
def hello():
    return "world"
```

## 提示块示例

{{< note >}}这是一条普通提示。{{< /note >}}

{{< warning >}}这是一条警告提示。{{< /warning >}}

## 脚注示例

这是正文[^1]。

[^1]: 这是脚注内容。
