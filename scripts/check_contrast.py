#!/usr/bin/env python3
"""令牌对比度审计：确保正文/界面关键文本对 ≥ 4.5:1（WCAG AA）。

只审计实色令牌对；半透明 soft 层仅作背景装饰，不作为正文承载面。
用法：python3 scripts/check_contrast.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAIRS = [
    # (mode, fg_token, bg_token, 说明)
    ("light", "fg", "bg", "正文/背景"),
    ("light", "muted", "bg", "弱化文字/背景"),
    ("light", "primary", "bg", "主色链接/背景"),
    ("light", "brand-fg", "surface", "品牌深字/卡片底"),
    ("light", "primary-fg", "primary", "主色按钮字/主色底"),
    ("light", "warning", "warning-soft", "警告文字/警示底"),
    ("light", "destructive", "destructive-soft", "危险文字/危险底"),
    ("light", "secondary", "secondary-soft", "次要链接/浅底"),
    ("dark", "fg", "bg", "正文/背景"),
    ("dark", "muted", "bg", "弱化文字/背景"),
    ("dark", "primary", "bg", "主色链接/背景"),
    ("dark", "primary-fg", "primary", "主色按钮字/主色底"),
    ("dark", "success", "bg", "成功文字/背景"),
    ("dark", "warning", "bg", "警告文字/背景"),
    ("dark", "destructive", "bg", "危险文字/背景"),
    ("dark", "secondary", "bg", "次要链接/背景"),
]

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _relative_luminance(hex_color: str) -> float:
    # Tailwind 压缩产物可能使用 #rgb 简写，先归一化为 6 位
    if len(hex_color) == 4:
        hex_color = "#" + "".join(ch * 2 for ch in hex_color[1:])
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]

    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    l1, l2 = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _extract_block(css: str, selector: str) -> dict[str, str]:
    """提取全部 :root / .dark 块内的 --liblog-* 实色令牌。

    tokens.css 由 Tailwind CSS 4 编译产出，同一选择器会出现多个块
    （theme 别名块 + 本站实色令牌块），合并时后者优先。
    """
    values = {}
    for match in re.finditer(re.escape(selector) + r"\s*\{(.*?)\}", css, re.DOTALL):
        for name, value in re.findall(
            r"--liblog-([a-z0-9-]+)\s*:\s*([^;]+);", match.group(1)
        ):
            value = value.strip()
            if HEX_RE.match(value):
                values[name] = value
    return values


def verify(css: str) -> list[tuple[str, str, str, str, float]]:
    """返回 [(mode, fg, bg, 说明, ratio)]，全部 ≥ 4.5 时为空列表。"""
    blocks = {
        "light": _extract_block(css, ":root"),
        "dark": _extract_block(css, ".dark"),
    }
    failures = []
    for mode, fg_name, bg_name, label in PAIRS:
        fg = blocks[mode].get(fg_name)
        bg = blocks[mode].get(bg_name)
        if not fg or not bg:
            failures.append((mode, fg_name, bg_name, f"令牌缺失（{label}）", 0.0))
            continue
        ratio = contrast_ratio(fg, bg)
        if ratio < 4.5:
            failures.append((mode, fg_name, bg_name, label, ratio))
    return failures


def main() -> int:
    css = (ROOT / "themes" / "blog-theme" / "static" / "css" / "tokens.css").read_text(
        encoding="utf-8"
    )
    failures = verify(css)
    if not failures:
        print("contrast audit OK: 全部关键文本对 ≥ 4.5:1")
        return 0
    for mode, fg, bg, label, ratio in failures:
        print(f"FAIL [{mode}] {fg}/{bg} {label}: {ratio:.2f}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
