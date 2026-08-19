# Li&Blog 第三轮 100 版深度优化记录（v101–v200）

> 日期：2026-08-19 ｜ 状态：进行中
> 基线：前两轮（OPTIMIZATION-50.md、OPTIMIZATION-100.md）已完成；本轮基线 114 项单元测试全绿、Hugo v0.165.0 构建通过、工作区干净（main 分支）。
> 外部对标（2026-08-19 检索）：Ghost（编辑器卡片/内置 SEO 工具/分析看板/回收站）、WordPress（仪表盘待办与最近活动、回收站、复制为新草稿、批量标签）、Hugo 生态（partialCached 构建提速、模板一致性、AEO/结构化数据）、静态 CMS（Decap/Keystatic 的 Git 工作流、内容体检）、Docker 安全基线（no-new-privileges/只读根文件系统/资源限制）。

## 热修复（2026-08-19，v200 之后）

**现象：** 部署新 compose（只读根文件系统）后，所有预览/全量构建失败；修复一轮后仍报 `read-only file system`。

**根因（多层，均已实测复现）：**
1. `scripts/build.py` 对 `.build-tmp`/`.preview-out` 执行 `shutil.rmtree`，目录为 tmpfs 挂载点时 `rmdir` 返回 `EBUSY`（Device or resource busy），构建直接退出码 2。
2. tmpfs 默认 root 属主，应用以 UID 1000 运行时 Hugo 对目标目录 `chtimes` 报 `operation not permitted`。
3. 只读根文件系统且无 tmpfs 的部署中，Hugo 默认缓存 `/tmp/hugo_cache`、`--cacheDir` 目标、`--gc` 的 `/app/resources` 基目录均不可写，报 `read-only file system`。

**修复：**
- `scripts/build.py` 新增 `clear_tree()`：整树删除失败时回退为仅清空目录内容；`tmp.mkdir(exist_ok=True)` 兼容保留的挂载点。
- 构建临时目录（`BUILD_TMP_ROOT`）、预览输出（`PREVIEW_ROOT`）、Hugo 缓存（`HUGO_CACHEDIR`）全部改为环境变量可控并指向 `data/` 命名卷；compose 不再依赖 tmpfs。
- `compose.yaml` 新增 `blog-resources` 命名卷挂载到 `/app/resources`，满足 Hugo `--gc` 的可写基目录；`scripts/docker-entrypoint.sh` 把 `/app/.build-tmp`、`/app/resources` 纳入属主修复循环。
- 后台预览失败 flash 附带构建 stderr 末尾 200 字，便于后续定位。

**验证：** 127 项测试全绿（新增 `test_clear_tree_tolerates_mountpoint`、`test_build_tmp_and_preview_env_overrides`）；只读根文件系统 + 无 tmpfs + data/resources 卷挂载场景 `--preview` 与 `--full` 均 `build OK`（357 页/534 文件）；`docker compose config -q` 通过；新镜像 `liblog-admin:round3-fix2` 复测通过。

## 系列路线图

| 版本区间 | 系列 | 主题 |
| --- | --- | --- |
| v101–v106 | 基建 | 第三轮日志、开发工具、构建清单、自动缓存指纹、产物校验强化 |
| v107–v120 | SEO/AEO | OG 图片宽高、article 元数据、ProfilePage/Organization/ItemList JSON-LD、列表面包屑、定制分页、归档页、图片 caption |
| v121–v135 | 性能/无障碍 | partialCached、color-scheme、搜索输入属性与防抖、搜索索引瘦身、nginx 缓存与 TLS 模板 |
| v136–v150 | 后台工作流 | 仪表盘最近活动/体检提醒/定时文章、回收站、复制为新草稿、定时发布、SEO 检查面板、预览设备切换、快捷键帮助、slug 即时校验 |
| v151–v165 | 后台效率 | 媒体未引用筛选、批量加标签、每页条数、统计路径标题化、备份记录、配置前端校验、全局搜索、字数增强、表格工具栏 |
| v166–v180 | 安全/构建/部署 | 草稿不泄漏校验、构建报告 JSON、compose 安全加固、Dockerfile 细化、CSP 补齐、会话轮换、测试覆盖、文档同步 |
| v181–v195 | 内容与治理 | README/MASTER/BRAND/AGENTS/.env 同步、依赖固定、web 构建校验、响应式/深色/键盘回归 |
| v196–v200 | 收尾 | 对比度/硬编码/性能/安全审计、日志整理、最终基线提交 |

