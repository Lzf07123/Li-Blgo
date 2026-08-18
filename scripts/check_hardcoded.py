#!/usr/bin/env python3
"""单一事实来源抽查：公开站模板禁止硬编码颜色值（hex/rgba）。

颜色只允许出现在 themes/blog-theme/static/css/tokens.css；
模板内联样式只允许引用令牌变量（var(--liblog-*)）。
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUTS = ROOT / "themes" / "blog-theme" / "layouts"
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")


def check() -> list[str]:
    errors = []
    for p in sorted(LAYOUTS.rglob("*")):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "theme-color" in line:
                continue  # meta theme-color 必须内联字面值，值与 tokens.css 同步
            for m in COLOR_RE.finditer(line):
                errors.append(
                    f"{p.relative_to(ROOT)}:{line_no}: 硬编码颜色 {m.group(0)}"
                )
    return errors


def main() -> int:
    errors = check()
    if not errors:
        print("hardcoded color audit OK")
        return 0
    for err in errors:
        print(err, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
