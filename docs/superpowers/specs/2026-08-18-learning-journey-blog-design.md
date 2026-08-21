# Li&Blog 学习历程博客 · 设计文档

> 日期：2026-08-18 ｜ 版本：v1.0 ｜ 状态：设计定稿，待用户评审
> 配套文件：`design-system/blog/BRAND.md`（品牌意图）、`design-system/blog/MASTER.md`（实现速览）

## 1. 项目定位

- 一句话定位：**一次记录，见证每一步成长**
- 品牌承诺：**每一篇都是真实足迹，每次回顾都有迹可循**
- 人格比喻：安静的同行者
- 定位说明：个人学习历程博客，记录为主、兼顾分享与作品展示；以"怎么学会的"为核心——阶段、项目、踩坑、复盘、下一步。

## 2. 硬性约束

1. **公开前端零交互入口**：无评论、留言、注册、登录、表单、用户输入类组件；纯展示。
2. **个人备案合规**：非经营性；无公开交互栏目；不收集访客个人信息；页脚展示 ICP/公安备案号。
3. **最低占用高性能**：访客流量零后端进程；常态仅 nginx 常驻；后台按需手动启动。
4. **全站可见内容后台可改**：公开站任何可见内容都有后台编辑入口，模板零硬编码可见文案。
5. **单管理员**：后台只有一个管理员账号；本地密码 + Li&Pass OIDC 双认证入口；无任何其他用户。
6. **容器编排**：Docker Compose + profiles；后台容器手动按需拉起。
7. **完全支持 Markdown**：全部内容以 Markdown 为源，构建期渲染。

## 3. 技术架构

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 静态生成 | Hugo（Go 单二进制）+ Python 分段编排壳 | Goldmark + Chroma；临时目录构建、GOMEMLIMIT 限内存、原子发布 |
| 后台 | FastAPI + SQLite + Jinja2 | 单 worker；内容管理 + 统计 + 登录 |
| 内容源 | Markdown / YAML 文件 | 单一事实来源，无独立内容数据库 |
| 公开托管 | Nginx + CDN（可选） | 静态文件直出 |
| 编排 | Docker Compose profiles | nginx 默认常驻，admin 按需启动 |
| 搜索 | Fuse.js + 构建期 JSON 索引 | 纯前端本地匹配 |
| 统计 | Nginx empty_gif 匿名打点 + SQLite | 仅路径 + 时间戳 |

```mermaid
flowchart LR
    A[访客浏览器] --> B[CDN]
    B --> C[Nginx 容器]
    C --> D[output 共享卷]
    E[管理员] --> C
    C --> F[admin 容器 FastAPI]
    F --> G[content 卷 Markdown]
    F --> D
    F --> H[data 卷 SQLite]
    F --> J[构建编排：校验→Hugo 渲染→原子发布]
    J --> G
    J --> D
    I[beacon 匿名日志卷] -. nginx 打点 -> F
```

### 3.1 Hugo 分段构建（小内存适配）

生成器：**Hugo**（Go 单二进制）。1000 篇文档全量构建约 1–3 秒；通过分段编排 + Go 内存上限适配 512MB 主机。

**分段编排流水线（Python 薄壳）：**

| 阶段 | 做什么 | 内存量级 |
| --- | --- | --- |
| 0 校验 | 构建前快速静态校验：frontmatter 完整性、内部链接、图片存在性 | <10MB |
| 1 渲染 | `GOMEMLIMIT=256MiB HUGO_NUMWORKERMULTIPLIER=0.5 hugo --gc` 构建到临时目录 `.build-tmp/` | ≤256MB（Go 运行时软上限） |
| 2 发布 | 产物完整性抽检通过后**目录内逐文件原子同步**到 `output/`（保持目录 inode 稳定，兼容 Docker bind 挂载） | <20MB |
| 3 清理 | 删除旧临时目录，Hugo 缓存 `--gc` | <10MB |

要点：