## 迭代日志

| # | 系列 | 改动 | 状态 | 验证证据 |
| --- | --- | --- | --- | --- |
| v101 | 基建 | 建立本日志与第三轮路线图；记录 114 项测试基线 | 完成 | 本文件；`python -m unittest discover -s tests -q` 114 OK |
| v102 | 基建 | 新增 Makefile 与 .editorconfig 标准开发入口 | 完成 | make test/check/build/web-build/audit 可执行；.editorconfig 统一缩进 |
| v103 | 基建 | 构建产物自动缓存指纹（config/build.yaml 替代手写 ?v=） | 完成 | 产物 index.html 输出 `tokens.css?v=7b86410dbe`；后台 render() 读取同一指纹 |
| v104 | 构建 | verify_output 增加草稿/未来文章泄漏校验 | 完成 | 新增 2 项测试；输出验证 0 错误 |
| v105 | 构建 | build.py 支持 --metrics 模板性能报告 | 完成 | `--metrics` 透传 Hugo --templateMetrics/--templateMetricsHints |
| v106 | SEO | OG 图片补 width/height/type | 完成 | /posts/ 输出 og:image:width/height/type（logo 实测 1265×1265） |
| v107 | SEO | article:section / article:author 元数据 | 完成 | 文章页输出 section 与 author 元信息 |
| v108 | SEO | 关于页 ProfilePage JSON-LD；全站 Organization JSON-LD | 完成 | /about/ 含 ProfilePage/Person/knowsAbout；首页含 Organization |
| v109 | SEO | 列表/标签页 ItemList JSON-LD | 完成 | /posts/、/posts/page/2/、/tags/ 均含 ItemList |
| v110 | SEO | 列表/标签/项目/时间线页可见面包屑 | 完成 | 5 类列表页输出 class=breadcrumb；aria-label 走 strings.yaml |
| v111 | 内容 | 定制分页（首/末页、页码序列、aria） | 完成 | /posts/page/2/ 含 rel=prev/next、页码序列与 aria-label |
| v112 | 内容 | /archive/ 归档页（按年分组与计数） | 完成 | 构建 357 页；/archive/ 输出年份分组与日期列表；页脚加入口 |
| v113 | 内容 | 图片渲染钩子支持 caption 与 alt 兜底 | 完成 | 构建通过；title 参数渲染 figure/figcaption，空 alt 用文件名 |
| v114 | 内容 | 文章封面/卡片图补 width/height 防 CLS | 完成 | 单页/卡片封面输出 width/height（imageConfig 实测） |
| v115 | 性能 | 静态资源 partialCached 构建提速 | 完成 | density/css-ambient/asset-versions 均 partialCached；构建 344ms/357 页 |
| v116 | 性能 | color-scheme meta；搜索输入 enterkeyhint/spellcheck/role | 完成 | head 输出 color-scheme；搜索框 autocapitalize/autocorrect/spellcheck/enterkeyhint 齐全 |
| v117 | 性能 | nginx open_file_cache 与 favicon/robots/llms 缓存 | 完成 | open_file_cache 4 项 + 2 条 location 缓存；nginx -t 通过 |
| v118 | 安全 | nginx HTTPS 模板补 http2/TLS 会话/现代套件 | 完成 | 模板含 http2/会话缓存/现代 cipher/HSTS；nginx -t 通过 |
| v119 | 性能 | 搜索防抖与计数播报完善 | 完成 | 80ms 防抖；结果计数 role=status 播报保留 |
| v120 | 性能 | 搜索索引瘦身（摘要限长/字段裁剪） | 完成 | 摘要截断 180 字符；search/index.json 22KB 构建通过 |
| v121 | 后台 | 仪表盘最近活动（审计日志 8 条） | 完成 | 仪表盘输出最近活动列表；121 测试全绿 |
| v122 | 后台 | 仪表盘内容体检提醒卡 | 完成 | 仪表盘显示严重/提醒计数并链到 /audit |
| v123 | 后台 | 仪表盘定时/未来文章提示 | 完成 | 未来日期文章列表入仪表盘并标注日期 |
| v124 | 后台 | 文章回收站（软删除/恢复/清空） | 完成 | data/trash 跨文件系统移动；/trash 页 + 3 路由 + 2 项测试 |
| v125 | 后台 | 复制为新草稿 | 完成 | /duplicate 路由自动去重 slug 并转草稿；1 项测试 |
| v126 | 后台 | 定时发布状态（scheduled）与提示 | 完成 | 列表 status=scheduled 筛选 + 定时徽章；构建校验防未来泄漏 |
| v127 | 后台 | 编辑器 SEO 检查面板 | 完成 | 标题长度/摘要/标签/封面/slug/字数检查入编辑页 |
| v128 | 后台 | 预览设备宽度切换（移动/平板/桌面） | 完成 | 预览头三档按钮切换 iframe 宽度 |
| v129 | 后台 | 编辑器快捷键帮助（?） | 完成 | ? 与按钮打开快捷键 dialog |
| v130 | 后台 | slug 唯一性即时检查 | 完成 | /{section}/slug-check JSON + 250ms 防抖提示；1 项测试 |
| v131 | 后台 | 重复标题即时警告 | 完成 | 编辑页内嵌标题清单，输入时提示同名文章 |
| v132 | 后台 | 媒体库未引用筛选 | 完成 | content/config 引用扫描；unused=1 过滤 + 未引用计数；1 项测试 |
| v133 | 后台 | 批量加标签/清除标签 | 完成 | bulk 支持 add_tag/remove_tag + datalist；1 项测试 |
| v134 | 后台 | 批量操作栏移动端吸底 | 完成 | 768px 下 sticky bottom 批量栏（令牌阴影） |
| v135 | 后台 | 统计路径映射文章标题 | 完成 | 统计表已知路径显示标题，原路径作标签 |
| v136 | 后台 | 备份页显示最近备份/恢复记录 | 完成 | backup_download/restore 审计 + 最近 10 条展示 |
| v137 | 后台 | 配置表单 YAML 前端语法校验 | 完成 | 键值行校验 + is-invalid 样式 |
| v138 | 后台 | 后台全局快速跳转搜索框 | 完成 | 侧栏过滤导航，Enter 直达首个匹配 |
| v139 | 后台 | 编辑字数统计区分中英文 | 完成 | 中文逐字 + 拉丁词数 + 预计分钟 |
| v140 | 后台 | 编辑器插入表格工具栏 | 完成 | data-md=table 插入 2×2 Markdown 表格 |
| v141 | 后台 | 自动保存冲突检测（多标签页） | 完成 | storage 事件提示加载另一标签页草稿 |
| v142 | 后台 | 后台页面标题统一为「栏目 · Li&Blog 后台」 | 完成 | 15 个模板补齐 block title |
| v143 | 后台 | 媒体库月份分组显示图片数 | 完成 | 分组标题为「媒体库 YYYY-MM（N 张）」 |
| v144 | 内容 | 文章列表卡片补更新日期 | 完成 | 卡片 meta 在 Lastmod 与 Date 不同日时输出「更新于」 |
| v145 | 内容 | 时间线列表按年份分组 | 完成 | /timeline/ 输出 timeline-year 分组（2026 一组） |
| v146 | 内容 | 项目卡补日期与状态徽章 | 完成 | 项目卡输出 time 与 badge-primary 状态胶囊 |
| v147 | 内容 | 文章列表按年份分组 | 完成 | /posts/ 输出 list-year-heading 年份标题 |
| v148 | 内容 | RSS 全文/摘要开关 | 完成 | hugo.toml `rss_full=false`；输出验证无 content:encoded |
| v149 | 内容 | 404 页补时间线入口 | 完成 | 404 导航补历程链接（strings.nav.timeline） |
| v150 | 内容 | 搜索无结果时推荐标签 | 完成 | 无结果时按出现频次推荐 6 个标签链接 |
| v151 | 安全 | 登录成功清理匿名会话（防会话残留） | 完成 | 本地/OIDC 登录后删除 anon session；125 测试全绿 |
| v152 | 安全 | admin 中间件补 CSP 响应头 | 完成 | 后台响应含 form-action/frame-src 白名单 CSP |
| v153 | 安全 | 上传文件名规范强化（控制字符） | 完成 | slugify 过滤控制字符并限长 80 |
| v154 | 安全 | 修订恢复审计补齐 | 完成 | revision_restore 写入 audit_log |
| v155 | 构建 | build.py --report JSON 输出 | 完成 | 成功/失败报告文件；测试参数同步 |
| v156 | 构建 | 校验 sitemap 不含草稿 URL | 完成 | verify_output 扫 sitemap loc；新增 1 项测试 |
| v157 | 部署 | compose 安全加固（no-new-privileges/pids_limit） | 完成 | 双服务 security_opt + pids_limit；compose config 通过 |
| v158 | 部署 | admin/nginx 只读根文件系统 + tmpfs | 完成 | read_only + tmpfs（build-tmp/preview-out/nginx 缓存）；构建锁与 Hugo 缓存落 data 卷与 /tmp |
| v159 | 部署 | Dockerfile pip check + compileall | 完成 | builder pip check；runtime compileall admin/scripts |
| v160 | 部署 | nginx CSP 补 upgrade-insecure-requests | 完成 | nginx -t 通过 |
| v161 | 测试 | 新增仪表盘/统计映射/日志筛选路由测试 | 完成 | 3 项新测试（dashboard/stats/logs） |
| v162 | 测试 | 新增构建校验测试（sitemap 草稿） | 完成 | 1 项新测试；125 项全绿 |
| v163 | 文档 | README 第三轮特性同步 | 完成 | 归档/回收站/SEO 面板/只读加固入特性清单 |
| v164 | 文档 | MASTER.md 覆盖审计同步 | 完成 | archive/trash/seo-panel/device-preview 入组件与覆盖表 |
| v165 | 文档 | BRAND.md/AGENTS.md 边界同步 | 完成 | 派生内容口径 + make 验证命令 |
| v166 | 文档 | .env.example 新变量说明 | 完成 | HUGO_CACHEDIR/BUILD_LOCK_PATH + build.yaml 说明 |
| v167 | 依赖 | requirements.txt 固定版本审计 + pip check | 完成 | 10 个依赖全版本固定；Dockerfile pip check |
| v168 | 前端 | web 构建校验与体积报告 | 完成 | Makefile web-verify；npm build 40ms/278.5kb |
| v169 | 前端 | effects-react.js 产物回归构建 | 完成 | 重建后 git 无差异（确定性产物） |
| v170 | 可观测 | healthz 补构建清单信息 | 完成 | /healthz 返回 build.built_at/asset_count；测试更新 |
| v171 | 可观测 | 健康检查补媒体引用完整性 | 完成 | 缺失引用与未引用计数入 /admin/health |
| v172 | 可观测 | 操作日志分页与筛选 | 完成 | kind 筛选 + 100/页分页；2 项测试 |
| v173 | 可观测 | 统计 CSV 文件名带筛选范围 | 完成 | liblog-stats-{start}-{end}.csv |
| v174 | 内容 | 内容体检补封面引用缺失 | 完成 | 封面 /img|/assets 缺失入 danger |
| v175 | 内容 | 内容体检补未来日期提示 | 完成 | 未来日期文章入 warning |
| v176 | 内容 | 编辑页修订历史显示可读时间 | 完成 | YYYYMMDD-HHMMSS → 格式化标签 |
| v177 | 内容 | 导入结果按成功/失败分组可折叠 | 完成 | details/summary 折叠成功表与失败明细 |
| v178 | 内容 | 媒体库缩略图加载失败占位 | 完成 | onerror 加 table-thumb-missing「图片缺失」 |
| v179 | 内容 | 保存留在本页后预览自动刷新 | 完成 | 带 ok 参数时 iframe 载入 preview_path?raw=1 |
| v180 | 内容 | 公开站文章底部补许可声明 | 完成 | strings.common.license_prefix + 页脚许可链接 |
| v181 | 回归 | 公开站移动端新组件走查 | 完成 | 480px 补齐归档/面包屑/许可/搜索模态规则；构建通过 |
| v182 | 回归 | 后台移动端新组件走查 | 完成 | 768px 补 preview-devices/seo-panel/nav-filter 规则 |
| v183 | 回归 | 深浅色新组件走查 | 完成 | 后台补 color-scheme meta；全部走语义令牌 |
| v184 | 回归 | 键盘导航新组件走查 | 完成 | 快捷键按钮 aria-keyshortcuts=?；后台全局 focus-visible |
| v185 | 回归 | 对比度审计通过 | 完成 | check_contrast.py：全部关键文本对 ≥ 4.5:1 |
| v186 | 回归 | 硬编码审计通过 | 完成 | check_hardcoded.py：模板零硬编码颜色 |
| v187 | 回归 | 性能审计更新 | 完成 | PERF-AUDIT.md：306ms/534 文件/278.5KB 效果包 |
| v188 | 回归 | 安全审计更新 | 完成 | SECURITY-AUDIT.md：CSP/只读容器/会话清理/回收站 |
| v189 | 回归 | 全量测试 + 构建回归 | 完成 | 126 项测试全绿；容器 Hugo 305ms，verify 0 错误 |
| v190 | 回归 | 容器真实构建验证 | 完成 | docker build liblog-admin:round3 成功；uid=1000、依赖与 Hugo v0.165.0 验证通过 |
| v191 | 收尾 | 日志完整回填 | 完成 | 本表 v101–v200 全部回填 |
| v192 | 收尾 | 本轮 diff 统计与基线快照 | 完成 | 5 commits / 65 files / +1844 −78（相对 v100 基线 f052f49） |
| v193 | 收尾 | 提交并打 tag | 完成 | tag v200-optimization |
| v194 | 收尾 | 搜索模态移动端全屏化 | 完成 | 480px 下 search-modal-panel inset 8px |
| v195 | 收尾 | 后台全局 focus-visible 样式 | 完成 | admin-body 下 a/button/input/select/textarea/summary 焦点环 |
| v196 | 收尾 | 打印样式补面包屑隐藏 | 完成 | @media print 隐藏 .breadcrumb |
| v197 | 收尾 | 定时文章「立即发布」 | 完成 | publish-now 路由改日期为今天并发布；1 项测试 |
| v198 | 收尾 | SEO 面板显示定时倒计时 | 完成 | days_until>0 时提示「距定时发布还有 N 天」 |
| v199 | 收尾 | 回收站分栏统计卡 | 完成 | 文章/项目/时间线各自回收数量卡片 |
| v200 | 收尾 | 最终基线提交 | 完成 | 126 测试 + 审计 + 容器构建 + tag v200-optimization |

## 验证标准（每版必过）

- 单元测试：`.venv/bin/python -m unittest discover -s tests -q` 全绿（新增功能同步补测试）。
- Hugo 构建：仓库内置 v0.165.0 二进制经 `scripts/build.py --full` 成功且 `verify_output` 空错误。
- 模板规范：无新增硬编码 hex/可见文案；新增可见内容同步后台编辑入口并回写 MASTER.md。
- 安全底线：公开站零交互入口不变；备案号不引入假占位；后台不收集访客个人信息。
