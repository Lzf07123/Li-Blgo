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
| 静态生成 | 自研分段增量构建引擎（Python） | Python-Markdown + Pygments + Jinja2；批处理 + SQLite manifest，峰值内存可配 |
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
    F --> J[构建引擎：扫描→分块渲染→聚合→发布]
    J --> G
    J --> D
    I[beacon 匿名日志卷] -. nginx 打点 -> F
```

### 3.1 分段构建引擎（小内存适配）

目标：200–1000 篇 Markdown 文档在 512MB 主机上构建，峰值内存可控、增量保存秒级、任何时刻输出目录完整可用。

**四阶段流水线：**

| 阶段 | 做什么 | 内存量级 |
| --- | --- | --- |
| 0 扫描 | 遍历 content/config/themes，只读 frontmatter，与 manifest 比对（mtime + sha256），产出变更清单 | <5MB |
| 1 分块渲染 | 只处理变更文章，按 `BUILD_BATCH_SIZE`（默认 32）分批渲染 Markdown + Pygments + Jinja2；每批原子写输出后释放引用；高亮结果按 (lexer, code sha256) 缓存复用 | ≤ `BUILD_MEMORY_LIMIT`（默认 128MB） |
| 2 聚合页 | 只读 frontmatter/摘要，生成首页、分页列表、标签、归档、搜索 JSON、RSS、sitemap | ≈2MB |
| 3 清理发布 | 删除已失效输出，更新 manifest，输出完整性抽检 | <10MB |

**内存自适应：** `BUILD_MEMORY_LIMIT` 为软上限，超限自动缩批（32→16→8）；每批结束后释放引用并 `gc.collect()`。

**增量与全量：** 保存单篇 → 同步跑阶段 0–2（秒级）；"全部重建"与首次上线 → 后台任务跑全量分块（1000 篇约 5–15 分钟，一次性，可接受），带进度。

**中断安全：** 每个文件先写临时文件再 `os.replace` 原子替换；manifest 每批更新；构建中断时输出目录始终完整。

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

### Markdown 能力清单（构建期全部渲染，访客零解析器）

- GFM：表格、任务列表、删除线、自动链接
- 围栏代码块 + Pygments 语法高亮（配色映射 `--liblog-*` 令牌）
- 脚注、TOC、标题锚点、内部链接
- Admonition 提示块（`!!! note` 等，纯 CSS）
- 数学公式：KaTeX 本地文件，仅 `math: true` 文章加载
- Mermaid 图表：本地文件，仅 `mermaid: true` 文章加载
- 受限 HTML（内容仅作者本人），可选用 bleach 白名单清理
- 渲染配置单一出处（`markdown_config.py`），构建引擎与后台预览共用

## 5. 公开站设计

### 首页（个人信息 + 历程聚合）

| 区块 | 内容 | 数据来源 | 后台栏目 |
| --- | --- | --- | --- |
| Hero | Logo/占位 + 姓名 + 定位 + 身份/方向/目标 | brand.yaml + profile.yaml | 品牌 / 关于我 |
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
- README 仍按 Li&About 规范使用 shields.io；站点用家族淡色胶囊，理由记录于 BRAND.md

## 6. 后台设计

### 首启 Setup（三步向导）

- 触发：SQLite 无管理员记录时，访问后台任意路径 302 到 `/admin-xxxx/setup`
- 步骤 1 基础信息：站点名称/定位/承诺（brand.yaml）+ 姓名/身份/方向/目标（profile.yaml）
- 步骤 2 管理员创建：用户名 + 强密码（Argon2），创建后 setup 永久失效
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

### 后台安全

- 秘密路径 `/admin-xxxx` + 强密码 + 登录限速 + 可选 IP 白名单
- 容器非 root；不挂 Docker socket；admin 不暴露宿主端口
- OIDC secret 只存环境变量/secret 文件，不进 git
- 后台关闭时 nginx 返回中性"暂不可用"页

## 7. OIDC 对接设计（Li&Pass）

依据《OIDC 对接指南》实现，对接方契约全部满足：

- 必选：回调端点 `GET /admin-xxxx/oidc/callback`（state 校验、error 按失败处理、换码带 PKCE）
- 令牌：JWKS 按 kid 验签 RS256；校验 iss / aud=client_id / nonce / iat / exp / at_hash
- userinfo：access_token 调用，`sub` 与管理员绑定值精确匹配
- 登出通道：回程登出 `POST /admin-xxxx/oidc/backchannel`（验签、120 秒窗口、jti 防重放、events 检查、按 (sub,sid) 下线）
- 本地会话自带过期，不依赖门户送达
- 登出本网站始终可用；RP 发起登出列为二期可选
- 客户端类型：机密客户端；登记回调与回程地址逐字符精确匹配

## 8. 搜索与统计

- 搜索：构建期生成文章 JSON 索引，Fuse.js 本地匹配，零服务端开销
- 统计：Nginx `empty_gif` 返回 1×1 像素，仅写匿名日志（时间 + 路径，无 IP/UA/Cookie/Referer）
- 后台启动时自动导入 SQLite 日聚合，成功后清空日志；失败保留重试
- Nginx 关闭常规访问日志，匿名打点日志为唯一统计来源

## 9. 设计系统（Li-Design 实例化）

- 来源：Li-Design V1.2 模板；令牌值参考 Li&Pass / Li&Chat 设计子模块落地代码事实
- 22 槽位已全部填定，见 `design-system/blog/BRAND.md`
- 文件映射：

| 模板默认 | 本博客落点 |
| --- | --- |
| frontend/src/index.css | themes/blog-theme/static/css/tokens.css |
| frontend/src/lib/brand.ts | config/brand.yaml |
| frontend/index.html | 站点基础模板 head 区（P1） |
| frontend/public/ | themes/blog-theme/static/img/ |

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
      - output:/usr/share/nginx/html:ro
      - beacon-log:/var/log/nginx
  admin:
    profiles: ["admin"]
    build: .
    volumes:
      - content:/app/content
      - output:/app/output
      - data:/app/data
      - beacon-log:/app/beacon
```

