"""Li&Blog 管理后台主应用：Setup、双登录、八栏目、预览与重建。"""

import datetime
import os
from contextlib import asynccontextmanager
from math import ceil
from typing import Optional
from urllib.parse import unquote, urlencode

import yaml
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from admin import (
    audit,
    backup as backup_store,
    build,
    content as store,
    forms,
    importer,
    media as media_store,
    oidc,
    restore as restore_store,
    revisions,
    security,
)
from admin.ingest import import_beacon_log
from admin.config import ROOT, settings
from admin.db import (
    clear_oidc_sub,
    connect,
    create_admin,
    get_admin,
    init_db,
    record_audit,
    update_admin,
)
from admin.session import COOKIE, create_session, delete_session, get_session
from admin.uploads import read_limited


def _bootstrap_build() -> None:
    """admin 每次启动自动全量构建；失败只告警不阻塞启动（LIBLOG_BOOTSTRAP_BUILD=0 可关闭）。"""
    if os.getenv("LIBLOG_BOOTSTRAP_BUILD", "1") == "0":
        return
    try:
        result, elapsed = build.run_full()
    except Exception as exc:  # noqa: BLE001 - 启动引导失败不应拖垮后台
        print(f"[build] 启动引导构建异常：{exc}")
        return
    if result.returncode == 0:
        print(f"[build] 启动引导构建成功（{elapsed}s）")
    else:
        tail = (result.stderr or result.stdout or "").strip()[-300:]
        hint = ""
        if "PermissionError" in tail or "Permission denied" in tail:
            hint = (
                "；请检查 content/config/output 对 UID 1000 可写"
                "（sudo chown -R 1000:1000 content config output）"
            )
        print(f"[build] 启动引导构建失败：{tail}{hint}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    imported = import_beacon_log()
    if imported:
        print(f"[beacon] imported {imported} hits")
    _bootstrap_build()
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="liblog_oauth_state",
    max_age=3600,
    same_site="lax",
    https_only=settings.cookie_secure,
)


@app.middleware("http")
async def admin_headers(request: Request, call_next):
    if request.url.path.startswith(f"/{settings.admin_path}/") and settings.ip_whitelist:
        if client_ip(request) not in settings.ip_whitelist:
            return Response("403 Forbidden", status_code=403)
    response = await call_next(request)
    if request.url.path.startswith(f"/{settings.admin_path}/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
    return response


@app.get("/healthz")
def healthz():
    """容器健康检查：不经过后台鉴权，仅容器网络内可达。"""
    return {"status": "ok"}


templates = Jinja2Templates(directory=str(ROOT / "admin" / "templates"))
rate = security.RateLimiter()
DUMMY_HASH = security.hash_password("dummy-timing-equalizer")
STATUS_LABELS = {"published": "已发布", "draft": "草稿", "active": "进行中"}
ADMIN_BADGE_VARIANTS = {
    "published": "admin-badge--published",
    "draft": "admin-badge--draft",
    "active": "admin-badge--active",
}
ADMIN_NAV = [
    {
        "label": "内容",
        "items": [
            {"label": "文章", "path": "/posts", "icon": "file"},
            {"label": "标签", "path": "/tags", "icon": "text"},
            {"label": "项目", "path": "/projects", "icon": "folder"},
            {"label": "时间线", "path": "/timeline", "icon": "clock"},
            {"label": "关于我", "path": "/about", "icon": "user"},
            {"label": "资源", "path": "/resources", "icon": "book"},
        ],
    },
    {
        "label": "设置",
        "items": [
            {"label": "品牌", "path": "/config/brand", "icon": "palette"},
            {"label": "文案", "path": "/config/strings", "icon": "text"},
            {"label": "首页", "path": "/config/homepage", "icon": "home"},
            {"label": "资料", "path": "/config/profile", "icon": "card"},
            {"label": "账号", "path": "/settings/account", "icon": "user"},
        ],
    },
    {
        "label": "系统",
        "items": [
            {"label": "媒体库", "path": "/media", "icon": "image"},
            {"label": "统计", "path": "/stats", "icon": "chart"},
            {"label": "操作日志", "path": "/logs", "icon": "text"},
            {"label": "健康检查", "path": "/health", "icon": "chart"},
            {"label": "内容体检", "path": "/audit", "icon": "card"},
            {"label": "备份", "path": "/backup", "icon": "archive"},
        ],
    },
]

settings.preview_root.mkdir(parents=True, exist_ok=True)
app.mount(
    f"/{settings.admin_path}/static",
    StaticFiles(directory=str(ROOT / "themes" / "blog-theme" / "static")),
    name="admin-static",
)


def ap(path: str) -> str:
    return f"/{settings.admin_path}{path}"


def build_admin_nav(request: Request) -> list[dict]:
    """后台侧边栏导航：路径前缀匹配当前项，模板只负责渲染。"""
    current = request.url.path
    groups = []
    for group in ADMIN_NAV:
        items = []
        for item in group["items"]:
            base = ap(item["path"])
            items.append(
                {
                    **item,
                    "active": current == base or current.startswith(base + "/"),
                }
            )
        groups.append({"label": group["label"], "items": items})
    return groups


def display_path(path: str) -> str:
    """beacon 参数经过 Hugo 与浏览器双重编码，展示层再做一次解码。"""
    try:
        return unquote(path)
    except Exception:
        return path


def safe_stats_href(path: str) -> str:
    """统计路径只允许站内相对路径，拒绝 javascript:/data: 等 scheme。"""
    try:
        decoded = unquote(path)
    except Exception:
        return ""
    if not decoded.startswith("/") or ":" in decoded:
        return ""
    if len(decoded) > 512 or any(ord(ch) < 32 or ch.isspace() for ch in decoded):
        return ""
    return path


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _audit(kind: str, detail: str) -> None:
    try:
        conn = connect()
        record_audit(conn, kind, detail)
        conn.close()
    except Exception:
        pass


def current_session(request: Request) -> Optional[dict]:
    session_id = request.cookies.get(COOKIE)
    if not session_id:
        return None
    return get_session(session_id)


def ensure_anon_session(request: Request) -> Optional[dict]:
    sess = current_session(request)
    if sess is None:
        session_id = create_session("anon")
        sess = get_session(session_id)
        request.state.new_session_id = session_id
    request.state.anon_session = sess
    return sess


def attach_session_cookie(response, session_id: str) -> None:
    response.set_cookie(
        COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_ttl,
    )


def csrf_ok(request: Request, form) -> bool:
    sess = current_session(request)
    if sess is None:
        return False
    return security.check_token(sess["csrf"], form.get("_csrf", ""))


def render(request: Request, name: str, context: dict) -> HTMLResponse:
    sess = current_session(request)
    if sess is None:
        sess = getattr(request.state, "anon_session", None)
    context.setdefault("admin_path", settings.admin_path)
    context.setdefault("csrf", sess["csrf"] if sess else "")
    context.setdefault("status_labels", STATUS_LABELS)
    context.setdefault("nav_groups", build_admin_nav(request))
    flash = request.query_params.get("ok") or request.query_params.get("error")
    context.setdefault("flash", flash)
    context.setdefault("flash_type", "error" if request.query_params.get("error") else "ok")
    return templates.TemplateResponse(request, name, context)


def require_login(request: Request) -> None:
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if not has_admin:
        raise HTTPException(status_code=302, headers={"Location": ap("/setup")})
    if current_session(request) is None:
        raise HTTPException(status_code=302, headers={"Location": ap("/login")})


def after_build_redirect(base: str) -> RedirectResponse:
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"{base}?error=构建失败"), status_code=303)
    return RedirectResponse(ap(f"{base}?ok=已保存并重建({elapsed}s)"), status_code=303)


def query_url(base: str, **params) -> str:
    parts = {k: v for k, v in params.items() if v not in (None, "")}
    qs = urlencode(parts)
    return f"{base}?{qs}" if qs else base


# ---------- 登录与登出 ----------

