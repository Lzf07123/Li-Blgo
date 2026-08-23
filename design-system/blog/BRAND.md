# Li&Blog 品牌方案（BRAND.md）

> 版本：v1.4 ｜ 日期：2026-08-24 ｜ 状态：设计定稿 + 视觉重构
> 来源：实例化自 Li-Design V1.5 可复用品牌模板（git 子模块 `design-system/Li-Design`）；令牌值已与 `reusable-tokens.template.css` 逐项核对（含 V1.5 页脚组件规格），另含打印/代码高亮/CTA 等本站扩展

## 1. 品牌内核（继承 Li& 家族，跨项目不变层）

### 1.1 定位与人格

| 维度 | 内容 |
| --- | --- |
| 一句话定位 | 一次记录，见证每一步成长 |
| 人格关键词 | 安静、可信、克制、清晰、可靠 |
| 人格比喻 | 一位安静的同行者：不喧哗，只把走过的路清楚摆在你面前 |
| 品牌承诺 | 每一篇都是真实足迹，每次回顾都有迹可循 |
| 避免成为 | 营销号、技术炫技页、冷冰冰的文档站 |

### 1.2 五大原则（TRUST 内核）

1. **信任优先**：只写真实信息，不编造熟练度、数据与链接；技术徽章只列实际掌握的技术。
2. **淡色科技感**：中性/淡色底 + 单一主色强调；全淡色系、无粉色、无大面积重色；海玻璃主色。
3. **以动衬静**：氛围动效极慢、极淡、CSS-only；尊重 `prefers-reduced-motion`；阅读页零动效。
4. **单一事实来源**：颜色/间距/阴影/动效只存在令牌 CSS；品牌文案只存在 `config/brand.yaml`；个人资料只存在 `config/profile.yaml`；站点文案只存在 `config/strings.yaml`；组件与模板禁止硬编码。
5. **无障碍与节能**：正文对比度 ≥ 4.5:1；焦点环可见；移动端减量；公开站无任何交互入口。

### 1.3 视觉语法：几何暗线

| 符号 | 语义映射（本博客） | 用法 |
| --- | --- | --- |
| 细直线 | 学习路径 | 背景层低频穿行 |
| Z 形折线 | 关键转折 | 首页 2–3 个，其余页面最多 1 个 |
| 方块 | 项目成果 | 往复钟摆，稳定存在感 |
| 锁钥组合 | 后台入口（仅 admin 登录页） | 稀有元素 |
| 圆点光斑 | 笔记/知识点 | 盘旋公转，活跃但安静 |

符号铁律：低透明度（0.04–0.25）、背景层、几何、无渐变/阴影/滤镜、不与文字与表格冲突、不作为功能图标。

## 2. 22 槽位（已填定）

| # | 槽位 | 值 |
| --- | --- | --- |
| 1 | 项目显示名 | Li&Blog |
| 2 | 技术标识 | liblog |
| 3 | 一句话定位 | 一次记录，见证每一步成长 |
| 4 | 品牌承诺 | 每一篇都是真实足迹，每次回顾都有迹可循 |
| 5 | 人格比喻 | 安静的同行者 |
| 6 | 符号隐喻 | 见 §1.3 |
| 7 | 主色（浅） | #25786D / hover #1F6359 / soft #D9F4EE / fg #FFFFFF |
| 8 | 主色（深） | #7FD4C6 / hover #A5E4D9 / soft rgba(127,212,198,.16) / fg #17332E |
| 9 | 中性色（浅） | #F6FBF9 / #FFFFFF / #EEF6F3 / #35423F / #64736C / #E1ECE8 |
| 10 | 中性色（深） | #3A3F45 / #434950 / #4B5259 / #F0F2F4 / #B8C0C7 / #545C64 |
| 11 | 语义色 | Li-Design V1.5 调校值：success #2A7C52 / warning #9A5C05 / destructive #C43737（深色 #86D6AC / #EAD48E / #E8A49A，各配 soft；深色带文字组件回退 soft-solid / soft-fg） |
| 12 | 焦点环 | 浅 #25786D / 深 #7FD4C6，2px 描边 + 2px offset |
| 13 | 字体栈 | Inter → ui-sans-serif/system → PingFang SC / Hiragino Sans GB / 微软雅黑；零远程加载 |
| 14 | 可选标题字体 | 暂不引入（保持最低占用） |
| 15 | Logo / favicon | 留空变量；上传至媒体库 `media/`（公开路径 `/img/`）；品牌内置资源放 `themes/blog-theme/static/assets/brand/`；512×512 透明底 WebP + favicon.webp；未上传时用品牌色文字占位 |
| 16 | 令牌前缀 | `--liblog-*` |
| 17 | 主题存储键 | liblog-theme（公开站跟随系统，无切换按钮；后台可切换） |
| 18 | slogan / 备案 | 只存 config/brand.yaml；备案上线前留空，禁止假占位号 |
| 19 | 氛围浓度 | 首页 4 / 内容页 0 / 后台 4×0.5；移动端减量 |
| 20 | 浏览器品牌位 | favicon、theme-color（明暗）、description、首帧主题脚本（跟随系统） |
| 21 | 强调色板 | 家族六色 strong/soft：ice/aqua/lilac/sage/mint/sand（值见 MASTER.md 令牌快照），仅小面积装饰 |
| 22 | 按钮与光效 | 按钮半透明单色（浅 10% / 深 13%）仅后台；公开站首页 Hero CTA 例外：阅读博客浅色主按钮（保留扫光）、关于我深色次按钮，颜色走 `--liblog-btn-light-*` / `--liblog-btn-dark-*` 令牌；光效 CSS-only，文章页禁用 |

