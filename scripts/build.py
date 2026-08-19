#!/usr/bin/env python3
"""分段构建编排壳：校验 → Hugo 渲染（临时目录）→ 原子发布 → 清理。

生产环境在 admin 容器内执行（镜像内置 Hugo 固定版本二进制）；
本地验证可用 HUGO_BIN 指向任意同版本二进制。
"""

import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

FINGERPRINT_FILES = {
    "css.tokens": "themes/blog-theme/static/css/tokens.css",
    "css.style": "themes/blog-theme/static/css/style.css",
    "css.admin": "themes/blog-theme/static/css/admin.css",
    "js.effects": "themes/blog-theme/static/js/effects-react.js",
    "js.fuse": "themes/blog-theme/static/js/fuse.min.js",
    "js.reading_progress": "themes/blog-theme/static/js/reading-progress.js",
    "js.admin_dropdown": "themes/blog-theme/static/js/admin-dropdown.js",
}


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


def validate_content_links(root):
    """校验 Markdown 内部链接与图片路径：站点路径映射到内容/静态文件存在性。

    动态路径（/tags/、外链、锚点）跳过；媒体路径校验 /img/ 与 /assets/。
    """
    errors = []
    content_root = root / "content"
    theme_static = root / "themes" / "blog-theme" / "static"
    site_static = root / "static"
    if not content_root.exists():
        return errors
    md_link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    html_href_re = re.compile(r'\bhref\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    html_src_re = re.compile(r'\bsrc\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    def check_url(rel_path: str, source: str) -> None:
        url = rel_path.strip().split()[0].strip("<>")
        if not url or url.startswith(("#", "http://", "https://", "mailto:", "data:")):
            return
        clean = url.split("#")[0].split("?")[0].rstrip("/")
        if clean.startswith(("/posts/", "/projects/", "/timeline/")):
            rel = clean.lstrip("/")
            candidates = [
                content_root / f"{rel}.md",
                content_root / rel / "_index.md",
                content_root / rel / "index.md",
            ]
            if not any(c.exists() for c in candidates):
                errors.append(f"{source}: 内部链接不存在 {url}")
        elif clean in ("/about", "/resources") or clean.startswith(
            ("/about/", "/resources/")
        ):
            name = clean.strip("/").split("/")[0]
            target = content_root / f"{name}.md"
            if not target.exists():
                errors.append(f"{source}: 内部链接不存在 {url}")
        elif clean.startswith(("/img/", "/assets/")):
            rel = clean.lstrip("/")
            found = any((base / rel).exists() for base in (theme_static, site_static))
            if not found:
                errors.append(f"{source}: 图片/资源不存在 {url}")

    for p in sorted(content_root.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        source = p.relative_to(root).as_posix()
        for m in md_link_re.finditer(text):
            check_url(m.group(1), source)
        for m in html_href_re.finditer(text):
            check_url(m.group(1), source)
        for m in html_src_re.finditer(text):
            check_url(m.group(1), source)
    return errors


def run_build(root, dst, hugo_cmd="hugo", memory_limit="256MiB", extra=(), metrics=False):
    """以受限内存运行 Hugo，构建到 dst（临时目录）。"""
    env = dict(os.environ)
    env.setdefault("GOMEMLIMIT", memory_limit)
    env.setdefault("HUGO_NUMWORKERMULTIPLIER", "0.5")
    extra = list(extra)
    site_baseurl = os.environ.get("SITE_BASEURL", "").strip()
    if site_baseurl:
        extra += ["--baseURL", site_baseurl]
    cache_dir = os.environ.get("HUGO_CACHEDIR", "").strip()
    if cache_dir:
        extra += ["--cacheDir", cache_dir]
    if metrics:
        extra += ["--templateMetrics", "--templateMetricsHints"]
    # 并发串行由本编排的 flock 保证，不再让 Hugo 写工作目录锁文件（兼容只读根文件系统）
    extra += ["--noBuildLock"]
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


def verify_output(dst, expect_absolute_urls=False, content_root=None):
    """抽检关键产物与占位符，返回错误列表。"""
    errors = []
    required = (
        "index.html",
        "index.xml",
        "sitemap.xml",
        "robots.txt",
        "llms.txt",
        "search/index.json",
        "404.html",
    )
    for rel in required:
        if not (dst / rel).exists():
            errors.append(f"产物缺失: {rel}")
    search_index = dst / "search" / "index.json"
    if search_index.exists():
        try:
            json.loads(search_index.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            errors.append(f"search/index.json 不是合法 JSON: {exc}")
    sitemap = dst / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        if "<urlset" not in text or "<loc>" not in text:
            errors.append("sitemap.xml 缺少 urlset/loc")
    if expect_absolute_urls:
        for rel in ("index.html", "robots.txt"):
            target = dst / rel
            if target.exists():
                text = target.read_text(encoding="utf-8", errors="replace")
                if "example.com" in text:
                    errors.append(f"产物含占位域名 example.com: {rel}")
    if content_root and content_root.exists():
        import datetime as _dt
        import yaml as _yaml

        sitemap_text = ""
        sitemap = dst / "sitemap.xml"
        if sitemap.exists():
            sitemap_text = sitemap.read_text(encoding="utf-8", errors="replace")
        for p in sorted((content_root / "posts").glob("*.md")):
            text = p.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            try:
                fm = _yaml.safe_load(text.split("---", 2)[1]) or {}
            except Exception:
                continue
            rel = f"posts/{p.stem}/index.html"
            if fm.get("status") == "draft" and (dst / rel).exists():
                errors.append(f"草稿泄漏到公开产物: {rel}")
            if fm.get("status") == "draft" and f"/posts/{p.stem}/" in sitemap_text:
                errors.append(f"sitemap 包含草稿 URL: /posts/{p.stem}/")
            try:
                date_text = str(fm.get("date", "")).strip()
                if date_text:
                    pub = _dt.date.fromisoformat(date_text[:10])
                    if pub > _dt.date.today() and (dst / rel).exists():
                        errors.append(f"未来日期文章出现在公开产物: {rel} ({date_text})")
            except ValueError:
                pass
    return errors


def write_fingerprint(root):
    """构建前把关键静态资源哈希写入 config/build.yaml（自动缓存指纹）。

    Hugo dataDir 指向 config/，模板可通过 hugo.Data.build 读取；
    后台由 render() 读取同一文件生成资源版本号。文件为构建期生成物，
    不视为品牌/个人/站点文案事实来源。
    """
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    data = {"css": {}, "js": {}, "built_at": ""}
    for key, rel in FINGERPRINT_FILES.items():
        section, name = key.split(".", 1)
        path = root / rel
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
        else:
            digest = "missing"
        data[section][name] = digest
    import datetime

    data["built_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    import yaml

    text = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).strip()
    target = config_dir / "build.yaml"
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(f"# build.yaml（构建期自动生成，勿手改）\n{text}\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def build(args):
    """执行 校验 → 渲染 → 发布 → 清理。"""
    started = time.time()
    errors = validate_content(ROOT)
    errors += validate_content_links(ROOT)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    write_fingerprint(ROOT)

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

    try:
        run_build(
            ROOT,
            tmp,
            hugo_cmd=hugo_cmd,
            memory_limit=memory_limit,
            extra=extra,
            metrics=args.metrics,
        )
        publish(tmp, dst)
        verify_errors = verify_output(
            dst,
            expect_absolute_urls=bool(os.environ.get("SITE_BASEURL", "").strip()),
            content_root=(ROOT / "content" if not args.preview else None),
        )
        if verify_errors:
            for err in verify_errors:
                print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        total = sum(p.stat().st_size for p in dst.rglob("*") if p.is_file())
        count = sum(1 for p in dst.rglob("*") if p.is_file())
        elapsed = round(time.time() - started, 2)
        if args.report:
            report = {
                "ok": True,
                "destination": str(dst),
                "files": count,
                "bytes": total,
                "elapsed_s": elapsed,
                "preview": bool(args.preview),
            }
            pathlib.Path(args.report).write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(
            f"build OK -> {dst} ({count} files, {total / 1024 / 1024:.2f} MB, {elapsed}s)"
        )
    except Exception as exc:  # noqa: BLE001 - 失败统一清理并给出可读退出码
        if args.report:
            pathlib.Path(args.report).write_text(
                json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if tmp.exists():
            shutil.rmtree(tmp)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    finally:
        if not args.keep_tmp and tmp.exists():
            shutil.rmtree(tmp)


def main():
    parser = argparse.ArgumentParser(description="Li&Blog 分段构建编排")
    parser.add_argument("--full", action="store_true", help="全量构建并发布到 output/")
    parser.add_argument("--preview", action="store_true", help="构建草稿到 .preview-out/")
    parser.add_argument("--keep-tmp", action="store_true", help="保留临时目录（调试）")
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="附加 Hugo --templateMetrics / --templateMetricsHints 输出",
    )
    parser.add_argument("--report", metavar="PATH", help="构建结果 JSON 报告输出路径")
    args = parser.parse_args()

    lock_path = pathlib.Path(
        os.environ.get("BUILD_LOCK_PATH", str(ROOT / ".build.lock"))
    )
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        build(args)


if __name__ == "__main__":
    main()
