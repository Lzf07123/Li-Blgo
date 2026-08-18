# Li&Blog 性能审计记录

> 日期：2026-08-19 ｜ 数据来源：容器 Hugo v0.165.0 `--gc --minify` 实测

## 构建指标

| 指标 | 实测 |
| --- | --- |
| 页面数 | 356（含分页 9） |
| 构建耗时 | 408 ms |
| 产物体积 | 17 MB（533 个文件） |
| 峰值内存约束 | GOMEMLIMIT=256MiB（容器内 Hugo 自行受限） |

## 页面资源（公开站）

| 资源 | 体积 | 说明 |
| --- | --- | --- |
| tokens.css | 6.8 KB | 令牌唯一出处 |
| style.css | 35.4 KB | 公开站样式 |
| admin.css | 36.0 KB | 仅后台加载 |
| effects-react.js | 285 KB（gzip ≈ 90 KB） | 仅首页（v024 起栏目页不再加载） |
| fuse.min.js | 23.9 KB | 仅搜索模态打开时按需 fetch 索引 |
| search/index.json | 1.06 MB | 构建期生成，浏览器本地检索 |

## 性能策略清单

- HTML 不缓存（nginx `expires 0`），静态资源 7d 长缓存，搜索索引 5m。
- 图片：懒加载 + `decoding=async` + width/height（防 CLS）；首屏 Logo eager + fetchpriority=high。
- 渲染：`--minify`、`content-visibility`、`contain`、`text-wrap: balance`。
- 动效：React 仅首页；栏目页 CSS-only；文章页零效果；`prefers-reduced-motion` 全局收敛。
- 无外部 CDN/远程字体/远程 JS；Fuse.js 本地化。

## 结论

公开站为纯静态零请求外链页面，首页之外不加载效果运行时；LCP 主路径为内联首帧脚本 + 本地 CSS，无第三方阻塞。