@app.get(ap("/login"), response_class=HTMLResponse)
def login_page(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if not has_admin:
        return RedirectResponse(ap("/setup"), status_code=302)
    ensure_anon_session(request)
    response = render(request, "login.html", {"oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    if getattr(request.state, "new_session_id", None):
        attach_session_cookie(response, request.state.new_session_id)
    return response


@app.post(ap("/login"), response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return render(request, "login.html", {"error": "会话失效，请重试", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    if len(password) > 1024:
        return render(request, "login.html", {"error": "用户名或密码错误", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    if not rate.allow(f"ip:{client_ip(request)}", 30, 60):
        conn = connect()
        record_audit(conn, "login_limited", "global ip limit", client_ip(request))
        conn.close()
        return render(request, "login.html", {"error": "尝试次数过多，请稍后再试", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    key = f"{client_ip(request)}:{username}"
    if not rate.allow(key, 5, 60):
        conn = connect()
        record_audit(conn, "login_limited", f"username={username}", client_ip(request))
        conn.close()
        return render(request, "login.html", {"error": "尝试次数过多，请稍后再试", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    conn = connect()
    admin = get_admin(conn)
    conn.close()
    if admin is None:
        security.verify_password(password, DUMMY_HASH)
        conn = connect()
        record_audit(conn, "login_fail", f"username={username}", client_ip(request))
        conn.close()
        return render(request, "login.html", {"error": "用户名或密码错误", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    if not security.verify_password(password, admin["password_hash"]):
        conn = connect()
        record_audit(conn, "login_fail", f"username={username}", client_ip(request))
        conn.close()
        return render(request, "login.html", {"error": "用户名或密码错误", "oidc_enabled": oidc.enabled(), "brand": store.load_yaml("brand")})
    conn = connect()
    record_audit(conn, "login_ok", f"username={username}", client_ip(request))
    conn.close()
    session_id = create_session("local")
    response = RedirectResponse(ap("/"), status_code=303)
    response.set_cookie(
        COOKIE, session_id, httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.session_ttl,
    )
    return response


@app.get(ap("/logout"))
def logout_page():
    """GET 仅作兼容跳转，不执行登出（登出必须 POST + CSRF）。"""
    return RedirectResponse(ap("/login"), status_code=302)


@app.post(ap("/logout"))
def logout(request: Request, csrf_token: str = Form("", alias="_csrf")):
    sess = current_session(request)
    if sess and not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/?error=会话失效"), status_code=303)
    if sess:
        delete_session(sess["id"])
    response = RedirectResponse(ap("/login"), status_code=302)
    response.delete_cookie(COOKIE)
    return response


@app.get(ap("/login/oidc"))
def oidc_login(request: Request):
    if not oidc.enabled():
        return RedirectResponse(ap("/login?error=OIDC未配置"), status_code=302)
    try:
        return oidc.authorize_start(request, "login")
    except Exception:
        return RedirectResponse(ap("/login?error=OIDC启动失败"), status_code=302)


@app.get(ap("/oidc/callback"))
async def oidc_callback(request: Request):
    try:
        status, sub, session_id, sid = await oidc.handle_callback(request)
    except Exception:
        return RedirectResponse(ap("/login?error=OIDC登录失败"), status_code=302)
    if status == "denied":
        return RedirectResponse(ap("/login?error=该账号不是本后台管理员"), status_code=302)
    if status == "bound":
        return RedirectResponse(ap("/setup/oidc?bound=1"), status_code=302)
    response = RedirectResponse(ap("/"), status_code=302)
    response.set_cookie(
        COOKIE, session_id, httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.session_ttl,
    )
    return response


@app.post(ap("/oidc/backchannel"))
async def oidc_backchannel(request: Request):
    ok = await oidc.backchannel_logout(request)
    return HTMLResponse("OK", status_code=200 if ok else 400)


# ---------- Setup 三步向导 ----------

@app.get(ap("/setup"))
def setup_index(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    return RedirectResponse(ap("/setup/basic"), status_code=302)


@app.get(ap("/setup/basic"), response_class=HTMLResponse)
def setup_basic_page(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    brand = store.load_yaml("brand")
    profile = store.load_yaml("profile")
    ensure_anon_session(request)
    response = render(request, "setup_basic.html", {"brand": brand, "profile": profile})
    if getattr(request.state, "new_session_id", None):
        attach_session_cookie(response, request.state.new_session_id)
    return response


@app.post(ap("/setup/basic"))
def setup_basic_submit(
    request: Request,
    site_name: str = Form("Li&Blog"),
    tagline: str = Form(""),
    promise: str = Form(""),
    persona: str = Form(""),
    name: str = Form(""),
    identity: str = Form(""),
    direction: str = Form(""),
    goal: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/setup/basic?error=会话失效"), status_code=303)
    brand = store.load_yaml("brand")
    brand.update({"name": site_name, "tagline": tagline, "promise": promise, "persona": persona})
    profile = store.load_yaml("profile")
    profile.update({"name": name, "identity": identity, "direction": direction, "goal": goal})
    try:
        store.save_yaml("brand", brand)
        store.save_yaml("profile", profile)
    except OSError as exc:
        return RedirectResponse(
            ap(f"/setup/basic?error=保存失败，config 目录不可写（{exc}）"),
            status_code=303,
        )
    return RedirectResponse(ap("/setup/account"), status_code=303)


@app.post(ap("/setup/restore"))
async def setup_restore(
    request: Request,
    file: UploadFile = File(...),
    confirm: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/setup/basic?error=会话失效"), status_code=303)
    if confirm != "1":
        return RedirectResponse(ap("/setup/basic?error=请先勾选确认覆盖"), status_code=303)
    try:
        data = await read_limited(file, settings.restore_max_bytes)
        restore_store.restore_backup(data, safety=True)
    except ValueError as exc:
        return RedirectResponse(ap(f"/setup/basic?error={exc}"), status_code=303)
    build_result, elapsed = build.run_full()
    if build_result.returncode != 0:
        return RedirectResponse(ap("/setup/basic?error=已恢复但构建失败"), status_code=303)
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(
            ap("/login?ok=备份恢复完成，请使用备份中的管理员账号登录"), status_code=303
        )
    return RedirectResponse(ap("/setup/account"), status_code=303)


@app.get(ap("/setup/account"), response_class=HTMLResponse)
def setup_account_page(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    ensure_anon_session(request)
    response = render(request, "setup_account.html", {"brand": store.load_yaml("brand")})
    if getattr(request.state, "new_session_id", None):
        attach_session_cookie(response, request.state.new_session_id)
    return response


@app.post(ap("/setup/account"))
def setup_account_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    confirm: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/setup/account?error=会话失效"), status_code=303)
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    if len(username) < 3 or len(password) < 8 or len(password) > 1024:
        return RedirectResponse(ap("/setup/account?error=用户名至少3位，密码需8-1024位"), status_code=303)
    if password != confirm:
        return RedirectResponse(ap("/setup/account?error=两次密码不一致"), status_code=303)
    conn = connect()
    create_admin(conn, username, security.hash_password(password))
    conn.close()
    session_id = create_session("local")
    response = RedirectResponse(ap("/setup/oidc"), status_code=303)
    response.set_cookie(
        COOKIE, session_id, httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.session_ttl,
    )
    return response


@app.get(ap("/setup/oidc"), response_class=HTMLResponse)
def setup_oidc_page(request: Request):
    require_login(request)
    conn = connect()
    admin = get_admin(conn)
    conn.close()
    ensure_anon_session(request)
    response = render(
        request,
        "setup_oidc.html",
        {
            "bound": bool(admin and admin["oidc_sub"]),
            "oidc_enabled": oidc.enabled(),
            "callback_uri": settings.lipass_redirect_uri or "(部署后按实际域名填写)",
        },
    )
    if getattr(request.state, "new_session_id", None):
        attach_session_cookie(response, request.state.new_session_id)
    return response


@app.post(ap("/setup/oidc/bind"))
def setup_oidc_bind(request: Request, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/setup/oidc?error=会话失效"), status_code=303)
    try:
        return oidc.authorize_start(request, "setup_bind")
    except Exception:
        return RedirectResponse(ap("/setup/oidc?error=OIDC未配置或启动失败"), status_code=303)


# ---------- 后台首页与统计 ----------

@app.get(ap("/"), response_class=HTMLResponse)
def dashboard(request: Request):
    require_login(request)
    counts = {s: len(store.list_markdown(s)) for s in ("posts", "projects", "timeline")}
    posts = store.list_markdown("posts")
    posts.sort(key=lambda it: not it.get("pinned", False))
    drafts = [p for p in posts if p.get("status") == "draft"]
    recent_posts = posts[:5]
    conn = connect()
    stats = conn.execute("SELECT path, day, views FROM stats ORDER BY views DESC LIMIT 20").fetchall()
    trend_rows = conn.execute(
        "SELECT day, SUM(views) AS total FROM stats "
        "WHERE day >= date('now', '-6 days') GROUP BY day ORDER BY day"
    ).fetchall()
    conn.close()
    trend_map = {r["day"]: r["total"] for r in trend_rows}
    trend = []
    for offset in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).isoformat()
        trend.append({"day": day, "total": trend_map.get(day, 0)})
    trend_max = max((t["total"] for t in trend), default=0)
    for t in trend:
        t["pct"] = round(t["total"] * 100 / trend_max) if trend_max else 0
    last_build = "尚未构建"
    index_file = settings.output_root / "index.html"
    if index_file.exists():
        last_build = datetime.datetime.fromtimestamp(index_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    output_info = build.output_info()
    top_rows = [{"path": display_path(r["path"]), "views": r["views"]} for r in stats[:5]]
    top_max = max((r["views"] for r in top_rows), default=0)
    for r in top_rows:
        r["pct"] = round(r["views"] * 100 / top_max) if top_max else 0
    recent_columns = [
        {"key": "title", "label": "标题", "type": "link"},
        {"key": "date", "label": "日期", "type": "text"},
        {"key": "status", "label": "状态", "type": "badge"},
        {"key": "actions", "label": "操作", "type": "actions"},
    ]
    recent_rows = [
        {
            "title": p["title"],
            "title_href": ap(f"/posts/{p['slug']}/edit"),
            "date": p["date"],
            "status": p["status"],
            "status_label": STATUS_LABELS.get(p["status"], p["status"]),
                "status_class": ADMIN_BADGE_VARIANTS.get(p["status"], "admin-badge--muted"),
            "actions": [{"label": "编辑", "href": ap(f"/posts/{p['slug']}/edit")}],
        }
        for p in recent_posts
    ]
    stats_columns = [
        {"key": "path", "label": "路径", "type": "link"},
        {"key": "day", "label": "日期", "type": "text"},
        {"key": "views", "label": "次数", "type": "number"},
    ]
    stats_rows = [
        {
            "path": display_path(r["path"]),
            "path_href": safe_stats_href(r["path"]),
            "day": r["day"],
            "views": r["views"],
        }
        for r in stats
    ]
    return render(
        request,
        "dashboard.html",
        {
            "counts": counts,
            "drafts": drafts,
            "recent_posts": recent_posts,
            "stats": stats,
            "media_count": len(media_store.list_media()),
            "last_build": last_build,
            "output_info": output_info,
            "trend": trend,
            "top_rows": top_rows,
            "recent_table": {
                "caption": "最近文章",
                "columns": recent_columns,
                "rows": recent_rows,
                "empty": "暂无文章",
                "striped": True,
            },
            "stats_table": {
                "caption": "最近访问统计",
                "columns": stats_columns,
                "rows": stats_rows,
                "empty": "暂无数据（统计上线后展示）",
            },
        },
    )


@app.get(ap("/stats"), response_class=HTMLResponse)
def stats_page(
    request: Request,
    start: str = "",
    end: str = "",
    group: str = "path",
    limit: int = 500,
):
    require_login(request)
    conn = connect()
    params: list = []
    if group == "month":
        sql = (
            "SELECT strftime('%Y-%m', day) AS period, SUM(views) AS total, "
            "COUNT(DISTINCT path) AS paths FROM stats WHERE 1=1"
        )
    elif group == "year":
        sql = (
            "SELECT strftime('%Y', day) AS period, SUM(views) AS total, "
            "COUNT(DISTINCT path) AS paths FROM stats WHERE 1=1"
        )
    else:
        sql = "SELECT path, day, views FROM stats WHERE 1=1"
    if start:
        sql += " AND day >= ?"
        params.append(start)
    if end:
        sql += " AND day <= ?"
        params.append(end)
    if group in ("month", "year"):
        sql += " GROUP BY period ORDER BY period DESC LIMIT ?"
        params.append(min(max(int(limit), 10), 1000))
    else:
        sql += " ORDER BY views DESC LIMIT ?"
        params.append(min(max(int(limit), 10), 1000))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if group in ("month", "year"):
        total_views = sum(r["total"] for r in rows)
        unique_paths = sum(r["paths"] for r in rows)
        columns = [
            {"key": "period", "label": "周期", "type": "text"},
            {"key": "total", "label": "访问", "type": "number"},
            {"key": "paths", "label": "独立路径", "type": "number"},
        ]
    else:
        total_views = sum(r["views"] for r in rows)
        unique_paths = len({r["path"] for r in rows})
        columns = [
            {"key": "path", "label": "路径", "type": "link"},
            {"key": "day", "label": "日期", "type": "text"},
            {"key": "views", "label": "次数", "type": "number"},
        ]
    if group in ("month", "year"):
        table_rows = [
            {"period": r["period"], "total": r["total"], "paths": r["paths"]}
            for r in rows
        ]
    else:
        table_rows = [
            {
                "path": display_path(r["path"]),
                "path_href": safe_stats_href(r["path"]),
                "day": r["day"],
                "views": r["views"],
            }
            for r in rows
        ]
    table = {
        "caption": "访问统计",
        "columns": columns,
        "rows": table_rows,
        "empty": "暂无数据",
        "striped": True,
    }
    return render(
        request,
        "stats.html",
        {
            "table": table,
            "start": start,
            "end": end,
            "group": group,
            "total_views": total_views,
            "unique_paths": unique_paths,
        },
    )


@app.post(ap("/rebuild"))
def rebuild(request: Request, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/?error=会话失效"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"/?error=构建失败:{result.stderr[-200:]}"), status_code=303)
    return RedirectResponse(ap(f"/?ok=构建成功({elapsed}s)"), status_code=303)


# ---------- 媒体库 ----------

@app.get(ap("/media"), response_class=HTMLResponse)
def media_page(request: Request, q: str = ""):
    require_login(request)
    items = media_store.list_media()
    total_size = sum(it["size"] for it in items)
    largest = max((it["size"] for it in items), default=0)
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it["rel"].lower()]
    groups = {}
    for it in items:
        month = "/".join(it["rel"].split("/")[:2]) if "/" in it["rel"] else "未分类"
        groups.setdefault(month, []).append(it)
    media_columns = [
        {"key": "thumb", "label": "图片", "type": "image"},
        {"key": "rel", "label": "路径", "type": "link"},
        {"key": "size", "label": "大小", "type": "text", "align": "right"},
        {"key": "actions", "label": "操作", "type": "actions"},
    ]

    def media_rows(files):
        rows = []
        for m in files:
            static_url = f"/{settings.admin_path}/static/img/{m['rel']}"
            size_text = f"{m['size'] / 1024:.0f} KB" if m["size"] >= 1024 else f"{m['size']} B"
            if m.get("dims"):
                size_text = f"{m['dims'][0]}×{m['dims'][1]} · {size_text}"
            rows.append(
                {
                    "thumb": m["rel"],
                    "thumb_src": static_url,
                    "rel": m["rel"],
                    "rel_href": static_url,
                    "rel_external": True,
                    "size": size_text,
                    "actions": [
                        {"label": "查看", "href": static_url, "external": True},
                        {
                            "label": "复制路径",
                            "button": True,
                            "class": "media-copy",
                            "data_url": m["url"],
                        },
                        {
                            "label": "复制 Markdown",
                            "button": True,
                            "class": "media-copy-md",
                            "data_url": m["url"],
                        },
                        {
                            "label": "删除",
                            "href": ap("/media/delete"),
                            "method": "post",
                            "name": "path",
                            "value": m["rel"],
                            "danger": True,
                            "confirm": f"确定删除 {m['rel']}？删除后会清理引用并重建公开站。",
                        },
                    ],
                }
            )
        return rows

    grouped = [
        {
            "month": m,
            "table": {
                "caption": f"媒体库 {m}",
                "columns": media_columns,
                "rows": media_rows(groups[m]),
                "empty": "暂无图片",
                "striped": True,
            },
        }
        for m in sorted(groups, reverse=True)
    ]
    return render(
        request,
        "media.html",
        {
            "items": items,
            "groups": grouped,
            "q": q,
            "total_size": total_size,
            "largest": largest,
        },
    )


@app.post(ap("/media/upload"))
async def media_upload(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/media?error=会话失效"), status_code=303)
    try:
        data = await read_limited(file, media_store.MAX_SIZE)
        p = media_store.save_upload(file.filename or "", data)
        _audit("media_upload", p.relative_to(media_store.MEDIA_ROOT).as_posix())
    except ValueError as exc:
        return RedirectResponse(ap(f"/media?error={exc}"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/media?error=已上传但构建失败"), status_code=303)
    return RedirectResponse(ap(f"/media?ok=已上传 {p.relative_to(media_store.MEDIA_ROOT).as_posix()} 并重建（{elapsed}s）"), status_code=303)


@app.post(ap("/media/delete"))
def media_delete(request: Request, path: str = Form(""), csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/media?error=会话失效"), status_code=303)
    try:
        media_store.delete_media(path)
        cleaned_md = store.remove_image_references(path)
        cleaned_cfg = store.clear_config_image_refs(path)
    except (ValueError, FileNotFoundError) as exc:
        return RedirectResponse(ap(f"/media?error={exc}"), status_code=303)
    _audit("media_delete", path)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/media?error=已删除但构建失败"), status_code=303)
    cleaned = len(cleaned_md) + len(cleaned_cfg)
    if cleaned:
        msg = f"已删除并清理 {cleaned} 处引用，已重建（{elapsed}s）"
    else:
        msg = f"已删除并重建（{elapsed}s）"
    return RedirectResponse(ap(f"/media?ok={msg}"), status_code=303)


@app.post(ap("/media/upload-json"))
async def media_upload_json(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return JSONResponse({"error": "会话失效"}, status_code=403)
    try:
        data = await read_limited(file, media_store.MAX_SIZE)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    try:
        p = media_store.save_upload(file.filename or "", data)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    rel = p.relative_to(media_store.MEDIA_ROOT).as_posix()
    return JSONResponse({"url": f"/img/{rel}", "rel": rel})


@app.post(ap("/posts/{slug}/status"))
def post_status(
    request: Request,
    slug: str,
    status: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/posts?error=会话失效"), status_code=303)
    if status not in ("published", "draft"):
        return RedirectResponse(ap("/posts?error=状态不合法"), status_code=303)
    try:
        old, body = store.read_markdown("posts", slug)
        old["status"] = status
        store.write_markdown("posts", slug, old, body)
        _audit("post_status", f"{slug}={status}")
    except (ValueError, FileNotFoundError) as exc:
        return RedirectResponse(ap(f"/posts?error={exc}"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/posts?error=状态更新后构建失败"), status_code=303)
    return RedirectResponse(ap(f"/posts?ok=已{('发布' if status == 'published' else '转为草稿')}并重建（{elapsed}s）"), status_code=303)


@app.post(ap("/posts/{slug}/pin"))
def post_pin(
    request: Request,
    slug: str,
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/posts?error=会话失效"), status_code=303)
    try:
        old, body = store.read_markdown("posts", slug)
        old["pinned"] = not old.get("pinned", False)
        store.write_markdown("posts", slug, old, body)
        _audit("post_pin", f"{slug}={'置顶' if old['pinned'] else '取消置顶'}")
    except (ValueError, FileNotFoundError) as exc:
        return RedirectResponse(ap(f"/posts?error={exc}"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/posts?error=置顶状态更新后构建失败"), status_code=303)
    return RedirectResponse(
        ap(f"/posts?ok=已{('取消置顶' if not old['pinned'] else '置顶')}并重建（{elapsed}s）"), status_code=303
    )


@app.get(ap("/stats/export"))
def stats_export(request: Request, start: str = "", end: str = ""):
    require_login(request)
    conn = connect()
    sql = "SELECT path, day, views FROM stats WHERE 1=1"
    params: list = []
    if start:
        sql += " AND day >= ?"
        params.append(start)
    if end:
        sql += " AND day <= ?"
        params.append(end)
    sql += " ORDER BY day DESC, views DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    def csv_cell(value) -> str:
        s = str(value)
        if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
            s = "'" + s
        return '"' + s.replace('"', '""') + '"'

    lines = ["path,day,views"]
    lines += [
        f'{csv_cell(r["path"])},{csv_cell(r["day"])},{r["views"]}' for r in rows
    ]
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="liblog-stats.csv"'},
    )


@app.get(ap("/audit"), response_class=HTMLResponse)
def audit_page(request: Request):
    require_login(request)
    issues = audit.audit_content()
    danger = sum(1 for i in issues if i["severity"] == "danger")
    warning = len(issues) - danger
    columns = [
        {"key": "title", "label": "标题", "type": "link"},
        {"key": "severity", "label": "级别", "type": "badge"},
        {"key": "message", "label": "问题", "type": "text"},
        {"key": "actions", "label": "操作", "type": "actions"},
    ]
    rows = []
    for issue in issues:
        edit_href = (
            ap(f"/{issue['section']}/{issue['slug']}/edit")
            if issue["section"] in SECTIONS and not SECTIONS[issue["section"]]["single"]
            else ""
        )
        rows.append(
            {
                "title": issue["title"],
                "title_href": edit_href,
                "severity": issue["severity"],
                "severity_label": "严重" if issue["severity"] == "danger" else "提醒",
                "severity_class": (
                    "admin-badge--danger"
                    if issue["severity"] == "danger"
                    else "admin-badge--draft"
                ),
                "message": issue["message"],
                "actions": (
                    [{"label": "编辑", "href": edit_href}] if edit_href else []
                ),
            }
        )
    table = {
        "caption": "内容体检结果",
        "columns": columns,
        "rows": rows,
        "empty": "未发现问题，内容健康",
        "striped": True,
    }
    return render(
        request,
        "audit.html",
        {"issues": issues, "danger": danger, "warning": warning, "table": table},
    )


@app.get(ap("/logs"), response_class=HTMLResponse)
def logs_page(request: Request):
    require_login(request)
    conn = connect()
    rows = conn.execute(
        "SELECT at, kind, detail, ip FROM audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    columns = [
        {"key": "at", "label": "时间", "type": "text"},
        {"key": "kind", "label": "事件", "type": "badge"},
        {"key": "detail", "label": "详情", "type": "text"},
        {"key": "ip", "label": "来源", "type": "text"},
    ]
    table = {
        "caption": "操作日志",
        "columns": columns,
        "rows": [
            {
                "at": datetime.datetime.fromtimestamp(r["at"]).strftime("%Y-%m-%d %H:%M:%S"),
                "kind": r["kind"],
                "kind_label": {
                    "login_ok": "登录成功",
                    "login_fail": "登录失败",
                    "login_limited": "登录限速",
                    "password_changed": "修改密码",
                    "session_revoked": "撤销会话",
                }.get(r["kind"], r["kind"]),
                "kind_class": (
                    "admin-badge--published"
                    if r["kind"] == "login_ok"
                    else (
                        "admin-badge--danger"
                        if r["kind"] in ("login_fail", "login_limited")
                        else "admin-badge--muted"
                    )
                ),
                "detail": r["detail"],
                "ip": r["ip"],
            }
            for r in rows
        ],
        "empty": "暂无日志",
        "striped": True,
    }
    return render(request, "logs.html", {"table": table})


@app.get(ap("/health"), response_class=HTMLResponse)
def admin_health_page(request: Request):
    require_login(request)
    import shutil

    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append(
            {
                "name": name,
                "ok": ok,
                "detail": detail,
                "label": "正常" if ok else "异常",
                "class": "admin-badge--published" if ok else "admin-badge--danger",
            }
        )

    for name, path in (
        ("content 目录", settings.content_root),
        ("config 目录", settings.config_root),
        ("output 目录", settings.output_root),
        ("data 目录", settings.db_path.parent),
        ("preview 目录", settings.preview_root),
        ("媒体目录", media_store.MEDIA_ROOT),
    ):
        path.mkdir(parents=True, exist_ok=True)
        check(f"{name}可写", os.access(path, os.W_OK))
    hugo_bin = os.environ.get("HUGO_BIN", shutil.which("hugo") or "")
    check("Hugo 二进制可用", bool(hugo_bin), hugo_bin or "未找到（容器内应内置）")
    check("GOMEMLIMIT 已设置", bool(os.environ.get("GOMEMLIMIT")), os.environ.get("GOMEMLIMIT", ""))
    check("beacon 日志可读", os.path.exists(settings.beacon_log), str(settings.beacon_log))
    try:
        conn = connect()
        conn.execute("SELECT 1 FROM audit_log LIMIT 1").fetchone()
        conn.close()
        check("SQLite 可读写", True)
    except Exception as exc:  # noqa: BLE001
        check("SQLite 可读写", False, str(exc))
    columns = [
        {"key": "name", "label": "检查项", "type": "text"},
        {"key": "label", "label": "状态", "type": "badge"},
        {"key": "detail", "label": "详情", "type": "text"},
    ]
    table = {
        "caption": "健康检查",
        "columns": columns,
        "rows": [
            {"name": c["name"], "label": c["label"], "label_class": c["class"], "detail": c["detail"]}
            for c in checks
        ],
        "empty": "无检查项",
        "striped": True,
    }
    ok_count = sum(1 for c in checks if c["ok"])
    return render(
        request,
        "health.html",
        {"checks": checks, "ok_count": ok_count, "total": len(checks), "table": table},
    )


def _tag_counts() -> list[dict]:
    counts: dict[str, int] = {}
    for item in store.list_markdown("posts"):
        for tag in item.get("tags") or []:
            counts[str(tag)] = counts.get(str(tag), 0) + 1
    return [{"name": name, "count": count} for name, count in sorted(counts.items())]


@app.get(ap("/tags"), response_class=HTMLResponse)
def tags_page(request: Request):
    require_login(request)
    tags = _tag_counts()
    columns = [
        {"key": "name", "label": "标签", "type": "text"},
        {"key": "count", "label": "文章数", "type": "number"},
    ]
    table = {
        "caption": "标签列表",
        "columns": columns,
        "rows": [{"name": t["name"], "count": t["count"]} for t in tags],
        "empty": "还没有标签",
        "striped": True,
    }
    return render(request, "tags.html", {"tags": tags, "table": table})


@app.post(ap("/tags/apply"))
def tags_apply(
    request: Request,
    old_tag: str = Form(""),
    new_tag: str = Form(""),
    action: str = Form("rename"),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/tags?error=会话失效"), status_code=303)
    old_tag = old_tag.strip()
    new_tag = new_tag.strip()
    if not old_tag or action not in ("rename", "merge", "delete"):
        return RedirectResponse(ap("/tags?error=参数不合法"), status_code=303)
    if action in ("rename", "merge") and not new_tag:
        return RedirectResponse(ap("/tags?error=新标签不能为空"), status_code=303)
    changed = 0
    for item in store.list_markdown("posts"):
        if old_tag not in (item.get("tags") or []):
            continue
        fm, body = store.read_markdown("posts", item["slug"])
        tags = [str(t) for t in (fm.get("tags") or []) if str(t) != old_tag]
        if action in ("rename", "merge") and new_tag not in tags:
            tags.append(new_tag)
        fm["tags"] = tags
        store.write_markdown("posts", item["slug"], fm, body)
        changed += 1
    if not changed:
        return RedirectResponse(ap("/tags?error=没有文章使用该标签"), status_code=303)
    _audit("tags_apply", f"{action}:{old_tag}->{new_tag or '删除'}")
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/tags?error=标签更新后构建失败"), status_code=303)
    return RedirectResponse(
        ap(f"/tags?ok=已更新 {changed} 篇文章并重建（{elapsed}s）"), status_code=303
    )


# ---------- 文章批量导入 ----------

@app.get(ap("/posts/import"), response_class=HTMLResponse)
def posts_import_page(request: Request):
    require_login(request)
    return render(request, "import_posts.html", {"label": "批量导入文章"})


@app.post(ap("/posts/import"))
async def posts_import_submit(
    request: Request,
    files: list[UploadFile] = File(...),
    overwrite: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/posts/import?error=会话失效"), status_code=303)
    if len(files) > settings.import_max_files:
        return RedirectResponse(ap(f"/posts/import?error=一次最多导入 {settings.import_max_files} 个文件"), status_code=303)
    entries = []
    unsupported = []
    total_read = 0
    try:
        for f in files:
            name = (f.filename or "").strip()
            if not name:
                raise ValueError("存在缺少文件名的上传项")
            if name.lower().endswith(".zip"):
                data = await read_limited(f, settings.import_max_zip_bytes)
                total_read += len(data)
                if total_read > settings.import_max_zip_bytes:
                    raise ValueError("导入总大小超过限制")
                entries.extend(importer.extract_zip(data))
            elif name.lower().endswith((".md", ".markdown")):
                data = await read_limited(f, settings.import_max_file_bytes)
                total_read += len(data)
                if total_read > settings.import_max_zip_bytes:
                    raise ValueError("导入总大小超过限制")
                entries.append((name, data))
            else:
                unsupported.append(name)
        import_result = importer.import_posts(entries, overwrite=overwrite == "1")
    except ValueError as exc:
        return RedirectResponse(ap(f"/posts/import?error={exc}"), status_code=303)
    if unsupported:
        import_result["errors"] = [
            f"{name}: 不支持的文件类型" for name in unsupported
        ] + import_result["errors"]
    if import_result["imported"] == 0:
        return render(
            request,
            "import_posts.html",
            {"label": "批量导入文章", "result": import_result},
        )
    build_result, elapsed = build.run_full()
    if build_result.returncode != 0:
        return RedirectResponse(ap("/posts/import?error=导入完成但构建失败"), status_code=303)
    return render(
        request,
        "import_posts.html",
        {"label": "批量导入文章", "result": import_result, "build_elapsed": elapsed},
    )


# ---------- 站点备份 ----------

@app.get(ap("/backup"), response_class=HTMLResponse)
def backup_page(request: Request):
    require_login(request)
    return render(request, "backup.html", {})


@app.get(ap("/backup/download"))
def backup_download(request: Request):
    require_login(request)
    data = backup_store.build_backup_zip()
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="liblog-backup-{ts}.zip"'},
    )


@app.post(ap("/backup/restore"))
async def backup_restore(
    request: Request,
    file: UploadFile = File(...),
    confirm: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/backup?error=会话失效"), status_code=303)
    if confirm != "1":
        return RedirectResponse(ap("/backup?error=请先勾选确认覆盖"), status_code=303)
    try:
        data = await read_limited(file, settings.restore_max_bytes)
        restore_store.restore_backup(data, safety=True)
    except ValueError as exc:
        return RedirectResponse(ap(f"/backup?error={exc}"), status_code=303)
    build_result, elapsed = build.run_full()
    if build_result.returncode != 0:
        return RedirectResponse(ap("/backup?error=已恢复但构建失败，请检查备份内容"), status_code=303)
    return RedirectResponse(
        ap("/login?ok=已从备份恢复并重建，请重新登录"), status_code=303
    )


# ---------- 栏目：列表 / 编辑 / 保存 / 删除 ----------

SECTIONS = {
    "posts": {"label": "文章", "single": False},
    "projects": {"label": "项目", "single": False},
    "timeline": {"label": "时间线", "single": False},
    "about": {"label": "关于我", "single": True},
    "resources": {"label": "资源", "single": True},
}


def _edit_fields(section: str, fm: dict) -> list:
    if section == "posts":
        return [
            ("title", "标题", "text", fm.get("title", "")),
            ("date", "日期", "text", fm.get("date", datetime.date.today().isoformat())),
            ("status", "状态", "select", fm.get("status", "published"), ["published", "draft"]),
            ("tags", "标签（逗号分隔）", "text", ", ".join(fm.get("tags") or [])),
            ("summary", "摘要", "textarea", fm.get("summary", "")),
            ("cover", "封面图路径（/img/…，选填）", "text", fm.get("cover", "")),
            ("pinned", "置顶文章", "checkbox", bool(fm.get("pinned", False))),
        ]
    if section == "projects":
        return [
            ("title", "名称", "text", fm.get("title", "")),
            ("date", "发布时间（可选，留空不显示）", "text", fm.get("date", "")),
            ("repo", "仓库链接", "text", fm.get("repo", "")),
            ("tech", "技术栈（逗号分隔）", "text", ", ".join(fm.get("tech") or [])),
            ("status", "状态", "text", fm.get("status", "active")),
            ("summary", "简介", "textarea", fm.get("summary", "")),
            ("badge_label", "徽章标签", "text", (fm.get("badge") or {}).get("label", "")),
            ("badge_color", "徽章颜色", "text", (fm.get("badge") or {}).get("color", "")),
            ("badge_href", "徽章链接", "text", (fm.get("badge") or {}).get("href", "")),
        ]
    if section == "timeline":
        return [
            ("title", "标题", "text", fm.get("title", "")),
            ("date", "日期", "text", fm.get("date", datetime.date.today().isoformat())),
            ("kind", "类型", "text", fm.get("kind", "里程碑")),
            ("summary", "摘要", "textarea", fm.get("summary", "")),
        ]
    return [("title", "标题", "text", fm.get("title", ""))]


@app.get(ap("/{section}"), response_class=HTMLResponse)
def section_list(
    request: Request,
    section: str,
    q: str = "",
    status: str = "",
    page: int = 1,
    sort: str = "date",
    order: str = "desc",
    per_page: int = 50,
):
    require_login(request)
    if section not in SECTIONS:
        raise HTTPException(404)
    if SECTIONS[section]["single"]:
        return RedirectResponse(ap(f"/{section}/edit"), status_code=302)
    if sort not in ("title", "date", "status", "slug"):
        sort = "date"
    if order not in ("asc", "desc"):
        order = "desc"
    per_page = min(max(int(per_page), 10), 100) if per_page else 50
    items = store.list_markdown(section, q=q, status=status, sort=sort, order=order)
    if section == "posts":
        items.sort(key=lambda it: not it.get("pinned", False))
    total = len(items)
    page = max(1, page)
    pages = max(1, ceil(total / per_page))
    if page > pages:
        page = pages
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    base = ap(f"/{section}")

    def qurl(**over):
        params = {"q": q, "status": status, "sort": sort, "order": order, "per_page": per_page}
        params.update(over)
        return query_url(base, **params)

    columns = []
    if section == "posts":
        columns.append({"key": "select", "label": "选择", "type": "select"})
    columns += [
        {"key": "title", "label": "标题", "type": "link", "sortable": True},
        {"key": "date", "label": "日期", "type": "text", "sortable": True},
        {"key": "status", "label": "状态", "type": "badge", "sortable": section != "timeline"},
        {"key": "actions", "label": "操作", "type": "actions"},
    ]
    rows = []
    group_year = None
    for item in page_items:
        if section == "posts":
            year = str(item.get("date") or "")[:4]
            if year != group_year:
                group_year = year
                rows.append({"__group": year or "未标注"})
        actions = [
            {"label": "编辑", "href": ap(f"/{section}/{item['slug']}/edit")},
            {"label": "查看", "href": f"/{section}/{item['slug']}/", "external": True},
        ]
        if section == "posts":
            actions.append(
                {
                    "label": "转草稿" if item["status"] == "published" else "发布",
                    "href": ap(f"/posts/{item['slug']}/status"),
                    "method": "post",
                    "name": "status",
                    "value": "draft" if item["status"] == "published" else "published",
                }
            )
            actions.append(
                {
                    "label": "取消置顶" if item.get("pinned") else "置顶",
                    "href": ap(f"/posts/{item['slug']}/pin"),
                    "method": "post",
                }
            )
        if section != "timeline":
            actions.append(
                {
                    "label": "删除",
                    "href": ap(f"/{section}/{item['slug']}/delete"),
                    "method": "post",
                    "danger": True,
                    "confirm": "确定删除？删除后会立即重建公开站。",
                }
            )
        rows.append(
            {
                "slug": item["slug"],
                "select": item["slug"],
                "title": item["title"],
                "title_href": ap(f"/{section}/{item['slug']}/edit"),
                "title_tags": (
                    ([{"label": "置顶", "class": "admin-tag--pinned"}] if item.get("pinned") else [])
                    + (item.get("tags") or [])[:2]
                ),
                "date": item["date"],
                "status": item["status"],
                "status_label": STATUS_LABELS.get(item["status"], item["status"]),
                "status_class": ADMIN_BADGE_VARIANTS.get(item["status"], "admin-badge--muted"),
                "actions": actions,
            }
        )
    sort_links = {}
    for key in ("title", "date", "status"):
        if key == "status" and section == "timeline":
            continue
        next_order = "asc" if (sort == key and order == "desc") else "desc"
        sort_links[key] = qurl(sort=key, order=next_order, page="")
    empty = "没有匹配的内容，换个关键词或清除筛选试试。" if (q or status) else "还没有内容，点右上角“新建”开始。"
    table = {
        "caption": f"{SECTIONS[section]['label']}列表",
        "columns": columns,
        "rows": rows,
        "empty": empty,
        "striped": True,
        "sort": sort,
        "order": order,
        "sort_links": sort_links,
        "pagination": {
            "page": page,
            "pages": pages,
            "total": total,
            "prev_url": qurl(page=page - 1) if page > 1 else "",
            "next_url": qurl(page=page + 1) if page < pages else "",
        },
    }
    return render(
        request,
        "list.html",
        {
            "section": section,
            "label": SECTIONS[section]["label"],
            "q": q,
            "status": status,
            "page": page,
            "pages": pages,
            "total": total,
            "per_page": per_page,
            "sort": sort,
            "order": order,
            "table": table,
        },
    )


@app.post(ap("/posts/bulk"))
def posts_bulk(
    request: Request,
    action: str = Form(""),
    slugs: list[str] = Form(default=[]),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/posts?error=会话失效"), status_code=303)
    if action not in ("publish", "draft", "pin", "unpin", "delete"):
        return RedirectResponse(ap("/posts?error=批量操作不合法"), status_code=303)
    changed = 0
    for slug in slugs[:200]:
        if not store.SLUG_RE.match(slug):
            continue
        try:
            if action == "delete":
                store.delete_markdown("posts", slug)
            else:
                old, body = store.read_markdown("posts", slug)
                if action == "publish":
                    old["status"] = "published"
                elif action == "draft":
                    old["status"] = "draft"
                elif action == "pin":
                    old["pinned"] = True
                elif action == "unpin":
                    old["pinned"] = False
                store.write_markdown("posts", slug, old, body)
            changed += 1
        except (ValueError, FileNotFoundError):
            continue
    if not changed:
        return RedirectResponse(ap("/posts?error=没有可执行的文章"), status_code=303)
    _audit("posts_bulk", f"{action}:{changed}")
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap("/posts?error=批量操作后构建失败"), status_code=303)
    return RedirectResponse(
        ap(f"/posts?ok=已批量处理 {changed} 篇并重建（{elapsed}s）"), status_code=303
    )


@app.get(ap("/posts/export"))
def posts_export(
    request: Request,
    q: str = "",
    status: str = "",
    sort: str = "date",
    order: str = "desc",
):
    require_login(request)
    items = store.list_markdown("posts", q=q, status=status, sort=sort, order=order)
    items.sort(key=lambda it: not it.get("pinned", False))

    def cell(value) -> str:
        s = str(value)
        if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
            s = "'" + s
        return '"' + s.replace('"', '""') + '"'

    lines = ["slug,title,date,status,pinned,tags"]
    for it in items:
        lines.append(
            ",".join(
                [
                    cell(it["slug"]),
                    cell(it["title"]),
                    cell(it.get("date", "")),
                    cell(it.get("status", "")),
                    cell("1" if it.get("pinned") else "0"),
                    cell(", ".join(it.get("tags") or [])),
                ]
            )
        )
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="liblog-posts.csv"'},
    )


@app.get(ap("/{section}/new"), response_class=HTMLResponse)
def section_new(request: Request, section: str):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"]:
        raise HTTPException(404)
    return render(
        request,
        "edit.html",
        {
            "section": section,
            "slug": "",
            "label": SECTIONS[section]["label"],
            "fields": _edit_fields(section, {}),
            "all_tags": store.all_tags(),
            "media_items": media_store.list_media()[:20],
            "preview_path": "",
        },
    )


@app.get(ap("/{section}/edit"), response_class=HTMLResponse)
def section_edit(request: Request, section: str):
    require_login(request)
    if section not in SECTIONS:
        raise HTTPException(404)
    slug = section if SECTIONS[section]["single"] else ""
    if slug:
        fm, body = store.read_page(section)
    else:
        fm, body = {}, ""
    return render(
        request,
        "edit.html",
        {
            "section": section,
            "slug": slug,
            "label": SECTIONS[section]["label"],
            "fields": _edit_fields(section, fm),
            "all_tags": store.all_tags(),
            "body": body,
            "media_items": media_store.list_media()[:20],
            "preview_path": f"/preview/{section}" if SECTIONS[section]["single"] else "",
        },
    )


@app.get(ap("/{section}/{slug}/edit"), response_class=HTMLResponse)
def section_slug_edit(request: Request, section: str, slug: str):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"]:
        raise HTTPException(404)
    try:
        fm, body = store.read_markdown(section, slug)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404)
    return render(
        request,
        "edit.html",
        {
            "section": section,
            "slug": slug,
            "label": SECTIONS[section]["label"],
            "fields": _edit_fields(section, fm),
            "all_tags": store.all_tags(),
            "revisions": revisions.list_revisions("posts", slug),
            "body": body,
            "media_items": media_store.list_media()[:20],
            "preview_path": f"/preview/{section}/{slug}",
        },
    )


@app.post(ap("/{section}/save"))
def section_save(
    request: Request,
    section: str,
    slug: str = Form(""),
    new_slug: str = Form(""),
    action: str = Form("save"),
    csrf_token: str = Form("", alias="_csrf"),
    title: str = Form(""),
    date: str = Form(""),
    status: str = Form("published"),
    tags: str = Form(""),
    summary: str = Form(""),
    cover: str = Form(""),
    repo: str = Form(""),
    tech: str = Form(""),
    kind: str = Form(""),
    badge_label: str = Form(""),
    badge_color: str = Form(""),
    badge_href: str = Form(""),
    pinned: str = Form(""),
    body: str = Form(""),
):
    require_login(request)
    if section not in SECTIONS or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/{section}?error=会话失效"), status_code=303)
    old_slug = ""
    if new_slug and not SECTIONS[section]["single"]:
        if new_slug != slug and store.markdown_exists(section, new_slug):
            return RedirectResponse(ap(f"/{section}?error=目标标识已存在"), status_code=303)
        old_slug = slug
        slug = new_slug
    try:
        if SECTIONS[section]["single"]:
            old, _ = store.read_page(section)
            store.write_page(section, {**old, "title": title}, body)
        else:
            old = {}
            if slug:
                try:
                    old, _ = store.read_markdown(section, slug)
                except FileNotFoundError:
                    old = {}
            fm = dict(old)
            if section == "posts":
                fm.update(
                    {
                        "title": title,
                        "date": date,
                        "status": status,
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "summary": summary,
                        "cover": cover,
                        "pinned": pinned == "1",
                    }
                )
            elif section == "projects":
                fm.update(
                    {
                        "title": title,
                        "date": date,
                        "repo": repo,
                        "status": status,
                        "tech": [t.strip() for t in tech.split(",") if t.strip()],
                        "summary": summary,
                        "badge": {
                            "label": badge_label,
                            "color": badge_color,
                            "href": badge_href,
                        },
                        "show_on_home": fm.get("show_on_home", True),
                    }
                )
            else:
                fm.update({"title": title, "date": date, "kind": kind, "summary": summary})
            store.write_markdown(section, slug, fm, body)
            revisions.save_revision(section, slug, fm, body)
            _audit("content_save", f"{section}/{slug}")
            if old_slug and old_slug != slug:
                try:
                    store.delete_markdown(section, old_slug)
                except ValueError:
                    pass
    except ValueError as exc:
        return RedirectResponse(ap(f"/{section}?error={exc}"), status_code=303)
    if action == "preview_raw":
        result, elapsed = build.run_preview()
        if result.returncode != 0:
            edit_path = f"/{section}/edit" if SECTIONS[section]["single"] else f"/{section}/{slug}/edit"
            return RedirectResponse(ap(f"{edit_path}?error=预览构建失败"), status_code=303)
        preview_path = f"/{section}" if SECTIONS[section]["single"] else f"/{section}/{slug}"
        return RedirectResponse(ap(f"/preview{preview_path}?raw=1"), status_code=303)
    if action == "preview":
        result, elapsed = build.run_preview()
        if result.returncode != 0:
            edit_path = f"/{section}/edit" if SECTIONS[section]["single"] else f"/{section}/{slug}/edit"
            return RedirectResponse(ap(f"{edit_path}?error=预览构建失败"), status_code=303)
        preview_path = f"/{section}" if SECTIONS[section]["single"] else f"/{section}/{slug}"
        return RedirectResponse(ap(f"/preview{preview_path}"), status_code=303)
    if action == "save_stay":
        result, elapsed = build.run_full()
        if result.returncode != 0:
            edit_path = f"/{section}/edit" if SECTIONS[section]["single"] else f"/{section}/{slug}/edit"
            return RedirectResponse(ap(f"{edit_path}?error=构建失败"), status_code=303)
        edit_path = f"/{section}/edit" if SECTIONS[section]["single"] else f"/{section}/{slug}/edit"
        return RedirectResponse(ap(f"{edit_path}?ok=已保存并重建（{elapsed}s）"), status_code=303)
    return after_build_redirect(f"/{section}")


@app.get(ap("/posts/{slug}/revisions/{ts}"), response_class=HTMLResponse)
def revision_view(request: Request, slug: str, ts: str):
    require_login(request)
    try:
        fm, body = revisions.read_revision("posts", slug, ts)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404)
    return render(
        request,
        "revision.html",
        {"slug": slug, "ts": ts, "title": fm.get("title", slug), "body": body},
    )


@app.post(ap("/posts/{slug}/revisions/{ts}/restore"))
def revision_restore(
    request: Request,
    slug: str,
    ts: str,
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/posts/{slug}/edit?error=会话失效"), status_code=303)
    try:
        fm, body = revisions.read_revision("posts", slug, ts)
        store.write_markdown("posts", slug, fm, body)
        revisions.save_revision("posts", slug, fm, body)
    except (ValueError, FileNotFoundError) as exc:
        return RedirectResponse(ap(f"/posts/{slug}/edit?error={exc}"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"/posts/{slug}/edit?error=恢复后构建失败"), status_code=303)
    return RedirectResponse(
        ap(f"/posts/{slug}/edit?ok=已恢复 {ts} 版本并重建（{elapsed}s）"), status_code=303
    )


@app.post(ap("/{section}/{slug}/delete"))
def section_delete(request: Request, section: str, slug: str, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"] or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/{section}?error=会话失效"), status_code=303)
    try:
        store.delete_markdown(section, slug)
        _audit("content_delete", f"{section}/{slug}")
    except ValueError:
        return RedirectResponse(ap(f"/{section}?error=非法标识"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"/{section}?error=删除后构建失败"), status_code=303)
    return RedirectResponse(ap(f"/{section}?ok=已删除并重建({elapsed}s)"), status_code=303)


def rewrite_preview_html(html: str, admin_path: str) -> str:
    """把预览 HTML 里的静态资源指向后台受保护路径（含图片与内联 CSS url）。"""
    prefix = f"/{admin_path}/preview-out"
    html = html.replace('href="/css/', f'href="/{admin_path}/static/css/')
    html = html.replace('src="/js/', f'src="/{admin_path}/static/js/')
    html = html.replace('href="/img/', f'href="{prefix}/img/')
    html = html.replace('src="/img/', f'src="{prefix}/img/')
    html = html.replace("url('/img/", f"url('{prefix}/img/")
    html = html.replace('url("/img/', f'url("{prefix}/img/')
    return html


@app.get(ap("/preview-out/{path:path}"))
def preview_out_file(request: Request, path: str):
    """受登录保护的预览产物静态文件（替代未鉴权的 StaticFiles 挂载）。"""
    require_login(request)
    root = settings.preview_root.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404)
    return FileResponse(target)


@app.get(ap("/preview/{section}"), response_class=HTMLResponse)
def preview_single(request: Request, section: str, raw: int = 0):
    return preview_page(request, section, "", raw)


@app.get(ap("/preview/{section}/{slug}"), response_class=HTMLResponse)
def preview_page(request: Request, section: str, slug: str, raw: int = 0):
    require_login(request)
    target = settings.preview_root / section / slug / "index.html"
    exists = target.exists()
    if raw and exists:
        html = target.read_text(encoding="utf-8")
        html = rewrite_preview_html(html, settings.admin_path)
        return HTMLResponse(html)
    return render(
        request,
        "preview.html",
        {"section": section, "slug": slug, "exists": exists,
         "src": (f"/{settings.admin_path}/preview-out/{section}/{slug}/index.html" if slug
                 else f"/{settings.admin_path}/preview-out/{section}/index.html")},
    )


# ---------- 配置表单 ----------

CONFIG_PAGES = {
    "brand": (
        "品牌",
        [
            {"name": "name", "label": "站点名称", "type": "text"},
            {"name": "tagline", "label": "一句话定位", "type": "text"},
            {"name": "promise", "label": "品牌承诺", "type": "text"},
            {"name": "persona", "label": "人格比喻", "type": "text"},
            {"name": "copyright", "label": "版权文案（{year} 会被替换为当前年份）", "type": "text"},
            {"name": "icp", "label": "ICP 备案号（未备案留空）", "type": "text"},
            {"name": "icp_url", "label": "ICP 备案链接", "type": "text"},
            {"name": "police", "label": "公网安备号（未备案留空）", "type": "text"},
            {"name": "police_url", "label": "公安备案链接", "type": "text"},
            {"name": "icp_icon", "label": "ICP 图标（SVG 或图片路径，如 /img/xxx.png；留空只留空位）", "type": "textarea"},
            {"name": "police_icon", "label": "公安图标（SVG 或图片路径，如 /img/xxx.png；留空只留空位）", "type": "textarea"},
            {"name": "logo", "label": "Logo 图片路径", "type": "text", "help": "先把图片传到媒体库，再填 /img/… 路径"},
            {"name": "favicon", "label": "Favicon 路径", "type": "text", "help": "先传到媒体库，再填 /img/… 路径"},
        ],
    ),
    "strings": (
        "页面文案",
        [
            {"name": "nav", "label": "导航", "type": "yaml", "help": "每行一个 key: 值"},
            {"name": "home", "label": "首页区块标题", "type": "yaml", "help": "每行一个 key: 值"},
            {"name": "common", "label": "通用标签", "type": "yaml", "help": "每行一个 key: 值"},
            {"name": "footer", "label": "页脚文案", "type": "yaml", "help": "每行一个 key: 值"},
        ],
    ),
    "homepage": (
        "首页设置",
        [
            {"name": "hero.show_skills", "label": "Hero 显示技能徽章", "type": "checkbox"},
            {"name": "hero.skills_limit", "label": "技能徽章数量", "type": "number"},
            {"name": "journey.preview_count", "label": "历程速览条数", "type": "number"},
            {"name": "posts.featured", "label": "精选文章（slug 逗号分隔，留空自动取最新）", "type": "csv"},
            {"name": "posts.latest_count", "label": "最新文章条数", "type": "number"},
            {"name": "projects.show_on_home", "label": "首页显示项目集", "type": "checkbox"},
            {"name": "projects.max_cards", "label": "首页项目卡数量", "type": "number"},
        ],
    ),
    "profile": (
        "关于我资料",
        [
            {"name": "name", "label": "姓名", "type": "text"},
            {"name": "identity", "label": "身份", "type": "text"},
            {"name": "direction", "label": "方向", "type": "text"},
            {"name": "goal", "label": "当前目标", "type": "text"},
            {
                "name": "skills",
                "label": "技能徽章",
                "type": "list",
                "help": "每一行是一个徽章；颜色选色或填十六进制",
                "columns": [
                    {"key": "name", "label": "名称", "input": "text"},
                    {"key": "color", "label": "颜色", "input": "color"},
                    {"key": "icon", "label": "图标 slug", "input": "text"},
                    {"key": "href", "label": "链接", "input": "text"},
                ],
            },
            {
                "name": "links",
                "label": "外部链接",
                "type": "list",
                "columns": [
                    {"key": "label", "label": "名称", "input": "text"},
                    {"key": "href", "label": "链接", "input": "text"},
                ],
            },
        ],
    ),
}


@app.get(ap("/config/{name}"), response_class=HTMLResponse)
def config_edit(request: Request, name: str):
    require_login(request)
    if name not in CONFIG_PAGES:
        raise HTTPException(404)
    label, specs = CONFIG_PAGES[name]
    data = store.load_yaml(name)
    fields = []
    for spec in specs:
        key = spec["name"]
        value = forms.nested_get(data, key.split("."))
        ftype = spec.get("type", "text")
        field = dict(spec)
        if ftype == "yaml":
            value = value if isinstance(value, (dict, list)) else {}
            value = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
            field["value"] = value
        elif ftype == "checkbox":
            field["value"] = bool(value)
        elif ftype == "list":
            field["value"] = value if isinstance(value, list) else []
        elif ftype == "csv":
            field["value"] = ", ".join(value if isinstance(value, list) else [])
        elif ftype == "number":
            field["value"] = value if value is not None else ""
        else:
            field["value"] = value if value is not None else ""
        fields.append(field)
    return render(request, "config_form.html", {"name": name, "label": label, "fields": fields})


@app.post(ap("/config/{name}"))
async def config_save(request: Request, name: str, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if name not in CONFIG_PAGES or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/config/{name}?error=会话失效"), status_code=303)
    form = await request.form()
    data = store.load_yaml(name)
    label, specs = CONFIG_PAGES[name]
    data, err = forms.parse_config(data, specs, form)
    if err:
        return RedirectResponse(ap(f"/config/{name}?error={err}"), status_code=303)
    if name == "brand":
        data["icp_icon"] = store.sanitize_inline_svg(data.get("icp_icon", ""))
        data["police_icon"] = store.sanitize_inline_svg(data.get("police_icon", ""))
    try:
        store.save_yaml(name, data)
    except OSError as exc:
        return RedirectResponse(
            ap(f"/config/{name}?error=保存失败，config 目录不可写（{exc}）"),
            status_code=303,
        )
    return after_build_redirect(f"/config/{name}")


@app.get(ap("/settings/account"), response_class=HTMLResponse)
def account_page(request: Request):
    require_login(request)
    conn = connect()
    admin = get_admin(conn)
    current_id = (current_session(request) or {}).get("id")
    session_rows = conn.execute(
        "SELECT id, kind, created_at, expires_at FROM sessions ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    sessions_ctx = [
        {
            "id": r["id"],
            "kind": "本地" if r["kind"] == "local" else ("OIDC" if r["kind"] == "oidc" else "匿名"),
            "created": datetime.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M"),
            "expires": datetime.datetime.fromtimestamp(r["expires_at"]).strftime("%Y-%m-%d %H:%M"),
            "current": r["id"] == current_id,
        }
        for r in session_rows
    ]
    return render(
        request,
        "account.html",
        {
            "username": admin["username"] if admin else "",
            "bound": bool(admin and admin["oidc_sub"]),
            "oidc_enabled": oidc.enabled(),
            "callback_uri": settings.lipass_redirect_uri or "(部署后按实际域名填写)",
            "sessions": sessions_ctx,
        },
    )


@app.post(ap("/settings/account"))
def account_save(
    request: Request,
    current_password: str = Form(""),
    new_username: str = Form(""),
    new_password: str = Form(""),
    confirm: str = Form(""),
    csrf_token: str = Form("", alias="_csrf"),
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/settings/account?error=会话失效"), status_code=303)
    conn = connect()
    admin = get_admin(conn)
    if admin is None or not security.verify_password(current_password, admin["password_hash"]):
        conn.close()
        return RedirectResponse(ap("/settings/account?error=当前密码不正确"), status_code=303)
    username = new_username.strip()
    if len(username) < 3:
        conn.close()
        return RedirectResponse(ap("/settings/account?error=用户名至少 3 位"), status_code=303)
    password_hash = None
    if new_password:
        if len(new_password) < 8 or len(new_password) > 1024:
            conn.close()
            return RedirectResponse(ap("/settings/account?error=新密码需 8-1024 位"), status_code=303)
        if new_password != confirm:
            conn.close()
            return RedirectResponse(ap("/settings/account?error=两次新密码不一致"), status_code=303)
        password_hash = security.hash_password(new_password)
    update_admin(conn, username=username, password_hash=password_hash)
    current_id = (current_session(request) or {}).get("id")
    if password_hash:
        conn.execute("DELETE FROM sessions WHERE id != ?", (current_id,))
    conn.commit()
    conn.close()
    if password_hash:
        _audit("password_changed", "管理员密码已修改")
    return RedirectResponse(ap("/settings/account?ok=账号设置已更新"), status_code=303)


@app.post(ap("/settings/account/oidc/bind"))
def account_oidc_bind(request: Request, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/settings/account?error=会话失效"), status_code=303)
    try:
        return oidc.authorize_start(request, "settings_bind")
    except Exception:
        return RedirectResponse(ap("/settings/account?error=OIDC未配置或启动失败"), status_code=303)


@app.post(ap("/settings/account/oidc/unbind"))
def account_oidc_unbind(request: Request, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/settings/account?error=会话失效"), status_code=303)
    conn = connect()
    clear_oidc_sub(conn)
    conn.close()
    return RedirectResponse(ap("/settings/account?ok=已解绑 OIDC"), status_code=303)


@app.post(ap("/settings/account/sessions/{session_id}/revoke"))
def account_session_revoke(
    request: Request, session_id: str, csrf_token: str = Form("", alias="_csrf")
):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/settings/account?error=会话失效"), status_code=303)
    current_id = (current_session(request) or {}).get("id")
    if session_id == current_id:
        return RedirectResponse(ap("/settings/account?error=不能撤销当前会话"), status_code=303)
    delete_session(session_id)
    _audit("session_revoked", f"session={session_id[:8]}…")
    return RedirectResponse(ap("/settings/account?ok=已撤销会话"), status_code=303)
