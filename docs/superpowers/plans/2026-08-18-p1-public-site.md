# P1 公开站实施计划（Hugo 分段构建 + 容器化工具链）

> **For agentic workers:** REQUIRED SUB-SKILL: 本计划在单一会话内联执行；如拆分子任务使用 superpowers:subagent-driven-development。步骤用 `- [ ]` 追踪。

**Goal:** 产出可构建、可发布、低占用的 Hugo 公开站：主题骨架、内容结构、分段编排壳，全部验证通过。

**Architecture:** Hugo 生成静态站（Goldmark + Chroma），Python 薄壳做校验→渲染→原子发布→清理；Hugo 二进制只存在于容器镜像内（admin 镜像内置），不依赖宿主机工具链；公开站零交互、零硬编码可见文案。

**Tech Stack:** Hugo extended v0.165.0 固定版本二进制（admin 镜像 Dockerfile 下载安装，禁止第三方 Hugo 镜像）、Python 3 stdlib + PyYAML、Docker Compose（nginx + admin profiles）、Fuse.js（P4 引入，本阶段仅生成搜索 JSON）。

## Global Constraints

- Hugo extended；渲染只用 Hugo（Goldmark + Chroma + shortcodes），禁止 Python-Markdown/Pygments 渲染链路
- 构建内存：`GOMEMLIMIT=256MiB HUGO_NUMWORKERMULTIPLIER=0.5`；构建只写临时目录，校验通过才原子发布
- 公开站零交互；模板零硬编码可见文案，全部来自 `config/*.yaml`
- 令牌唯一出处 `themes/blog-theme/static/css/tokens.css`（`--liblog-*`），组件样式放 `style.css`
- 分页 20 篇/页；首页最新 5 篇；搜索 JSON 只含 title/url/summary/tags
- 备案号留空；Logo/favicon 留空（品牌色文字占位）
- 内容渲染单一出处：Hugo（后台预览同样走 Hugo，P2 实现）
- Hugo 固定版本二进制：生产环境由 admin 镜像 Dockerfile 下载 v0.165.0 并校验 checksum；本地验证用 `HUGO_BIN=/tmp/hugo-bin`；禁止 klakegg/peaceiris 等第三方 Hugo 镜像

---

### Task 1: Hugo 工程骨架与配置

**Files:**
- Create: `hugo.toml`
- Create: `themes/blog-theme/theme.toml`

**Interfaces:**
- Produces: 站点根配置；`dataDir = "config"` 使 `config/*.yaml` 以 `.Site.Data.brand/.profile/.homepage/.strings` 可用；输出格式 `search`（JSON）。

- [ ] **Step 1: 创建 hugo.toml**

```toml
baseURL = "https://blog.example.com/"
title = "Li&Blog"
theme = "blog-theme"
dataDir = "config"
defaultContentLanguage = "zh-cn"
enableRobotsTXT = true

[pagination]
pagerSize = 20

[taxonomies]
tag = "tags"

[markup.goldmark.renderer]
unsafe = true

[markup.highlight]
codeFences = true
lineNos = true
lineNumbersInTable = false
noClasses = false
style = "friendly"

[outputs]
home = ["HTML", "RSS"]

[outputFormats.Search]
mediaType = "application/json"
baseName = "index"
isPlainText = true
notAlternativeFormats = true

[params]
themeKey = "liblog-theme"
```

- [ ] **Step 2: 创建 theme.toml**

```toml
name = "blog-theme"
license = "MIT"
min_version = "0.140.0"
```

- [ ] **Step 3: 验证**

Run: `/tmp/hugo-bin config | head -20`
Expected: 输出含 `theme = "blog-theme"`、`dataDir = "config"`。

- [ ] **Step 4: Commit**

```bash
git add hugo.toml themes/blog-theme/theme.toml
git commit -m "chore: Hugo 工程骨架与配置"
```

---

### Task 2: 基础模板与令牌样式

**Files:**
- Create: `themes/blog-theme/layouts/_default/baseof.html`
- Create: `themes/blog-theme/layouts/partials/head.html`
- Create: `themes/blog-theme/layouts/partials/header.html`
- Create: `themes/blog-theme/layouts/partials/footer.html`
- Create: `themes/blog-theme/layouts/partials/badge.html`
- Create: `themes/blog-theme/static/css/style.css`

**Interfaces:**
- Produces: `baseof` 骨架；`badge.html` 参数 `label, href, color`（color 为空时用 `--liblog-primary`）；页脚从 `.Site.Data.brand` 读取版权/备案。

- [ ] **Step 1: baseof.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>{{ partial "head.html" . }}</head>
<body>
  {{ partial "header.html" . }}
  <main class="page-shell">{{ block "main" . }}{{ end }}</main>
  {{ partial "footer.html" . }}
