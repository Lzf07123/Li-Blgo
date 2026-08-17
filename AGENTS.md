# Li&Blog 项目协作手册

## 事实来源（按优先级）

| 层级 | 文件 | 职责 |
| --- | --- | --- |
| 设计意图 | design-system/blog/BRAND.md | 定位、原则、视觉方向、氛围标准 |
| 实现速览 | design-system/blog/MASTER.md | 令牌、组件、页面模式、内容覆盖审计 |
| 设计文档 | docs/superpowers/specs/ | 系统设计事实（含本文件引用） |
| 代码事实 | themes/blog-theme/static/css/tokens.css + config/*.yaml | 令牌与品牌/个人/站点文案唯一出处 |

冲突时：代码事实优先，必须同步回写 BRAND.md / MASTER.md / 设计文档，防止文档漂移。

## 硬性规则

1. **单一事实来源**：品牌文案只存 config/brand.yaml；个人资料只存 config/profile.yaml；站点文案只存 config/strings.yaml；颜色/阴影/动效只存 tokens.css。组件与模板禁止硬编码可见文案和 hex 值。
2. **公开站零交互**：任何改动不得向公开页面引入评论、留言、注册、登录、表单、用户输入类组件。
3. **全站可见内容后台可改**：新增可见内容必须先确认后台有编辑入口，并更新 MASTER.md 内容覆盖审计表。
4. **备案红线**：备案号禁止假占位号；页脚备案链接指向官方域名；公开站不收集访客个人信息。
5. **秘密与安全**：OIDC client_secret、密码等只走环境变量/.env/secret 文件，禁止提交 git；后台路径保持秘密；不挂载 Docker socket；容器非 root。
6. **Markdown 为内容源**：文章/项目/时间线/关于/资源一律 Markdown/YAML，构建期渲染，禁止在公开页引入运行时 Markdown 解析器。
7. **性能底线**：公开站保持纯静态；新增前端依赖须说明体积与必要性；动效尊重 prefers-reduced-motion。
8. **构建约束**：构建必须走 Hugo 分段编排（校验 → `GOMEMLIMIT` 限内存渲染到临时目录 → 原子发布 → 清理）；峰值内存不得超过 `GOMEMLIMIT`（默认 256MiB）；渲染器只用 Hugo（Goldmark + Chroma + shortcodes），后台预览与线上构建共用；禁止引入 Python-Markdown/Pygments 渲染链路。Hugo 使用固定版本二进制（v0.165.0，admin 镜像 Dockerfile 下载并校验 checksum），禁止第三方 Hugo 镜像；构建在容器内执行，不依赖宿主机工具链。
9. **后台安全**：密码哈希用 stdlib PBKDF2-HMAC-SHA256（600k 迭代，零原生依赖，替代 Argon2/scrypt 以兼容 macOS 自带 Python 与容器）；会话存 SQLite、Cookie 只存随机 id（HttpOnly/SameSite=Lax）；所有 POST 校验 CSRF；登录限速 5 次/60 秒；OIDC 按对接文档契约实现（PKCE、state/nonce、id_token 验签、回程登出 jti 防重放、`sub` 精确匹配单管理员）；OIDC secret 只走环境变量。
10. **软件源与运行期依赖**：基础镜像的 apt/pip/Hugo 下载必须通过 `APT_MIRROR` / `PIP_INDEX_URL` / `HUGO_DOWNLOAD_URL` / `HUGO_CHECKSUM_URL` 变量（.env.example 提供模板）；运行期禁止引入外部 CDN/远程字体/远程 JS；Fuse.js 等前端库必须本地化并提交。内容/配置/输出/数据用仓库 bind 挂载，beacon 日志为命名卷。

## 协作规范

- 并行任务零文件重叠：每个文件同一时刻只有一个 owner；需要改他人文件先认领并经 root 同意。
- 验证才算完成：任何改动必须给出可验证证据（构建通过、页面渲染、令牌占位符检查、对比度等）；具体验证命令随实施阶段落地补充到本文档。
- 不做破坏性操作；不动他人未提交的改动；不擅自切分支或合并。
- 验收以证据为准，不接受无证据的"完成"。

## 多 Agents 协作（首次设计/实现期）

参照 Li-Design 方案第 8 章：任务卡写明 Consumes 与 Produces（精确到文件）、验收标准可独立验证；root 负责拆解、指派与验收；槽位类需人拍板的决策禁止用猜测代替调查。
