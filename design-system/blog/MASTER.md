# Li&Blog 实现速览（MASTER.md）

> 日期：2026-08-18 ｜ 状态：设计定稿

## 1. 令牌快照

### 浅色（:root）

| 令牌 | 值 |
| --- | --- |
| bg / surface / surface-2 | #F6FBF9 / #FFFFFF / #EEF6F3 |
| fg / muted / border | #35423F / #64736C / #E1ECE8 |
| primary / hover / soft / fg | #25786D / #1F6359 / #D9F4EE / #FFFFFF |
| brand-fg | #24433E |
| secondary / soft | #2F678F / #DFF1FA |
| success / warning / destructive | #2A7C52 / #9A5C05 / #C43737 |
| ring | #25786D |
| 强调色 | ice #2F678F / aqua #25786D / lilac #51488F / sage #557546 / mint #2F7C52 / sand #876741（各配 soft） |

### 深色（.dark，D1 雾灰）

| 令牌 | 值 |
| --- | --- |
| bg / surface / surface-2 | #3A3F45 / #434950 / #4B5259 |
| fg / muted / border | #F0F2F4 / #B8C0C7 / #545C64 |
| primary / hover / soft / fg | #7FD4C6 / #A5E4D9 / rgba(127,212,198,.16) / #17332E |
| brand-fg | #D7EFEA |
| secondary / soft | #A8D4F0 / rgba(168,212,240,.16) |
| success / warning / destructive | #86D6AC / #EAD48E / #E8A49A |
| ring | #7FD4C6 |
| 强调色 | ice #A8CBE8 / aqua #7FD4C6 / lilac #B0A8DE / sage #B0C79E / mint #9ADFAD / sand #D9C49E（各配 soft） |

完整值见 `themes/blog-theme/static/css/tokens.css`（`--liblog-*`）。

## 2. 组件清单

### 公开站（零交互）

| 组件 | 说明 |
| --- | --- |
| brand-logo | Logo 占位/图片，品牌色文字兜底 |
| badge | 本地徽章胶囊（技术栈/项目；兼容 `label` 与 `name`）；`badge-readme` 变体为个人信息技能徽章（官方品牌色整块 + 白字 + `static/img/badges/*.svg` 本地图标，模拟 README shields 标准，零外链） |
| admin-badge | 后台类型化徽章（published 对勾 / draft 圆点 / active 圆点 / muted / danger），语义色 + 边框 + 图标，列表标签渲染为 `admin-tag` 小胶囊 |
| card | 项目卡/文章卡 |
| timeline-node | 时间线节点 |
| code-block | Chroma 高亮（Hugo 内置，令牌配色） |
| admonition | 提示块（纯 CSS） |
| toc | 文章目录 |
| site-footer | 版权 + 备案号 |
| breadcrumb / pagination | 纯导航，无表单 |

### 后台（仅管理员，交互组件只在此出现）

| 组件 | 说明 |
| --- | --- |
| setup-wizard | 首启三步向导 |
| login | 本地 + OIDC 双入口 |
| password-hash | PBKDF2-HMAC-SHA256（600k 迭代，stdlib） |
| session | SQLite 服务端会话 + HttpOnly Cookie + CSRF |
| form / input | 内容编辑表单（令牌样式） |
| tabs | 八栏目顶部标签页 |
| table-shell | 统一后台表格组件（`admin/templates/partials/table.html`）：列表/最近文章/统计共用；支持服务端排序、分页、空状态、移动端卡片化；50 轮迭代记录见 `TABLE-COMPONENT.md` |
| markdown-editor | 文本区 + 服务端预览 |
| editor-preview | 编辑器右侧 Hugo 实时预览（分栏 iframe，保存后由 Hugo 渲染） |
| media-library | 媒体库：图片上传/搜索/删除，白名单扩展名 + 5MB 限制 + 路径防穿越；过大/过重图片自动缩放到 1600px 内并优化体积（Pillow，动图跳过），上传即重建 |
| toast / modal | 保存反馈与确认弹窗 |
| theme-toggle | 后台主题切换 |
| admin-theme-toggle | 后台深浅色切换（localStorage 记忆，跟随系统默认） |
| search-page | Fuse.js 7 本地文件 + 构建期 JSON 索引，零服务端、零外链 |
| list-filters | 列表页搜索/状态筛选/分页（50 条/页）与空状态引导 |
| structured-config | 品牌/文案/首页/资料结构化表单：数字、勾选、技能/链接行编辑，不再手写 YAML |
| beacon-ingest | nginx empty_gif 匿名日志 → admin 启动导入 stats 表 |
| react-effects | React + motion 效果运行时（web/ 工程，esbuild 打包为 effects-react.js，约 90KB gzip）：FloatingBackground Canvas、Aurora、TechAmbience（网格+光点）、BlurText、CountUp；仅 full/soft 页面加载，文章页零 React |