- `GOMEMLIMIT` 显式限制 Hugo 进程内存；`HUGO_NUMWORKERMULTIPLIER` 降低并行度进一步压低峰值
- Hugo 二进制为固定版本（v0.165.0），随仓库提交于 `bin/hugo/`（linux amd64/arm64，含 SHA256 校验），admin 镜像 Dockerfile 按 `TARGETARCH` COPY 并校验，构建不联网；禁止第三方 Hugo 镜像；构建在容器内执行，不依赖宿主机工具链
- Hugo 原生产出分页列表、标签/归档、RSS、sitemap、搜索 JSON（模板生成），无需自研聚合器
- **保存单篇 = 全量 Hugo 构建（1–3 秒）**，无需自研增量；"全部重建"同样秒级
- 可选 `--renderSegments`（home/list/page/taxonomy 分开渲染）供极端小内存场景进一步分段
- 中断安全：构建只写临时目录，校验通过才发布；发布原子切换
- **后台预览走 Hugo 自身渲染**（`--buildDrafts` + 临时输出），后台所见即线上成品

内容渲染单一出处：Hugo Goldmark + shortcodes；后台不再使用 Python-Markdown/Pygments 渲染链路。

## 4. 内容模型

所有可见内容来自文件，构建期聚合渲染：

```text
content/
├── posts/          # 文章（frontmatter：title/date/tags/summary/status/math/mermaid/cover）
├── projects/       # 兄弟项目与本站项目卡（含徽章字段）
├── timeline/       # 学习时间线节点
├── about.md        # 关于我长文
└── resources.md    # 资源推荐
config/
├── brand.yaml      # 品牌单点：名称/定位/承诺/Logo/备案
├── profile.yaml    # 个人信息：姓名/身份/方向/目标/技能/链接
├── homepage.yaml   # 首页配置：精选/数量/开关
└── strings.yaml    # 站点级文案：导航/区块标题/通用标签
```

### Markdown 能力清单（Hugo Goldmark，构建期全部渲染，访客零解析器）

- GFM：表格、任务列表、删除线、自动链接
- 围栏代码块 + Chroma 语法高亮（Hugo 内置，Go 实现；配色映射 `--liblog-*` 令牌）
- 脚注、TOC、标题锚点、内部链接
- Admonition 提示块：Hugo shortcode（`{{< note >}}` 等，纯 CSS）
- 数学公式：KaTeX 本地文件，仅 `math: true` 文章加载
- Mermaid 图表：本地文件，仅 `mermaid: true` 文章加载
- 受限 HTML（内容仅作者本人）
- 渲染单一出处：Hugo（Goldmark + shortcodes），后台预览调用同一 Hugo 渲染

## 5. 公开站设计

### 首页（个人信息 + 历程聚合）

| 区块 | 内容 | 数据来源 | 后台栏目 |
| --- | --- | --- | --- |
| Hero | Logo/占位 + 姓名 + 定位 + 身份/方向/目标 + 技能徽章（`hero.show_skills` 控制，同栏展示） | brand.yaml + profile.yaml + homepage.yaml | 品牌 / 关于我 / 首页设置 |
| 兄弟项目徽章 | 四兄弟项目徽章（链接仓库或复盘） | projects frontmatter | 项目 |
| 技术栈徽章 | 技能徽章行（官方色圆点） | profile.yaml skills | 关于我 |
| 历程速览 | 最近 N 个里程碑 | timeline + homepage.yaml | 时间线 / 首页设置 |
| 项目集 | 项目卡片 | projects | 项目 |
| 最新文章 | 最近 3–5 篇 | posts + homepage.yaml | 文章 / 首页设置 |
| 页脚 | 版权 + 备案号 | brand.yaml | 品牌 |

### 其他页面

- 文章列表 / 详情（TOC、上一篇/下一篇、标签）
- 项目集（卡片 → 复盘文章）
- 时间线（纵向里程碑）
- 关于我（profile 表单 + 长文）
- 资源推荐
- 归档 / 标签

### 徽章规范（站点版）

- 本地 HTML/SVG 胶囊，无 shields.io 外链
- 技术栈徽章：浅色胶囊 + 官方品牌色圆点 + 名称 + 官网链接
- 项目徽章：家族语义色，链接兄弟仓库或站内复盘
- 个人信息组件中的技能徽章：按 README 徽章标准本地实现（官方品牌色整块 + 白字 + 本地 SVG 图标 + 官网链接），不使用 shields.io 外链
- README 仍按 Li&About 规范使用 shields.io；站点用家族淡色胶囊，理由记录于 BRAND.md

## 6. 后台设计

### 首启 Setup（三步向导）