</body>
</html>
```

- [ ] **Step 2: head.html**：meta viewport、description（brand.tagline）、theme-color（`#f6fbf9` / 深 `#3a3f45`）、tokens.css + style.css、条件加载 KaTeX/Mermaid（`page.Params.math/mermaid`）。
- [ ] **Step 3: header.html**：导航从 `.Site.Data.strings.nav` 渲染，链接 `/` `/posts/` `/projects/` `/timeline/` `/about/` `/resources/`；Logo 区：brand.name 首字母占位 + name。
- [ ] **Step 4: footer.html**：版权（brand.copyright 中 `{year}` 替换当前年）、ICP 号 + `brand.icp_url` 链接、公安号 + `brand.police_url`；为空则不渲染。
- [ ] **Step 5: badge.html**

```html
{{ $color := .color | default "var(--liblog-primary)" }}
<span class="badge"><span class="badge-dot" style="background:{{ $color }}"></span><a href="{{ .href }}">{{ .label }}</a></span>
```

- [ ] **Step 6: style.css**：使用 `--liblog-*` 实现 `.badge/.card/.post-card/.project-card/.timeline/.page-shell/.nav/.footer/.code-block/.admonition`；正文对比度满足 AA；`prefers-reduced-motion` 单帧。
- [ ] **Step 7: 验证**

Run: `/tmp/hugo-bin --gc --destination /tmp/hugo-out`
Expected: exit 0；输出 index.html 含 `.page-shell`。

---

### Task 3: 内容结构与示例文档

**Files:**
- Create: `content/posts/{k8s-single-node-note,fastapi-oidc-pkce,ansible-pitfall}.md`
- Create: `content/projects/{lipass,lichat,lidesign,liabout,liblog}.md`
- Create: `content/timeline/_index.md` + 6 个节点文件
- Create: `content/about.md`、`content/resources.md`、`content/search.md`

**Interfaces:**
- Produces: frontmatter 约定——文章 `title/date/tags/summary/draft/math/mermaid`；项目 `title/repo/tech/status/badge/show_on_home/summary/article`；时间线 `title/date/kind/summary`。

- [ ] **Step 1: 3 篇示例文章**（真实且不编造经历：本站架构说明、Markdown 语法指南、文章类型与写作约定；含表格、代码块、`{{< note >}}`）。
- [ ] **Step 2: 5 个项目卡**（四兄弟项目 + Li&Blog 自身；badge 字段含 label/color/href）。
- [ ] **Step 3: 时间线**：`_index.md` + 6 个节点（2026-01 起：Linux → Docker → K8s → Li&Pass → Li&Chat → Li&Blog）。
- [ ] **Step 4: about/resources/search**：about 长文 + 技能引用；resources 条目；search.md 仅输出 JSON（frontmatter `outputs: ["SEARCH"]`）。
- [ ] **Step 5: 验证**

Run: `python3 - <<'EOF'
import yaml, pathlib
for p in pathlib.Path("content").rglob("*.md"):
    txt = p.read_text()
    if txt.startswith("---"):
        yaml.safe_load(txt.split("---",2)[1])
print("frontmatter OK", len(list(pathlib.Path("content").rglob("*.md"))), "docs")
EOF`
Expected: `frontmatter OK 17 docs`（3+5+7+2+1 略大于等于 17，按实际数量输出即可，无异常）。

---

### Task 4: 首页模板

**Files:**
- Create: `themes/blog-theme/layouts/index.html`
- Create: `themes/blog-theme/layouts/partials/post-card.html`
- Create: `themes/blog-theme/layouts/partials/project-card.html`

**Interfaces:**
- Consumes: `.Site.Data.profile/.homepage/.strings/.brand`；`.Site.RegularPages`（文章）、`where .Site.RegularPages "Section" "projects"`。

- [ ] **Step 1: index.html 五区块**：Hero（brand/profile/homepage 数据）→ 项目徽章行（projects 中 `show_on_home` 为真，badge 渲染）→ 技能徽章行（profile.skills，limit=homepage.hero.skills_limit）→ 历程速览（timeline 最新 `preview_count` 条）→ 项目卡（`max_cards`）→ 最新文章（`latest_count`）。
- [ ] **Step 2: post-card/project-card 局部件**：标题/日期/摘要/标签链接；项目卡含技术栈徽章与状态。
- [ ] **Step 3: 验证**

Run: `/tmp/hugo-bin --gc --destination /tmp/hugo-out`
Expected: exit 0；index.html 含 `一次记录，见证每一步成长`、`Docker` 徽章、至少 4 个项目卡。

---

### Task 5: 列表、详情与分区模板

**Files:**
- Create: `themes/blog-theme/layouts/_default/list.html`
- Create: `themes/blog-theme/layouts/_default/single.html`
- Create: `themes/blog-theme/layouts/projects/list.html`
- Create: `themes/blog-theme/layouts/timeline/list.html`
- Create: `themes/blog-theme/layouts/shortcodes/note.html`

**Interfaces:**
- Consumes: `.Paginator`（20/页）、`.TableOfContents`、`.Content`、`.Params.*`。

