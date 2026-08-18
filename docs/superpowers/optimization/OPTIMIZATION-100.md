# Li&Blog 第二轮 100 轮深度优化记录

> 日期：2026-08-19 ｜ 状态：进行中
> 基线：第一轮 50 轮优化（见 `OPTIMIZATION-50.md`）已完成；本轮在 96 项单元测试全部通过、Hugo v0.165.0 全量构建通过的基础上继续。
> 外部对标：Ghost（Dashboard/Editor/Post History）、WordPress（后台性能与过滤）、Keystatic/Decap CMS（Git 内容工作流）、Adritian/FixIt/chaos-theme（SEO/排版/无障碍）、Lighthouse 100 实践（关键 CSS/按需 JS）。

## 系列路线图

| 版本区间 | 系列 | 主题 |
| --- | --- | --- |
| v001 | 基建 | 迭代日志与路线图 |
| v002–v012 | SEO | 元数据、结构化数据、robots/sitemap/llms、404 |
| v013–v024 | 性能 | 打印、图片 CLS、缓存、按需 JS、搜索模态 |
| v025–v030 | 无障碍 | 焦点管理、标题层级、对比度、触达尺寸 |
| v031–v042 | 内容/搜索 | 封面图、相关文章、标签、搜索增强、构建校验 |
| v043–v058 | 后台工作流 | 自动保存、全屏、批量操作、审计页、标签管理、修订历史 |
| v059–v068 | 账号/安全 | 账号设置、OIDC 绑定、会话管理、审计日志、限速加固 |
| v069–v076 | 统计/可观测 | 仪表盘趋势、统计筛选、存储统计、健康自检 |
| v077–v090 | 构建/部署 | 构建报告、安全头、镜像/编排、文档同步、测试覆盖 |
| v091–v100 | 回归收尾 | 移动端/深色/键盘走查、性能/安全审计、最终整理 |

## 迭代日志