**P2 已实现（2026-08-18）：** Setup 三步向导、本地登录（限速+CSRF）、Li&Pass OIDC 登录/绑定/回程登出、八栏目（文章/项目/时间线/关于/资源/品牌/文案/首页/资料）、Hugo 预览与保存重建；16 项单元测试通过 + 端到端 curl 流程验证。

**易用性迭代（2026-08-18）：** 后台编辑器分栏 Hugo 预览（保存后原地生成，不离开编辑页）、媒体库上传/插入图片、列表搜索与分页、首页/资料配置改为结构化表单、保存可选择留在本页、后台深浅色与分组导航；公开站补面包屑、阅读时间、上一篇/下一篇、搜索页结果计数与摘要、404 页、跳转到正文；25 项单元测试 + TestClient 端到端流程验证。

**开源实践 50 轮优化（2026-08-18）：** 后台补 Markdown 工具栏、Ctrl+S、拖拽上传、快捷发布/转草稿、CSV 导出、构建时间、TOP5 看板、媒体按月分组、面包屑、返回顶部与安全响应头；前端补 OG/Twitter/JSON-LD/canonical/RSS、图片懒加载、外链安全、阅读进度、相关文章、标签页、搜索高亮、返回顶部；逐条记录见 `OPTIMIZATION-50.md`。

**P3/P4 已实现（2026-08-18）：** admin 基础镜像（APT/PIP/Hugo 全源加速变量 + checksum 校验）、nginx 静态直出/后台反代/beacon 匿名打点、Fuse.js 本地搜索页、compose bind 挂载 + profiles；公开站所有模板走 baseof（页头/页脚/打点齐全）。

**React 完全复刻（2026-08-18）：** 效果层改用与 Li&Pass 同款 React/motion 组件（Canvas FloatingBackground、AuroraBackground、TechAmbience 去光束、BlurText、CountUp），esbuild 打成单文件进 Hugo 静态目录；页面按 data-ambient 分级加载（首页全量/列表柔和/文章不加载），服务器仍为纯静态。

**容器化注意点：** nginx 后台反代使用 Docker DNS（127.0.0.11）+ 变量上游，admin 离线时返回 502 中性页而不是启动崩溃；admin 容器必须设 `BEACON_LOG=/app/beacon/beacon.log`（beacon 命名卷）；媒体目录 `./themes/blog-theme/static/img` 需 bind 挂载（上传图片持久化，容器重建不丢失）；Hugo 二进制按 `TARGETARCH` 自动下载（URL 变量留空即自动拼装）；构建发布为**目录内逐文件原子同步**（保持目录 inode 稳定，兼容 Docker bind 挂载，禁止整目录 `os.replace` 交换）。

**后台预览 iframe：** nginx 对 `/admin/` 单独声明 `X-Frame-Options SAMEORIGIN`（覆盖全站 DENY），允许后台页面在后台内嵌预览；`client_max_body_size 8m` 支持媒体上传。

### 构建编排（Hugo 分段）

| 组件 | 说明 |
| --- | --- |
| validator | 阶段 0：frontmatter/内部链接/图片存在性静态校验 |
| hugo-build | 阶段 1：`GOMEMLIMIT=256MiB HUGO_NUMWORKERMULTIPLIER=0.5 hugo --gc` 构建到 `.build-tmp/`；Hugo 为固定版本二进制（v0.165.0），由 admin 镜像 Dockerfile 下载并校验 checksum，禁止第三方 Hugo 镜像 |
| publisher | 阶段 2：产物抽检通过后原子切换/增量同步到 `output/` |
| cleaner | 阶段 3：清理临时目录与 Hugo 缓存 |
| preview | 后台预览：`hugo --buildDrafts` 临时输出，与线上同一渲染器 |

约束：峰值内存 ≤ `GOMEMLIMIT`（默认 256MiB）；构建只写临时目录、校验通过才发布；渲染器为 Hugo Goldmark + Chroma + shortcodes，后台不引入 Python-Markdown/Pygments。

## 3. 页面模式

