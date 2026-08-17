# P3 可用第一版实施计划（基础镜像 + 加速变量 + 容器化 + 搜索统计）

> **For agentic workers:** 本计划在单一会话内联执行。步骤用 `- [ ]` 追踪。

**Goal:** 交付可容器化运行的第一版：admin 基础镜像带全软件源加速变量；nginx 托管公开站并反代后台；匿名打点与导入；Fuse.js 本地搜索页；compose 一键拉起并端到端验证。

**Architecture:** 单机 Docker Compose：nginx（公开站 + `/admin` 反代 + beacon 匿名日志）+ admin（FastAPI，profile 按需启动）；content/config/output/data 用 bind 挂载（仓库即数据源），beacon-log 用命名卷。

**Tech Stack:** Docker Compose v2+、nginx:alpine、python:3.12-slim + Hugo v0.165.0 二进制、Fuse.js 7（本地化）。

## Global Constraints

- 软件源全部可加速：`APT_MIRROR`、`PIP_INDEX_URL`、`HUGO_DOWNLOAD_URL`、`HUGO_CHECKSUM_URL` 为 Dockerfile ARG，.env.example 提供示例
- 运行期零外部请求：字体/JS/搜索全部本地化；beacon 打点走同源 nginx
- 公开站零交互栏目：搜索框为纯前端本地过滤（Fuse.js + 构建期 JSON），无任何提交
- 匿名统计：nginx 日志只含 `时间|路径`，不含 IP/UA/Cookie；admin 启动时导入并清空
- 单管理员与 OIDC 契约不变；秘密路径、CSRF、限速不变
- 后台按需启动：`docker compose --profile admin up -d`

---

### Task 1: 基础镜像与加速变量

**Files:** Modify `Dockerfile`；Create `.env.example`、`.dockerignore`（补 data）

- [ ] Dockerfile 增加 `ARG APT_MIRROR/PIP_INDEX_URL/HUGO_DOWNLOAD_URL/HUGO_CHECKSUM_URL`，apt 换源、pip `-i`、Hugo 下载与 checksum 全走变量
- [ ] .env.example 覆盖运行期与构建期全部变量（含注释）
- [ ] 验证：`docker build --build-arg ...` 成功且 `hugo version` 输出 v0.165.0

### Task 2: nginx 配置（静态 + 反代 + beacon）

**Files:** Create `nginx/default.conf`

- [ ] root=output 静态直出；`/admin/` 反代 `http://admin:8000`（保留 Host/X-Forwarded-*）
- [ ] `location = /api/beacon`：`empty_gif` + 匿名日志 `beacon.log`（格式 `$time_iso8601|$request_uri`）
- [ ] 常规 access_log 关闭；安全头与 body 大小限制

### Task 3: 打点与导入

**Files:** Modify `themes/blog-theme/layouts/partials/footer.html`；Create `admin/ingest.py`；Modify `admin/config.py`、`admin/main.py`（lifespan 导入）

- [ ] footer 加入隐藏 1×1 像素 `<img src="/api/beacon?p={{ .RelPermalink }}">`
- [ ] `import_beacon_log()`：解析 `时间|/api/beacon?p=路径` → stats 表 upsert → 成功后清空日志
- [ ] lifespan 启动时执行导入；`BEACON_LOG` 环境变量可配路径

### Task 4: 本地搜索页

**Files:** Create `themes/blog-theme/static/js/fuse.min.js`（已下载）、`content/search-ui.md`、`themes/blog-theme/layouts/_default/single.search-ui.html`；Modify `config/strings.yaml`、`header.html`

- [ ] 搜索页：输入框 + 结果列表，加载 `/search/index.json` + fuse.min.js，本地过滤
- [ ] strings.nav 增加 `search: 搜索`；header 增加导航链接

### Task 5: compose 完善

**Files:** Modify `compose.yaml`

- [ ] nginx 挂载 `./nginx/default.conf`、`./output`、beacon-log；端口 `${HTTP_PORT:-80}` / `${HTTPS_PORT:-443}`
- [ ] admin 挂载 `./content ./config ./output ./data` + beacon-log；`env_file: .env (required:false)`；build args 透传加速变量；GOMEMLIMIT 环境
- [ ] 验证：`docker compose config` 通过

### Task 6: 容器化端到端验证

- [ ] `docker compose build admin`（默认源；慢则用加速变量）
- [ ] `HTTP_PORT=18080 docker compose up -d` → curl 首页含定位语
- [ ] 未启 admin 时 `/admin/login` 返回 502 中性页
- [ ] `HTTP_PORT=18080 docker compose --profile admin up -d` → `/admin/login` 200、首启 302 setup
- [ ] 访问公开页触发 beacon → 启动 admin 导入 → `/admin/stats` 出现路径与次数
- [ ] `/search-ui/` 200 且 fuse.min.js 可访问

### Task 7: 文档与提交

- [ ] MASTER/AGENTS/设计文档同步：bind 挂载、加速变量、beacon 导入、搜索页
- [ ] Commit：`feat: 可用第一版——加速镜像、nginx、beacon、搜索、compose 全链路`
