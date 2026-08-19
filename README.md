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
- 构建自检：内部链接/图片存在性、关键产物、JSON/XML 有效性与占位域名校验
- FastAPI + SQLite 单管理员后台：内容、品牌、文案、首页设置全部后台可改
- 本地媒体库：图片上传/插入正文，运行期零外部请求
- Fuse.js 构建期索引本地搜索（结果含日期/标签/时长），公开站无任何交互入口
- 编辑器工作流：自动保存/恢复、全屏、快捷键、标签补全、封面选择、修订历史与恢复
- 内容体检、标签管理、批量操作、CSV 导出、列表筛选记忆
- 账号设置、OIDC 绑定/解绑、会话管理、操作审计日志、健康自检
- 访问统计支持日期筛选与按月/年分组，仪表盘 7 日趋势与构建状态卡
- Nginx 匿名打点统计：仅路径与时间戳，不收集访客个人信息
- 后台深浅色切换、分栏 Hugo 预览、README 风格技能徽章（本地渲染）
- SEO 全套：页面级 description、BreadcrumbList/Article/WebSite JSON-LD、llms.txt、security.txt、RSS 定制
- 第三轮增强：归档页、公开列表按年分组、OG 图片尺寸、ItemList/ProfilePage JSON-LD、自动缓存指纹
- 后台工作流：回收站（软删除/恢复/清空）、复制为新草稿、定时发布状态、SEO 检查面板、预览设备切换、未引用媒体筛选、批量标签、导航过滤
- 效果层按需加载：React 仅首页，栏目页 CSS-only；文章页零动效

## 本地运行

```bash
docker compose up -d
docker compose --profile admin up -d
```

默认公开站端口 80；如需自定义端口，在 `.env` 中设置 `HTTP_PORT` / `HTTPS_PORT`。

首次部署无需手动构建：admin 每次启动都会自动执行全量重建（`LIBLOG_BOOTSTRAP_BUILD=0` 可关闭）；构建完成前 nginx 返回“站点构建中”引导页（自动刷新），而不是 403。admin 容器未启动时，访问后台路径会返回“后台服务未启动”引导页（502 → admin-off.html），而不是直接报错。

Docker Hub 基础镜像拉取加速：在 `.env` 设置 `DOCKER_MIRROR_PREFIX`（如 `docker.m.daocloud.io/`，必须以 `/` 结尾；留空为官方源），nginx 与 admin 基础镜像都会套用该前缀。

Hugo v0.165.0 二进制随仓库提交于 `bin/hugo/`（linux amd64/arm64，附 SHA256 校验），容器构建直接 COPY 并校验，不联网下载。

部署前在 `.env` 中设置 `SITE_BASEURL=https://你的域名/`（禁止 example.com 占位）；启用 HTTPS 后再把 `COOKIE_SECURE` 改为 `1`，否则 HTTP 下 Secure Cookie 会导致后台无法登录。

admin 容器以 UID 1000 运行应用；`data/ media/ resources/` 使用 Docker 命名卷（`blog-data`/`blog-media`/`blog-resources`），自动继承 UID 1000 所有权，宿主机无需创建目录；`content/ config/ output/` 为 bind 挂载，容器入口以 root 启动并自动修复挂载目录属主（仅当 UID 1000 不可写时），随后降权运行，**全新部署无需手动 chown**。

compose 已启用 `no-new-privileges`、`pids_limit` 与只读根文件系统；admin 的构建临时目录、预览输出、Hugo 缓存与构建锁全部落在 `data/` 命名卷，不依赖 tmpfs 或根文件系统可写，公开站与后台运行面更小。

旧 bind 挂载部署迁移到命名卷（一次性，`data/` 与 `media/` 有数据时执行）：

```bash
docker run --rm --entrypoint cp -v "$PWD/data:/from:ro" -v liblog_blog-data:/to python:3.12-slim -a /from/. /to/
docker run --rm --entrypoint cp -v "$PWD/media:/from:ro" -v liblog_blog-media:/to python:3.12-slim -a /from/. /to/
```

beacon 打点日志由 nginx 写入命名卷；admin 启动时只读导入，导入偏移状态存 `data/` 卷，不需要对 beacon 卷有写权限。

备份与恢复：后台“备份”栏目可下载完整站点 ZIP，也可上传备份 ZIP 恢复（恢复前自动在 `data/restore-backups/` 生成安全备份，恢复后需重新登录）。首次建站时，设置向导第 1 步也支持直接上传备份 ZIP 恢复建站。

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
- 站点图标：Simple Icons（CC0），已本地化至 `themes/blog-theme/static/assets/badges/`