| 页面类型 | 氛围浓度 | 关键约束 |
| --- | --- | --- |
| 首页 | 4 | 个人信息 Hero（姓名/身份/方向/目标 + 技能徽章同栏）、历程速览、项目卡、最新文章；无任何输入组件 |
| 文章/时间线/项目/关于/资源 | 0 | 纯排版；正文对比度 ≥ 4.5:1 |
| 后台 | 4×0.5 | 表格区不透明；飘动元素不侵入表内文字 |
| Setup/登录 | 4×0.5 | 居中卡片 + 顶部品牌 + 底部备案 |

## 4. 内容覆盖审计表（全站可见内容 ↔ 后台栏目）

| 可见内容 | 数据文件 | 后台栏目 |
| --- | --- | --- |
| 站点名称/定位/承诺 | brand.yaml | 品牌 |
| Logo / favicon | brand.yaml + static/img | 品牌（上传） |
| 版权/备案号 | brand.yaml | 品牌 |
| 备案图标 SVG（ICP/公安） | brand.yaml（`icp_icon` / `police_icon`） | 品牌（可改，留空只留空位） |
| 导航/区块标题/通用标签 | strings.yaml | 页面文案 |
| Hero 姓名/身份/方向/目标 | profile.yaml | 关于我 |
| 技能徽章 | profile.yaml | 关于我 |
| 技能徽章图标 | profile.yaml（`icon` slug）+ themes/blog-theme/static/img/badges/*.svg | 关于我资料（图标 slug） |
| 兄弟项目徽章 | projects frontmatter | 项目 |
| 首页精选/数量/开关 | homepage.yaml | 首页设置 |
| 文章全字段 | posts Markdown | 文章 |
| 项目卡全字段 | projects Markdown | 项目 |
| 时间线节点 | timeline Markdown | 时间线 |
| 关于我长文 | about.md | 关于我 |
| 资源条目 | resources.md | 资源 |
| 媒体图片（Logo/正文插图） | themes/blog-theme/static/img/ | 媒体库（上传后重建公开站） |
| 文章正文预览 | 编辑器正文 | 编辑页"生成预览"（Hugo 渲染） |

验收：逐页对照本表，任何可见内容必须能在后台找到编辑入口；模板零硬编码可见文案。

## 5. 验收清单（Pre-Delivery）

- [ ] 令牌无硬编码 hex（组件内），文案无硬编码（从 brand/profile/strings 读取）
- [ ] 浅色正文对比度 ≥ 4.5:1；键盘焦点可见
- [ ] prefers-reduced-motion 收敛单帧；移动端无横向滚动
- [ ] 响应式四档：375 / 768 / 1024 / 1440
- [ ] 公开站无任何输入/提交/评论/登录组件；无 shields.io 外链
- [ ] 每个 animation 有对应 @keyframes；文章页无循环动效
- [ ] 首页徽章链接兄弟项目且可后台编辑
- [ ] 全站内容覆盖审计表无缺口
- [ ] Markdown 能力清单逐项可渲染（含代码高亮/表格/脚注/Admonition/math/mermaid 按需）
- [ ] 备案号上线前留空；无假占位号
- [ ] Nginx 常规访问日志关闭；匿名打点仅路径+时间戳
- [ ] 后台安全：秘密路径/密码/限速/IP 白名单/非 root/无 Docker socket
- [ ] 全量构建峰值内存 ≤ 256MB（GOMEMLIMIT 实测记录到 MASTER.md）
- [ ] 保存单篇/全量重建 1–3 秒（1000 篇规模实测），中断后输出目录完整可用
- [ ] 后台预览与线上构建共用 Hugo 渲染器

**P1 实测（2026-08-18，37 页，Hugo 0.165.0 extended / macOS arm64）：** 构建耗时约 15ms，峰值 RSS ≈ 55.6MB（`GOMEMLIMIT=256MiB`），首页含 4 兄弟项目徽章与最新文章，搜索索引 3 条，无占位符残留。

## 6. 文件映射（模板 → 本博客）

| 模板默认 | 本博客落点 |
| --- | --- |
| frontend/src/index.css | themes/blog-theme/static/css/tokens.css |
| frontend/src/lib/brand.ts | config/brand.yaml |
| frontend/index.html | 站点基础模板 head 区（构建引擎渲染） |
| frontend/public/ | themes/blog-theme/static/img/ |
| design-system/<project>/BRAND.md | design-system/blog/BRAND.md |
| design-system/<project>/MASTER.md | design-system/blog/MASTER.md（本文件） |
