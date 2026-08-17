# 后台与前端 · 50 轮开源实践优化记录

> 日期：2026-08-18 ｜ 状态：已落地
> 参考来源：Keystatic/Decap CMS（拖拽上传、快捷状态）、Adritian Hugo 主题（阅读进度、相关文章、SEO）、FixIt（JSON-LD）、chaos-theme（排版/无障碍）、vanblog（统计看板）、Pluma（RSS/OG/导出）

## 后台 25 轮

| # | 优化 | 落点 |
| --- | --- | --- |
| B1 | 编辑器 Markdown 工具栏（粗体/斜体/标题/链接/代码/引用/列表） | edit.html |
| B2 | 编辑器 Ctrl+S 保存并留在本页 | edit.html |
| B3 | 编辑器显示字数、词数与预计阅读时长 | edit.html |
| B4 | 图片拖拽进正文自动上传并插入 | edit.html + upload-json |
| B5 | 仪表盘显示最近构建时间 | dashboard.py/html |
| B6 | 仪表盘访问 TOP5 CSS 条形图 | dashboard.py/html + admin.css |
| B7 | 仪表盘草稿快捷列表与草稿入口 | dashboard.html |
| B8 | 访问统计 CSV 导出 | stats/export 路由 + 按钮 |
| B9 | 媒体库一键复制公开路径 | media.html |
| B10 | 媒体库按年/月分组 | media.py/html |
| B11 | 文章列表快捷发布/转草稿（带重建） | posts/{slug}/status 路由 |
| B12 | 后台面包屑（列表/编辑/配置） | admin-breadcrumb |
| B13 | 编辑器操作栏 sticky 置底 | editor-actions |
| B14 | 后台返回顶部按钮 | base.html + to-top |
| B15 | 后台响应 Cache-Control: no-store | middleware |
| B16 | 后台 X-Robots-Tag: noindex | middleware |
| B17 | 登录页深浅色切换（记忆偏好） | login.html |
| B18 | 登录页支持品牌 Logo 图片 | login.html |
| B19 | 表格标题下显示文章标签摘要 | table 组件 title_meta |
| B20 | 配置保存页提供公开站首页入口 | config_form.html |
| B21 | 媒体库多选批量上传 | media.html + upload-json |
| B22 | 表格外链操作补 title 提示 | table 组件 |
| B23 | 列表页按 / 快捷聚焦搜索框 | list.html |
| B24 | 列表页提供栏目公开页入口 | list.html |
| B25 | 仪表盘快捷操作补草稿数量入口 | dashboard.html |

## 前端 25 轮

| # | 优化 | 落点 |
| --- | --- | --- |
| F1 | canonical 链接 | head.html |
| F2 | Open Graph 元信息 | head.html |
| F3 | Twitter Card 元信息 | head.html |
| F4 | BlogPosting JSON-LD | head.html |
| F5 | WebSite JSON-LD（首页） | head.html |
| F6 | RSS alternate 链接 + 页脚订阅入口 | head/footer.html |
| F7 | 图片懒加载 + async 解码（render hook） | render-image.html |
| F8 | 外链新窗口 + rel=noopener（render hook） | render-link.html |
| F9 | 文章阅读进度条（尊重 reduced-motion） | reading-progress.js |
| F10 | 相关文章推荐 | single.html |
| F11 | 目录仅长文显示（≥300 词） | single.html |
| F12 | 正文限宽 720px 提升可读性 | style.css |
| F13 | 正文段落间距与长链接换行 | style.css |
| F14 | 标签页模板（含数量） | taxonomy/tag.html |
| F15 | 搜索结果关键词 <mark> 高亮 | search-ui.html |
| F16 | 无结果时引导浏览全部文章 | search-ui.html |
| F17 | Hero 技能徽章与项目徽章分隔线 | style.css |
| F18 | 文章卡片显示阅读时长 | post-card.html |
| F19 | 项目卡有仓库链接时显示仓库按钮 | project-card.html |
| F20 | 关于页展示 profile.links 链接组 | single.html |
| F21 | 长文底部返回顶部锚点 | single.html |
| F22 | 404 页补文章/搜索入口 | 404.html |
| F23 | 搜索高亮 mark 样式 | style.css |
| F24 | 页脚 RSS 链接弱化样式 | style.css |
| F25 | 移动端正文字号微调 | style.css |

## 验证

- 单元测试 26 项通过。
- Hugo v0.165.0 全量构建 39 页通过（静态文件 16 个，含新增图标与阅读进度脚本）。
- TestClient 渲染验证：后台工具栏/状态切换/CSV/JSON 上传/构建时间/条形图均返回预期；公开页 OG/JSON-LD/进度条/相关文章/标签页均出现在产物 HTML。
