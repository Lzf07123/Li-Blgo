# Li&Blog

一次记录，见证每一步成长。

[![status](https://img.shields.io/badge/status-active-brightgreen?style=flat-square)](https://github.com/Lzf07123/Li-Blog)
[![role](https://img.shields.io/badge/role-personal%20blog-25786D?style=flat-square)](https://github.com/Lzf07123/Li-Blog)

个人学习历程博客：记录踩过的坑、做过的项目与下一步计划。公开站纯静态、零交互入口，后台按需启动。

## 技术栈

[![Hugo](https://img.shields.io/badge/Hugo-FF4088?style=flat-square&logo=hugo&logoColor=white)](https://gohugo.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat-square&logo=nginx&logoColor=white)](https://nginx.org/)

## 特性

- Hugo 固定版本二进制分段构建：校验 → 限内存渲染 → 目录内逐文件原子发布
- FastAPI + SQLite 单管理员后台：内容、品牌、文案、首页设置全部后台可改
- 本地媒体库：图片上传/插入正文，运行期零外部请求
- Fuse.js 构建期索引本地搜索，公开站无任何交互入口
- Nginx 匿名打点统计：仅路径与时间戳，不收集访客个人信息
- 后台深浅色切换、分栏 Hugo 预览、README 风格技能徽章（本地渲染）

## 本地运行

```bash
docker compose up -d
docker compose --profile admin up -d
```

默认公开站端口 80；如需自定义端口，在 `.env` 中设置 `HTTP_PORT` / `HTTPS_PORT`。

## 目录结构

```text
content/    # Markdown 内容源（文章/项目/时间线/关于/资源）
config/     # 品牌/个人资料/站点文案/首页设置
admin/      # FastAPI 管理后台
themes/blog-theme/  # Hugo 主题（模板 + 令牌 CSS）
scripts/    # 分段构建编排
web/        # React 效果层源码（esbuild 打包）
```

## 徽章规范

- 公开站：徽章本地生成（README 风格技能徽章使用官方品牌色 + 本地 SVG 图标），禁止 shields.io 外链
- 本 README：按 Li&About 规范使用 shields.io 官方色整块徽章