派生内容口径（第三轮）：归档页、按年分组、标签页等均为内容派生页面，不新增品牌文案槽位；新增可见文案一律先入 config/strings.yaml，再在后台「页面文案」编辑。

取色说明：主色沿用家族海玻璃（Li&Pass 对比度调校后定稿 #25786D / #7FD4C6，代码事实优先于模板初值 #2F7F74）。

## 3. 氛围动效（呼吸感）

- 公开站：首页 full（Canvas + CSS 氛围）；栏目列表/关于/资源 soft 减量；文章详情 0（纯排版）
- 实现口径（第二轮优化定稿）：React 效果层仅首页加载；栏目/关于/资源为 CSS-only 减量氛围（不加载效果包）；文章详情零动效
- 打印：独立 `--liblog-print-*` 令牌，白纸黑字，不随主题变化
- 后台：4 元素 × 透明度 0.5（表格区保持不透明表面）
- 只动 transform/opacity/background-position；错峰 delay；`prefers-reduced-motion` 单帧；移动端减量
- Canvas 效果层（FloatingBackground）仅在 full/soft 页面加载，移动端形状上限 6、DPR 上限 2，`prefers-reduced-motion` 时收敛为单帧静态绘制

## 4. 文案语调

- 清晰优先：先告诉读者发生了什么、为什么、下一步
- 不用感叹号、不用网络流行语、不过度拟人化
- 数字与时间精确；错误信息可行动
- 技术名保持官方大小写：FastAPI、TypeScript、PostgreSQL、Kubernetes、Tailwind CSS

## 5. 徽章规范（站点版，与 README 区分）

- 公开站徽章一律本地生成（HTML/SVG 胶囊），禁止 shields.io 外链
- 技术栈徽章：浅色胶囊 + 官方品牌色圆点 + 名称 + 官网链接
- 项目徽章：家族语义色 + 名称 + 仓库/复盘链接
- 个人信息组件中的技能徽章：按个人设计 README 徽章标准本地实现——官方品牌色整块底 + 白字 + 本地 SVG 图标（simple-icons 路径，mask 渲染当前色）+ 官网链接（无 shields.io 外链）
- README（GitHub）按 Li&About 规范继续使用 shields.io 官方色整块徽章
- 理由：公开站需自包含、国内访问性能与全淡色口径；README 是开发者语境，两处各守各的规范

## 6. 治理与单一事实来源

| 层级 | 文件 | 职责 |
| --- | --- | --- |
| 品牌意图 | design-system/blog/BRAND.md（本文件） | 定位、原则、视觉方向、氛围标准 |
| 实现速览 | design-system/blog/MASTER.md | 令牌、组件、页面模式、覆盖审计 |
| 模板参考 | design-system/Li-Design/（git 子模块，V1.5，锁定提交 `e899414`） | 家族模板/组件规格/验收清单；仅参考，非运行时依赖 |
| 代码事实 | themes/blog-theme/static/css/tokens.css | 颜色/阴影/动效令牌唯一出处 |
| 品牌资产 | config/brand.yaml | 名称/slogan/承诺/Logo/备案唯一出处 |
| 个人资料 | config/profile.yaml | 姓名/身份/方向/目标/技能唯一出处 |
| 站点文案 | config/strings.yaml | 导航/区块标题/通用标签唯一出处 |

冲突裁决：代码事实优先，并同步回写 BRAND.md / MASTER.md。新视觉决策先写本文件意图，再以令牌落地。

## 6.1 变更记录

- 2026-08-21 认证页对齐 Li&Panel AuthShell：登录与设置向导底部补齐版权 + 备案（`auth-footer`，图标占位字符走 `strings.footer.icon_fallback`），令牌落地
- 2026-08-21 样式层迁移 Tailwind CSS 4：`tokens.css` 由 `web/src/tokens.css` 编译生成（与 Li&Panel `index.css` 同构：`@theme` + `--liblog-*`），页眉/页脚使用与 Panel 完全相同的 utility class，构建走 `npm run css`
- 2026-08-21 页眉页脚 1:1 对齐 Li&Panel（同款实现）：页眉按 AppHeader——sticky + 半透明表面 + backdrop-blur（`--liblog-header-*` 令牌）+ 品牌名 ShinyText 扫光 + `flow-rule` 1px 流光线 + `h-16`/`max-w-7xl`；页脚按 SiteFooter 单行——版权 + 声明 + 备案 + 归档 + 许可，`min-h-14`/`text-xs`；公开站不引入主题切换按钮（跟随系统，槽位 17）。
- 2026-08-24 移动端导航：首页/关于/搜索常驻页眉，文章/项目/历程/资源/友情链接收进二级菜单；桌面页眉资源后增加友情链接，页脚保留友情链接入口；友情链接仍属导航，不引入任何用户输入组件；外链统一经过站内安全提醒页确认后再打开，公开站继续保持零交互栏目。
- 2026-08-24 公开站视觉重构：更大留白与一致栅格、液态玻璃卡片（`--liblog-glass-*`）、首页/项目页 CSS 瀑布流（仅真实封面参与，未配图不显示占位）、卡片悬浮微交互、搜索微骨架屏、全站带插图的空状态；仍遵守公开站零输入、`prefers-reduced-motion` 收敛、颜色只进 tokens.css 的底线。

## 7. 使用边界

- 本方案已实例化，Li&Blog 不再依赖 Li-Design 模板仓库作为运行时依赖；`design-system/Li-Design/` 仅作模板参考（git 子模块，已对齐 V1.5 / `e899414`，后续升级需显式更新锁定提交）
- 允许偏离：主色按产品域调校（走家族取色方法）、符号隐喻重映射、确需新模式时先写 spec 再更新 MASTER.md
- 禁止偏离：五大原则、动效铁律、单一事实来源、无障碍/节能底线、公开站零交互、备案留空规矩
