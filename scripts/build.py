#!/usr/bin/env python3
"""分段构建编排壳：校验 → Hugo 渲染（临时目录）→ 原子发布 → 清理。

生产环境在 admin 容器内执行（镜像内置 Hugo 固定版本二进制）；
本地验证可用 HUGO_BIN 指向任意同版本二进制。
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def validate_content(root):
    """校验 content/ 下所有 Markdown 的 frontmatter 可解析。返回错误列表。"""
    import yaml

    errors = []
    for p in sorted((root / "content").rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if text.startswith("---"):
            try:
                yaml.safe_load(text.split("---", 2)[1])
            except Exception as exc:  # noqa: BLE001 - 统一收集为可读错误
                errors.append(f"{p.relative_to(root)}: frontmatter 解析失败: {exc}")
    return errors


def run_build(root, dst, hugo_cmd="hugo", memory_limit="256MiB", extra=()):
    """以受限内存运行 Hugo，构建到 dst（临时目录）。"""
    env = dict(os.environ)
    env.setdefault("GOMEMLIMIT", memory_limit)
    env.setdefault("HUGO_NUMWORKERMULTIPLIER", "0.5")
    subprocess.run(
        [hugo_cmd, "--gc", "--destination", str(dst), *extra],
        cwd=root,
        env=env,
        check=True,
    )


def publish(src, dst):
    """原子发布：目录交换 + 旧目录清理。"""
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)
    backup = dst.parent / (dst.name + ".old")
    if backup.exists():
        shutil.rmtree(backup)
    if dst.exists():
        os.replace(dst, backup)
    os.replace(src, dst)
    if backup.exists():
        shutil.rmtree(backup)


def main():
    parser = argparse.ArgumentParser(description="Li&Blog 分段构建编排")
    parser.add_argument("--full", action="store_true", help="全量构建并发布到 output/")
    parser.add_argument("--preview", action="store_true", help="构建草稿到 .preview-out/")
    parser.add_argument("--keep-tmp", action="store_true", help="保留临时目录（调试）")
    args = parser.parse_args()

    errors = validate_content(ROOT)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    hugo_cmd = os.environ.get("HUGO_BIN", "hugo")
    memory_limit = os.environ.get("GOMEMLIMIT", "256MiB")
    extra = ("--buildDrafts",) if args.preview else ()
    dst = ROOT / ("output" if not args.preview else ".preview-out")
    tmp = ROOT / ".build-tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    run_build(ROOT, tmp, hugo_cmd=hugo_cmd, memory_limit=memory_limit, extra=extra)
    publish(tmp, dst)
    if args.keep_tmp:
        print(f"tmp kept: {tmp}")
    print(f"build OK -> {dst}")


if __name__ == "__main__":
    main()
