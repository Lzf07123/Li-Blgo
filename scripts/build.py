#!/usr/bin/env python3
"""分段构建编排壳：校验 → Hugo 渲染（临时目录）→ 原子发布 → 清理。

生产环境在 admin 容器内执行（镜像内置 Hugo 固定版本二进制）；
本地验证可用 HUGO_BIN 指向任意同版本二进制。
"""

import argparse
import fcntl
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
    extra = list(extra)
    site_baseurl = os.environ.get("SITE_BASEURL", "").strip()
    if site_baseurl:
        extra += ["--baseURL", site_baseurl]
    subprocess.run(
        [hugo_cmd, "--gc", "--minify", "--destination", str(dst), *extra],
        cwd=root,
        env=env,
        check=True,
    )


def publish(src, dst):
    """逐文件原子同步到既有目录。

    保持 dst 目录 inode 稳定，兼容 Docker bind 挂载（整目录交换会令挂载失效）。
    """
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        shutil.copy2(p, tmp)
        os.replace(tmp, target)
    for p in dst.rglob("*"):
        if p.is_file():
            rel = p.relative_to(dst)
            if not (src / rel).exists():
                p.unlink()
    for p in sorted(dst.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            try:
                p.rmdir()
            except OSError:
                pass


def build(args):
    """执行 校验 → 渲染 → 发布 → 清理。"""
    errors = validate_content(ROOT)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    hugo_cmd = os.environ.get("HUGO_BIN", "hugo")
    memory_limit = os.environ.get("GOMEMLIMIT", "256MiB")
    extra = ("--buildDrafts",) if args.preview else ()
    dst = ROOT / (".preview-out" if args.preview else "output")
    if args.full and not os.environ.get("SITE_BASEURL", "").strip():
        print(
            "WARNING: SITE_BASEURL 未设置，canonical/OG/RSS 将使用相对 baseURL；部署前必须配置真实域名",
            file=sys.stderr,
        )
    tmp = ROOT / ".build-tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    run_build(ROOT, tmp, hugo_cmd=hugo_cmd, memory_limit=memory_limit, extra=extra)
    publish(tmp, dst)
    if not args.keep_tmp:
        shutil.rmtree(tmp)
    print(f"build OK -> {dst}")


def main():
    parser = argparse.ArgumentParser(description="Li&Blog 分段构建编排")
    parser.add_argument("--full", action="store_true", help="全量构建并发布到 output/")
    parser.add_argument("--preview", action="store_true", help="构建草稿到 .preview-out/")
    parser.add_argument("--keep-tmp", action="store_true", help="保留临时目录（调试）")
    args = parser.parse_args()

    lock_path = ROOT / ".build.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        build(args)


if __name__ == "__main__":
    main()
