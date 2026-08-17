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
| badge | 本地徽章胶囊（技术栈/项目） |
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
| table-shell | 列表（文章/项目/时间线/资源） |
| markdown-editor | 文本区 + 服务端预览 |
| toast / modal | 保存反馈与确认弹窗 |
| theme-toggle | 后台主题切换 |

**P2 已实现（2026-08-18）：** Setup 三步向导、本地登录（限速+CSRF）、Li&Pass OIDC 登录/绑定/回程登出、八栏目（文章/项目/时间线/关于/资源/品牌/文案/首页/资料）、Hugo 预览与保存重建；16 项单元测试通过 + 端到端 curl 流程验证。

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
| 首页 | 4 | 徽章行、历程速览、项目卡、最新文章；无任何输入组件 |
| 文章/时间线/项目/关于/资源 | 0 | 纯排版；正文对比度 ≥ 4.5:1 |
| 后台 | 4×0.5 | 表格区不透明；飘动元素不侵入表内文字 |
| Setup/登录 | 4×0.5 | 居中卡片 + 顶部品牌 + 底部备案 |

## 4. 内容覆盖审计表（全站可见内容 ↔ 后台栏目）

| 可见内容 | 数据文件 | 后台栏目 |
| --- | --- | --- |
| 站点名称/定位/承诺 | brand.yaml | 品牌 |
| Logo / favicon | brand.yaml + static/img | 品牌（上传） |
| 版权/备案号 | brand.yaml | 品牌 |
| 导航/区块标题/通用标签 | strings.yaml | 页面文案 |
| Hero 姓名/身份/方向/目标 | profile.yaml | 关于我 |
| 技能徽章 | profile.yaml | 关于我 |
| 兄弟项目徽章 | projects frontmatter | 项目 |
| 首页精选/数量/开关 | homepage.yaml | 首页设置 |
| 文章全字段 | posts Markdown | 文章 |
| 项目卡全字段 | projects Markdown | 项目 |
| 时间线节点 | timeline Markdown | 时间线 |
| 关于我长文 | about.md | 关于我 |
| 资源条目 | resources.md | 资源 |

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