命令：日常 `docker compose up -d`；管理 `docker compose --profile admin up -d`；停后台 `docker compose --profile admin stop admin`。

卷：content（Markdown）、output（构建产物，nginx+admin 共享）、data（SQLite）、beacon-log（匿名打点）。

环境变量（.env，不进 git）：`LIPASS_ISSUER`、`LIPASS_CLIENT_ID`、`LIPASS_CLIENT_SECRET`、`ADMIN_OIDC_SUB`（setup 绑定后写入）。

## 12. 性能预算

| 状态 | 常驻 |
| --- | --- |
| 常态（后台离线） | nginx 约 5–10MB |
| 管理时段 | nginx + admin 约 70–90MB |
| 首页传输量 | HTML+CSS+JS < 100KB（不含图片） |
| 构建峰值 | ≤128MB（`BUILD_MEMORY_LIMIT` 可配，分块处理） |
| 保存单篇 | 秒级（增量阶段 0–2） |
| 全量首次/重建 | 1000 篇约 5–15 分钟（后台任务，一次性） |
| 服务器 | 512MB 轻量 VPS 足够 |

## 13. 实施路线

- **P0 设计实例化（本阶段）**：设计文档 + design-system/blog + 令牌 + 配置骨架 + AGENTS.md
- **P1 公开站**：分段构建引擎（扫描/分块渲染/聚合/发布）+ 主题 + 内容结构 + strings.yaml + 3 篇示例 + 兄弟项目 Markdown 初稿
- **P2 后台**：Setup 向导 + 双登录（本地 + OIDC）+ 八栏目 + 预览 + 增量重建（对接分段引擎）
- **P3 容器化**：Dockerfile + compose.yaml（profiles）+ 匿名打点导入
- **P4 搜索统计**：Fuse.js 索引（聚合阶段生成）+ empty_gif 打点
- **P5 备案上线**：域名、服务器、备案、HTTPS、Li&Pass 客户端登记、正式部署

## 14. 决策记录

已闭合决策：Python 栈（自研分段构建引擎 + FastAPI + SQLite）、Docker Compose profiles、双登录（本地 + OIDC）、单管理员、Setup 向导、八栏目后台、首页聚合、兄弟项目纳入、全 Markdown、本地徽章、海玻璃家族令牌、氛围浓度分层、本地搜索、匿名统计、回程登出、分段构建（分页 20 篇/页、索引瘦身、图片上传）。

有意留空：`logo` / `favicon`（后期上传）；`icp` / `police`（备案通过后填写，禁止假占位号）。

二期可选：RP 发起登出、CDN 接入、`logout_uri` 浏览器串跳。