- 触发：SQLite 无管理员记录时，访问后台任意路径 302 到 `/admin/setup`
- 步骤 1 基础信息：站点名称/定位/承诺（brand.yaml）+ 姓名/身份/方向/目标（profile.yaml）
- 步骤 2 管理员创建：用户名 + 强密码（PBKDF2-HMAC-SHA256，600k 迭代），创建后 setup 永久失效
- 步骤 3 OIDC 绑定（可跳过）：展示需登记的精确回调地址；配置缺失则隐藏；成功后写入 `oidc_sub`
- 中断恢复：每步落盘标记，重进 setup 从断点继续

### 双登录与账号关系

- 唯一管理员记录 `admin_account`：`username / password_hash / oidc_sub`
- 本地登录：用户名 + 密码
- OIDC 登录：授权码 + PKCE 全流程，`sub` 精确等于 `oidc_sub` 才放行
- 硬边界：不自动建号；`sub` 不匹配即拒绝；`oidc_sub` 为空时 OIDC 入口禁用
- 绑定/解绑（设置栏）需当前密码二次验证
- 会话绑定 `(sub, sid)`，支持回程登出

### 后台栏目（八栏，全站内容覆盖）

1. 品牌：名称/定位/承诺/版权/备案号/Logo 上传
2. 页面文案：strings.yaml 全量标签
3. 首页设置：精选文章/数量/徽章开关
4. 文章：CRUD + 草稿 + 预览
5. 项目：CRUD + 徽章字段
6. 时间线：节点 CRUD
7. 关于我：profile 表单 + 长文
8. 资源：条目 CRUD

保存即触发重建；批量操作合并为一次重建；后台提供"全部重建"按钮。

工具：文章支持批量导入（多选 Markdown 或 ZIP，校验 frontmatter/slug，同名默认跳过、可覆盖，导入完成后合并一次重建）；系统提供站点备份下载（content/、config/、媒体图片、data/blog.db 一致性快照、hugo.toml 打包为 ZIP）与后台恢复（上传 ZIP，恢复前自动生成安全备份到 data/restore-backups/，覆盖内容/配置/媒体/数据库后清除旧会话）；首次建站时设置向导可直接从备份 ZIP 恢复建站，备份含管理员账号则跳转登录，否则继续创建管理员。

### 后台安全

- 秘密路径 `/admin` + 强密码 + 登录限速 + 可选 IP 白名单
- 容器入口 root 仅用于初始化挂载目录属主，应用以 UID 1000 运行；不挂 Docker socket；admin 不暴露宿主端口
- OIDC secret 只存环境变量/secret 文件，不进 git
- 后台关闭时 nginx 返回"后台服务未启动"引导页（502 → admin-off.html）

## 7. OIDC 对接设计（Li&Pass）

依据《OIDC 对接指南》实现，对接方契约全部满足：

- 必选：回调端点 `GET /admin/oidc/callback`（state 校验、error 按失败处理、换码带 PKCE）
- 令牌：JWKS 按 kid 验签 RS256；校验 iss / aud=client_id / nonce / iat / exp / at_hash
- userinfo：access_token 调用，`sub` 与管理员绑定值精确匹配
- 登出通道：回程登出 `POST /admin/oidc/backchannel`（验签、120 秒窗口、jti 防重放、events 检查、按 (sub,sid) 下线）
- 本地会话自带过期，不依赖门户送达
- 登出本网站始终可用；RP 发起登出列为二期可选
- 客户端类型：机密客户端；登记回调与回程地址逐字符精确匹配

## 8. 搜索与统计

- 搜索：构建期生成文章 JSON 索引，Fuse.js 本地匹配，零服务端开销
- 统计：Nginx `empty_gif` 返回 1×1 像素，仅写匿名日志（时间 + 路径，无 IP/UA/Cookie/Referer）
- 后台启动时自动导入 SQLite 日聚合，成功后清空日志；失败保留重试
- Nginx 关闭常规访问日志，匿名打点日志为唯一统计来源

## 9. 设计系统（Li-Design 实例化）