- [ ] **Step 1: list.html**：标题 + `.Paginator.Pages` 渲染 post-card + 分页器（上一页/下一页）。
- [ ] **Step 2: single.html**：面包屑（strings.common.back）、标题、日期、标签、TOC（文章页）、`.Content`。
- [ ] **Step 3: projects/list.html**：项目卡网格；timeline/list.html：纵向时间轴（date/kind/summary）。
- [ ] **Step 4: note.html**

```html
{{ $type := .Get 0 | default "note" }}
<div class="admonition admonition-{{ $type }}">{{ .Inner | markdownify }}</div>
```

- [ ] **Step 5: 验证**

Run: `/tmp/hugo-bin --gc --destination /tmp/hugo-out && find /tmp/hugo-out -name '*.html' | wc -l`
Expected: exit 0；HTML 数量 ≥ 20（含分页）。

---

### Task 6: 搜索 JSON 模板

**Files:**
- Create: `themes/blog-theme/layouts/_default/single.search.json`

**Interfaces:**
- Produces: `content/search.md` 渲染为 `/search/index.json`，字段 `title/url/summary/tags`。

- [ ] **Step 1: 模板**

```json
[{{ range $i, $p := where .Site.RegularPages "Section" "posts" }}{{ if $i }},{{ end }}{{ dict "title" $p.Title "url" $p.RelPermalink "summary" $p.Summary "tags" $p.Params.tags | jsonify }}{{ end }}]
```

- [ ] **Step 2: 验证**

Run: `/tmp/hugo-bin --gc --destination /tmp/hugo-out && python3 -c "import json; d=json.load(open('/tmp/hugo-out/search/index.json')); print(len(d), d[0]['title'])"`
Expected: 输出 `3 <首篇标题>` 且 JSON 可解析。

---

### Task 7: 分段编排壳

**Files:**
- Create: `scripts/build.py`
- Create: `tests/test_build.py`

**Interfaces:**
- Produces: CLI `python3 scripts/build.py --full|--preview`；函数 `validate_content(root)`、`publish(src, dst)`、`run_build(root, hugo_cmd, dst, memory_limit)`。

- [ ] **Step 1: 测试先行**

```python
import tempfile, unittest, pathlib
from scripts.build import validate_content, publish

class TestBuild(unittest.TestCase):
    def test_validate_rejects_bad_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)/"bad.md"; p.write_text("---\ntitle: [broken\n---\n")
            errs = validate_content(pathlib.Path(d))
            self.assertTrue(any("frontmatter" in e for e in errs))
    def test_publish_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d)/"src"; src.mkdir(); (src/"a.html").write_text("x")
            dst = pathlib.Path(d)/"dst"; dst.mkdir(); (dst/"old.html").write_text("y")
            publish(src, dst)
            self.assertTrue((dst/"a.html").exists()); self.assertFalse((dst/"old.html").exists())
```

- [ ] **Step 2: 运行测试确认失败**（`python3 -m unittest tests/test_build.py -v`，Expected: FAIL import 不存在）
- [ ] **Step 3: 实现 build.py**：`validate_content` 解析 frontmatter 与内部链接；`run_build` 用 `env={"GOMEMLIMIT": os.environ.get("GOMEMLIMIT","256MiB"), "HUGO_NUMWORKERMULTIPLIER":"0.5"}` 调 `hugo --gc --destination <tmp>`；`publish` 用 `os.replace` 目录交换实现原子发布；`--preview` 加 `--buildDrafts`。
- [ ] **Step 4: 测试通过**（`python3 -m unittest tests/test_build.py -v`，Expected: 2 pass）
- [ ] **Step 5: 端到端**

Run: `GOMEMLIMIT=256MiB /usr/bin/time -l /tmp/hugo-bin --gc --destination /tmp/hugo-out 2>&1 | tail -8`
Expected: exit 0；`maximum resident set size` ≤ 256MB 量级；随后 `python3 scripts/build.py --full`（本地 docker 包装版）输出同款产物。

---

### Task 8: 验收与提交

- [ ] **Step 1: 全量验收**

Run:
```bash
/tmp/hugo-bin --gc --destination /tmp/hugo-out
rg -n "一次记录，见证每一步成长" /tmp/hugo-out/index.html
rg -n "Li&Pass|Li&Chat|Li&Design|Li&About" /tmp/hugo-out/projects/index.html
rg -n "TODO|TBD|\{\{" themes content config scripts || true
```
Expected: exit 0；首页含 tagline；项目页含四兄弟项目；无 TODO/TBD/`{{` 残留（shortcode `{{<` 除外需人工核对输出为空）。

- [ ] **Step 2: 更新设计文档**：MASTER.md 组件清单增加 `hugo-build（容器内）`、AGENTS.md 构建约束注明"Hugo 只存在于容器镜像内"。
- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: P1 公开站——Hugo 主题、内容结构、分段编排壳"
```