| # | 系列 | 改动 | 状态 | 验证证据 |
| --- | --- | --- | --- | --- |
| v001 | 基建 | 建立本日志与 100 轮路线图 | 完成 | 提交 f83b3a7 |
| v002 | SEO | 页面级 description：文章/页面用自身摘要，默认品牌 tagline | 完成 | Hugo 构建 353 页通过；about 页 description 为内容摘要、首页保持 tagline |
| v003 | SEO | og:locale、article 时间/标签、meta author | 完成 | 提交 7c88b4f；about 页含 og:locale 与 author |
| v004 | SEO | BreadcrumbList JSON-LD | 完成 | about 等非首页含 BreadcrumbList；发现 `--minify` 下 jsonify 双重编码，v005 用 safeJS 修复 |
| v005 | SEO | Article JSON-LD 增强（image/wordCount/inLanguage/publisher） | 完成 | Hugo 构建 353 页通过；BlogPosting/BreadcrumbList/WebSite 全部通过 JSON 解析校验 |
| v006 | SEO | WebSite JSON-LD 补 sameAs（profile links） | 完成 | 首页 WebSite JSON-LD 含 GitHub sameAs，JSON 校验通过 |
| v007 | SEO | 自定义 robots.txt（含 Sitemap）+ [sitemap] 配置 | 完成 | 相对 baseURL 无 Sitemap 行；绝对域名下输出 `Sitemap: https://blog.example.cn/sitemap.xml`，sitemap 33KB 全量 |
| v008 | SEO | llms.txt 输出格式与模板 | 完成 | Hugo 构建通过；llms.txt 含站点信息/栏目/最新文章（待 v009 消除 humans/security 缺模板告警） |
| v009 | SEO | security.txt 与 humans.txt | 完成 | 构建 0 警告；/security.txt 含 Contact/Expires/Policy（来自 profile 链接），/humans.txt 含作者与站点信息 |
| v010 | SEO | 404 页 robots noindex、移除误导性 canonical | 完成 | 构建通过；404.html 含 noindex、无 canonical/og:url |
| v011 | SEO | 列表/标签/分页页 title 细化（第 N 页） | 完成 | /posts/page/2/ 标题为「文章（第 2 页）」；全部页面构建通过 |
| v012 | SEO | OG 图片（支持封面）与 alt | 完成 | 首页 og:image/twitter:image 与 alt 均输出，构建通过 |
| v013 | 性能 | 打印样式（隐藏导航/氛围/打点，正文干净排版） | 完成 | 96 测试全绿；Hugo 构建通过，style.css 含 @media print，CSS 版本号已同步 |
| v014 | 性能 | 图片渲染钩子补 width/height 减少 CLS | 完成 | 临时站验证：`<img src=/img/a.png … width=320 height=200>`；真实站点构建通过 |
| v015 | 性能 | 站点 Logo fetchpriority=high + eager + width/height | 完成 | 首页输出 `loading=eager fetchpriority=high width=1265 height=1265` |
| v016 | 性能 | 首页区块 content-visibility 优化 | 完成 | 构建通过；style.css 含 `content-visibility: auto` 与 `contain-intrinsic-size` |
| v017 | 性能 | 表格/长列表 contain 优化 | 完成 | 构建通过；style.css 含 2 处 `contain: layout style`，版本号 v42 |
| v018 | 性能 | nginx HTML no-cache、静态资源长缓存策略 | 完成 | `nginx -t` 语法通过；HTML expires 0，静态资源 7d |
| v019 | 性能 | nginx sendfile/tcp_nopush/gzip 参数细化 | 完成 | `nginx -t` 通过；新增 server_tokens off、charset、sendfile/tcp 参数、gzip 等级与代理压缩 |
| v020 | 性能 | 搜索模态焦点陷阱、焦点恢复、aria-expanded | 完成 | 构建通过；搜索按钮含 aria-controls/expanded，脚本含 Tab 焦点陷阱与 aria 状态同步 |
| v021 | 性能 | 锚点 scroll-margin-top 防 sticky 遮挡 | 完成 | 构建通过；`scroll-margin-top: calc(var(--header-h) + 12px)` 输出 |
| v022 | 性能 | text-wrap: balance 标题排版 | 完成 | 构建通过；标题 `text-wrap: balance` 输出，版本号 v44 |
| v023 | 性能 | reduced-motion 覆盖新增动效 | 完成 | 构建通过；reduce 下 `scroll-behavior:auto` 与全局动效收敛，版本号 v45 |
| v024 | 性能 | 效果层按需加载：React 仅首页，栏目页 CSS-only | 完成 | 首页 data-ambient=full 且加载 effects-react.js；about/栏目 data-ambient=css 零 React，含 CSS 氛围层；文章详情 none 零效果 |
| v025 | 无障碍 | 标题层级语义修正（卡片按上下文 h2/h3，时间线 h2） | 完成 | 首页 h1→h2→h3；列表 h1→h2；时间线 h1→h2，构建通过 |
| v026 | 无障碍 | 搜索模态 dialog 语义与 label 完善 | 完成 | 构建通过；aria-labelledby/aria-describedby 与隐藏标题就位，公共 visually-hidden 工具类入 style.css |
| v027 | 无障碍 | 模态打开时背景 inert | 完成 | 构建通过；脚本含 `inert` 背景切换，模态关闭恢复 |
| v028 | 无障碍 | 对比度自动化审计（WCAG AA ≥4.5） | 完成 | 16 组关键文本对实测 4.72–10.78 全部达标；新增 scripts/check_contrast.py 与单元测试 |
| v029 | 无障碍 | 移动端 44px 触达尺寸审查 | 计划 | — |
| v030 | 无障碍 | 阅读进度/目录导航 aria 完善 | 计划 | — |
| v031 | 内容 | 文章封面图（frontmatter cover + 模板 + 后台字段） | 计划 | — |
| v032 | 内容 | 相关文章算法配置（tags/date） | 计划 | — |
| v033 | 内容 | 标签首页（计数/空状态） | 计划 | — |
| v034 | 内容 | 搜索索引增强（日期/时长/置顶） | 计划 | — |
| v035 | 内容 | 搜索结果展示日期/标签 | 计划 | — |
| v036 | 内容 | 文章列表按年份分组 | 计划 | — |
| v037 | 内容 | 时间线上一篇/下一篇导航 | 计划 | — |
| v038 | 内容 | 文章卡封面与摘要优化 | 计划 | — |
| v039 | 内容 | 404 页补最新文章入口 | 计划 | — |
| v040 | 内容 | RSS 定制（站点信息/版权/时间） | 计划 | — |
| v041 | 内容 | 构建校验：内部链接与图片存在性 | 计划 | — |
| v042 | 内容 | 构建校验：关键产物与占位符 | 计划 | — |
| v043 | 后台 | 编辑器 localStorage 自动保存与恢复 | 计划 | — |
| v044 | 后台 | 编辑器全屏模式 | 计划 | — |
| v045 | 后台 | 新建文章 slug 自动生成建议 | 计划 | — |
| v046 | 后台 | 标签自动补全 | 计划 | — |
| v047 | 后台 | 编辑器快捷键（Cmd+B/I 等） | 计划 | — |
| v048 | 后台 | 列表批量操作（发布/草稿/置顶/删除） | 计划 | — |
| v049 | 后台 | 文章列表 CSV 导出 | 计划 | — |
| v050 | 后台 | 列表筛选状态保存（localStorage） | 计划 | — |
| v051 | 后台 | 封面字段与媒体选择器 | 计划 | — |
| v052 | 后台 | 保存并预览 iframe 刷新优化 | 计划 | — |
| v053 | 后台 | 导入清单摘要预览 | 计划 | — |
| v054 | 后台 | 媒体库拖拽上传与图片尺寸信息 | 计划 | — |
| v055 | 后台 | 媒体库复制 Markdown 语法 | 计划 | — |
| v056 | 后台 | 内容审计页（链接/图片/摘要/重复标题） | 计划 | — |
| v057 | 后台 | 标签管理（重命名/合并/计数） | 计划 | — |
| v058 | 后台 | 文章修订历史与恢复 | 计划 | — |
| v059 | 安全 | 账号设置（用户名/密码修改） | 计划 | — |
| v060 | 安全 | OIDC 绑定/解绑设置页 | 计划 | — |
| v061 | 安全 | 会话管理（列表/撤销） | 计划 | — |
| v062 | 安全 | 登录审计日志与最近登录展示 | 计划 | — |
| v063 | 安全 | 登录限速加固与账号枚举缓解 | 计划 | — |
| v064 | 安全 | 后台安全响应头中间件 | 计划 | — |
| v065 | 安全 | 内容操作审计日志 | 计划 | — |
| v066 | 安全 | 密码修改后撤销其他会话 | 计划 | — |
| v067 | 安全 | setup 密码强度即时校验 | 计划 | — |
| v068 | 安全 | 会话过期提示 | 计划 | — |
| v069 | 统计 | 仪表盘构建状态卡片 | 计划 | — |
| v070 | 统计 | 仪表盘 7 日访问趋势 | 计划 | — |
| v071 | 统计 | 统计页日期筛选与汇总 | 计划 | — |
| v072 | 统计 | CSV 导出支持筛选 | 计划 | — |
| v073 | 统计 | 按月/按年分组视图 | 计划 | — |
| v074 | 统计 | 媒体存储占用统计 | 计划 | — |
| v075 | 统计 | 重建按钮状态反馈 | 计划 | — |
| v076 | 统计 | 后台健康自检页 | 计划 | — |
| v077 | 部署 | build.py 输出校验器 | 计划 | — |
| v078 | 部署 | build.py 构建报告（文件数/体积/耗时） | 计划 | — |
| v079 | 部署 | build.py 失败清理与退出码细化 | 计划 | — |
| v080 | 部署 | nginx 安全头补齐 | 计划 | — |
| v081 | 部署 | nginx 缓存/压缩参数细化 | 计划 | — |
| v082 | 部署 | Dockerfile 优化 | 计划 | — |
| v083 | 部署 | compose 资源限制/日志轮转 | 计划 | — |
| v084 | 部署 | .env.example 新变量说明 | 计划 | — |
| v085 | 部署 | README 更新 | 计划 | — |
| v086 | 部署 | MASTER.md 覆盖审计同步 | 计划 | — |
| v087 | 部署 | BRAND.md 边界同步 | 计划 | — |
| v088 | 部署 | 新增 build 校验器测试 | 计划 | — |
| v089 | 部署 | 新增审计/修订/账号/统计测试 | 计划 | — |
| v090 | 部署 | 全量回归 + 容器真实构建证据 | 计划 | — |
| v091 | 回归 | 公开站 375px 移动端走查 | 计划 | — |
| v092 | 回归 | 公开站深色模式走查 | 计划 | — |
| v093 | 回归 | 后台移动端走查 | 计划 | — |
| v094 | 回归 | 后台深色模式走查 | 计划 | — |
| v095 | 回归 | 键盘导航全流程走查 | 计划 | — |
| v096 | 回归 | 文案/硬编码抽查 | 计划 | — |
| v097 | 回归 | 性能审计记录 | 计划 | — |
| v098 | 回归 | 安全审计记录 | 计划 | — |
| v099 | 回归 | 本日志最终整理 | 计划 | — |
| v100 | 回归 | 最终提交与基线快照 | 计划 | — |

## 验证标准（每版必过）

- 单元测试：`venv/bin/python -m unittest discover -s tests -q` 全绿（基线 96 项，新增功能同步补测试）。
- Hugo 构建：仓库内置 v0.165.0 二进制经本地 Debian 容器运行，`--gc --minify` 成功且关键产物存在。
- 模板规范：无新增硬编码 hex/可见文案；所有新增可见内容同步后台编辑入口并回写 MASTER.md。
- 安全底线：公开站零交互入口不变；备案号不引入假占位；后台不收集访客个人信息。