- 来源：Li-Design V1.4 模板（git 子模块 `design-system/Li-Design`，`reusable-tokens.template.css`）；令牌值已逐项核对一致，另含打印/代码高亮/CTA 站点扩展
- 22 槽位已全部填定，见 `design-system/blog/BRAND.md`
- 认证页底部对齐（2026-08-21）：登录/设置向导底部补齐版权 + 备案（对齐 Li&Panel AuthShell 页脚）
- 样式层 Tailwind CSS 4（2026-08-21）：`tokens.css` 由 `web/src/tokens.css` 编译，与 Li&Panel `index.css` 同构（`@theme` 别名 + `--liblog-*` 令牌），页眉/页脚使用与 Panel 相同的 utility class
- 页眉页脚 1:1 对齐（2026-08-21，Li&Panel 同款实现）：页眉 AppHeader（sticky 玻璃 `--liblog-header-*`、品牌名 ShinyText、`flow-rule` 1px 流光线、`h-16`/`max-w-7xl`）；页脚 SiteFooter 单行（版权 + 声明 + 备案 + 归档 + 许可，`min-h-14`/`text-xs`）
- 文件映射：

| 模板默认 | 本博客落点 |
| --- | --- |
| design-system/Li-Design/reusable-tokens.template.css | 家族模板参考（git 子模块，非运行时依赖） |
| frontend/src/index.css | themes/blog-theme/static/css/tokens.css |
| frontend/src/lib/brand.ts | config/brand.yaml |
| frontend/index.html | 站点基础模板 head 区（P1） |
| frontend/public/ | themes/blog-theme/static/assets/ |

- 氛围浓度：首页 4 / 内容页 0 / 后台 4×0.5；CSS-only；prefers-reduced-motion 收敛
- 公开站零交互：模板交互组件只进后台

## 10. 备案合规清单

| 项 | 落实 |
| --- | --- |
| 页脚备案号 | ICP 号 + beian.miit.gov.cn 链接；公安号 + beian.gov.cn 链接（通过后填入） |
| 非经营性 | 无广告、无付费、无交易 |
| 无公开交互 | 无评论/留言/注册/登录；后台不对公众开放 |
| 个人信息 | 访客零收集（无 Cookie、无 IP 落地） |
| 内容 | 原创为主、转载授权、不碰敏感与需资质内容 |
| 服务器 | 大陆境内，备案通过后接入 |

## 11. 容器与部署

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./output:/usr/share/nginx/html:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - beacon-log:/var/log/nginx
  admin:
    profiles: ["admin"]
    build: .
    volumes:
      - ./content:/app/content
      - ./config:/app/config
      - ./output:/app/output
      - ./data:/app/data
      - beacon-log:/app/beacon
```

命令：日常 `docker compose up -d`；管理 `docker compose --profile admin up -d`；停后台 `docker compose --profile admin stop admin`。端口可用 `${HTTP_PORT}` / `${HTTPS_PORT}` 覆盖（如本地验证用 18080）。

挂载：content/config/output 用仓库 bind 挂载（仓库即数据源，单份数据；入口自动修复属主，无需手动 chown）；data/media 为 Docker 命名卷；beacon-log 为命名卷（nginx 写匿名打点，admin 启动只读导入）。

环境变量（.env，不进 git）：`LIPASS_ISSUER`、`LIPASS_CLIENT_ID`、`LIPASS_CLIENT_SECRET`、`LIPASS_REDIRECT_URI`、`ADMIN_PATH`、`ADMIN_SESSION_SECRET` 等；模板见 `.env.example`。

软件源加速变量（构建期 `--build-arg`）：`APT_MIRROR`、`PIP_INDEX_URL`——apt/pip 下载可走国内镜像，默认官方源；Docker Hub 基础镜像（nginx/python）可通过 `DOCKER_MIRROR_PREFIX` 镜像前缀变量加速（如 `docker.m.daocloud.io/`，须以 `/` 结尾，留空=官方源）；Hugo v0.165.0 二进制随仓库提交于 `bin/hugo/`，构建不联网下载。

镜像结构：多阶段构建（builder 从仓库 `bin/hugo/` COPY 并校验 Hugo + 安装 venv 依赖；runtime 只保留 venv/Hugo/ca-certificates），入口以 root 修复挂载目录属主后降权 UID 1000 执行，内置 `/healthz` 健康检查；`content/ config/ output/` 用仓库 bind 挂载（属主自动修复），`data/ media/` 为 Docker 命名卷（`blog-data`/`blog-media`，自动继承 UID 1000 所有权），媒体容器内映射 `themes/blog-theme/static/img`（公开 `/img/`），全新部署无需手动 chown。

媒体库删除：删除图片时同步扫描 content Markdown（正文图片语法、HTML img、Hugo figure 短代码、frontmatter cover 等）与 config YAML，清空引用该图片的地址后再触发重建。

## 12. 性能预算

| 状态 | 常驻 |
| --- | --- |
| 常态（后台离线） | nginx 约 5–10MB |
| 管理时段 | nginx + admin 约 70–90MB |
| 首页传输量 | HTML+CSS+JS < 100KB（不含图片） |
| 构建峰值 | ≤256MB（`GOMEMLIMIT` 可配） |
| 保存单篇/全量重建 | 1–3 秒（1000 篇规模） |
| 服务器 | 512MB 轻量 VPS 足够 |

## 13. 实施路线

- **P0 设计实例化（本阶段）**：设计文档 + design-system/blog + 令牌 + 配置骨架 + AGENTS.md
- **P1 公开站**：Hugo 主题骨架（Goldmark/shortcodes/Chroma）+ 分段编排壳 + 内容结构 + strings.yaml + 3 篇示例 + 兄弟项目 Markdown 初稿
- **P2 后台**：Setup 向导 + 双登录（本地 + OIDC）+ 八栏目 + 预览（走 Hugo）+ 保存触发编排构建
- **P3 容器化**：Dockerfile（加速变量）+ compose.yaml（profiles/bind 挂载）+ nginx 反代与匿名打点 + admin 每次启动全量重建（已完成，P3→P5 合并推进）
- **P4 搜索统计**：Fuse.js 本地化 + 搜索页 + empty_gif 打点 + 启动导入（已完成）
- **P5 备案上线**：域名、服务器、备案、HTTPS、Li&Pass 客户端登记、正式部署

## 14. 决策记录

已闭合决策：Hugo 分段构建（Go 生成器 + Python 编排壳）+ FastAPI 后台 + SQLite、Docker Compose profiles、双登录（本地 + OIDC）、单管理员、Setup 向导、八栏目后台、首页聚合、兄弟项目纳入、全 Markdown、本地徽章、海玻璃家族令牌、氛围浓度分层、本地搜索、匿名统计、回程登出、分页 20 篇/页、索引瘦身、图片上传、密码哈希 PBKDF2-HMAC-SHA256（600k，零原生依赖）。

有意留空：`logo` / `favicon`（后期上传）；`icp` / `police`（备案通过后填写，禁止假占位号）。

二期可选：RP 发起登出、CDN 接入、`logout_uri` 浏览器串跳。

## 15. 易用性迭代记录（2026-08-18）

针对“后台太难用”的反馈，参考 Editora / JekyllPad / Decap CMS 的静态站编辑体验、Hugo 博客后台的图片上传实践与通用 CMS 可用性清单，完成以下迭代：

- 后台编辑器：右侧分栏 Hugo 预览（`preview_raw`，保存后由 Hugo 渲染，不离开编辑页）、字符/词数统计、插入图片对话框、保存留在本页 / 返回列表两种动作。
- 媒体库：上传/搜索/删除图片（png/jpg/jpeg/gif/webp/avif，≤5MB，路径防穿越），上传后触发重建使公开站立即可见；编辑页可直接把媒体路径插入正文。
- 列表页：标题/标签搜索、状态筛选、50 条分页、状态徽章、公开页“查看”链接与空状态引导。
- 配置表单：首页设置改数字/勾选/精选文章；关于我资料的技能与外部链接改行编辑（颜色选择器），不再要求手写 YAML；文案分组保留 YAML 块但带字段说明与解析错误提示。
- 仪表盘与导航：分组导航（内容/设置/系统）、快捷操作、最近文章与草稿数、后台深浅色切换（localStorage 记忆）。
- 公开站：面包屑、阅读时间、更新日期、上一篇/下一篇、搜索页结果计数与摘要、404 页、跳转到正文、移动端导航触达尺寸。
- 验证：25 项单元测试 + TestClient 端到端流程（登录→配置保存→媒体上传→文章保存→Hugo 预览）通过；Hugo v0.165.0 全量构建 39 页通过。
