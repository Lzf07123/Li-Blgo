"""Li&Blog 管理后台主应用：Setup、双登录、八栏目、预览与重建。"""

import datetime
from contextlib import asynccontextmanager
from typing import Optional

import yaml
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from admin import build, content as store, oidc, security
from admin.config import ROOT, settings
from admin.db import connect, create_admin, get_admin, init_db
from admin.session import COOKIE, create_session, delete_session, get_session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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
templates = Jinja2Templates(directory=str(ROOT / "admin" / "templates"))
rate = security.RateLimiter()

settings.preview_root.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ROOT / "themes" / "blog-theme" / "static")), name="static")
app.mount(
    f"/{settings.admin_path}/preview-out",
    StaticFiles(directory=str(settings.preview_root)),
    name="preview-out",
)


def ap(path: str) -> str:
    return f"/{settings.admin_path}{path}"


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
    flash = request.query_params.get("ok") or request.query_params.get("error")
    context.setdefault("flash", flash)
    return templates.TemplateResponse(request, name, context)


def require_login(request: Request) -> None:
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if not has_admin:
        raise HTTPException(status_code=302, headers={"Location": ap("/setup")})
    if current_session(request) is None:
        raise HTTPException(status_code=302, headers={"Location": ap("/login")})


def parse_yaml_block(text: str, label: str):
    try:
        return yaml.safe_load(text or "{}"), None
    except yaml.YAMLError as exc:
        return None, f"{label} 解析失败：{exc}"


def after_build_redirect(base: str) -> RedirectResponse:
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"{base}?error=构建失败"), status_code=303)
    return RedirectResponse(ap(f"{base}?ok=已保存并重建({elapsed}s)"), status_code=303)


# ---------- 登录与登出 ----------

@app.get(ap("/login"), response_class=HTMLResponse)
def login_page(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if not has_admin:
        return RedirectResponse(ap("/setup"), status_code=302)
    ensure_anon_session(request)
    response = render(request, "login.html", {"oidc_enabled": oidc.enabled()})
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
        return render(request, "login.html", {"error": "会话失效，请重试", "oidc_enabled": oidc.enabled()})
    key = f"{client_ip(request)}:{username}"
    if not rate.allow(key, 5, 60):
        return render(request, "login.html", {"error": "尝试次数过多，请稍后再试", "oidc_enabled": oidc.enabled()})
    conn = connect()
    admin = get_admin(conn)
    conn.close()
    if admin is None or not security.verify_password(password, admin["password_hash"]):
        return render(request, "login.html", {"error": "用户名或密码错误", "oidc_enabled": oidc.enabled()})
    session_id = create_session("local")
    response = RedirectResponse(ap("/"), status_code=303)
    response.set_cookie(
        COOKIE, session_id, httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.session_ttl,
    )
    return response


@app.get(ap("/logout"))
def logout(request: Request):
    sess = current_session(request)
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
    store.save_yaml("brand", brand)
    store.save_yaml("profile", profile)
    return RedirectResponse(ap("/setup/account"), status_code=303)


@app.get(ap("/setup/account"), response_class=HTMLResponse)
def setup_account_page(request: Request):
    conn = connect()
    has_admin = get_admin(conn) is not None
    conn.close()
    if has_admin:
        return RedirectResponse(ap("/"), status_code=302)
    ensure_anon_session(request)
    response = render(request, "setup_account.html", {})
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
    if len(username) < 3 or len(password) < 8:
        return RedirectResponse(ap("/setup/account?error=用户名至少3位，密码至少8位"), status_code=303)
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
    ensure_anon_session(request)
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
    conn = connect()
    stats = conn.execute("SELECT path, day, views FROM stats ORDER BY views DESC LIMIT 20").fetchall()
    conn.close()
    return render(request, "dashboard.html", {"counts": counts, "stats": stats})


@app.get(ap("/stats"), response_class=HTMLResponse)
def stats_page(request: Request):
    require_login(request)
    conn = connect()
    rows = conn.execute("SELECT path, day, views FROM stats ORDER BY views DESC LIMIT 200").fetchall()
    conn.close()
    return render(request, "stats.html", {"rows": rows})


@app.post(ap("/rebuild"))
def rebuild(request: Request, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap("/?error=会话失效"), status_code=303)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"/?error=构建失败:{result.stderr[-200:]}"), status_code=303)
    return RedirectResponse(ap(f"/?ok=构建成功({elapsed}s)"), status_code=303)


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
        ]
    if section == "projects":
        return [
            ("title", "名称", "text", fm.get("title", "")),
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
def section_list(request: Request, section: str):
    require_login(request)
    if section not in SECTIONS:
        raise HTTPException(404)
    if SECTIONS[section]["single"]:
        return RedirectResponse(ap(f"/{section}/edit"), status_code=302)
    items = store.list_markdown(section)
    return render(request, "list.html", {"section": section, "label": SECTIONS[section]["label"], "items": items})


@app.get(ap("/{section}/new"), response_class=HTMLResponse)
def section_new(request: Request, section: str):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"]:
        raise HTTPException(404)
    return render(
        request,
        "edit.html",
        {"section": section, "slug": "", "label": SECTIONS[section]["label"], "fields": _edit_fields(section, {})},
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
        {"section": section, "slug": slug, "label": SECTIONS[section]["label"], "fields": _edit_fields(section, fm), "body": body},
    )


@app.get(ap("/{section}/{slug}/edit"), response_class=HTMLResponse)
def section_slug_edit(request: Request, section: str, slug: str):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"]:
        raise HTTPException(404)
    fm, body = store.read_markdown(section, slug)
    return render(
        request,
        "edit.html",
        {"section": section, "slug": slug, "label": SECTIONS[section]["label"], "fields": _edit_fields(section, fm), "body": body},
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
    repo: str = Form(""),
    tech: str = Form(""),
    kind: str = Form(""),
    badge_label: str = Form(""),
    badge_color: str = Form(""),
    badge_href: str = Form(""),
    body: str = Form(""),
):
    require_login(request)
    if section not in SECTIONS or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/{section}?error=会话失效"), status_code=303)
    if new_slug:
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
            if section == "posts":
                fm = {"title": title, "date": date, "status": status,
                      "tags": [t.strip() for t in tags.split(",") if t.strip()], "summary": summary}
                for key in ("math", "mermaid", "cover"):
                    if key in old:
                        fm[key] = old[key]
            elif section == "projects":
                fm = {"title": title, "repo": repo, "status": status,
                      "tech": [t.strip() for t in tech.split(",") if t.strip()], "summary": summary,
                      "badge": {"label": badge_label, "color": badge_color, "href": badge_href},
                      "show_on_home": old.get("show_on_home", True)}
            else:
                fm = {"title": title, "date": date, "kind": kind, "summary": summary}
            store.write_markdown(section, slug, fm, body)
    except ValueError as exc:
        return RedirectResponse(ap(f"/{section}?error={exc}"), status_code=303)
    if action == "preview":
        result, elapsed = build.run_preview()
        if result.returncode != 0:
            return RedirectResponse(ap(f"/{section}?error=预览构建失败"), status_code=303)
        return RedirectResponse(ap(f"/preview/{section}/{slug}"), status_code=303)
    return after_build_redirect(f"/{section}")


@app.post(ap("/{section}/{slug}/delete"))
def section_delete(request: Request, section: str, slug: str, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if section not in SECTIONS or SECTIONS[section]["single"] or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/{section}?error=会话失效"), status_code=303)
    store.delete_markdown(section, slug)
    result, elapsed = build.run_full()
    if result.returncode != 0:
        return RedirectResponse(ap(f"/{section}?error=删除后构建失败"), status_code=303)
    return RedirectResponse(ap(f"/{section}?ok=已删除并重建({elapsed}s)"), status_code=303)


@app.get(ap("/preview/{section}/{slug}"), response_class=HTMLResponse)
def preview_page(request: Request, section: str, slug: str):
    require_login(request)
    target = settings.preview_root / section / slug / "index.html"
    exists = target.exists()
    return render(
        request,
        "preview.html",
        {"section": section, "slug": slug, "exists": exists,
         "src": f"/{settings.admin_path}/preview-out/{section}/{slug}/index.html"},
    )


# ---------- 配置表单 ----------

CONFIG_PAGES = {
    "brand": ("品牌", ["name", "tagline", "promise", "persona", "copyright", "icp", "police", "logo", "favicon"]),
    "strings": ("页面文案", ["nav", "home", "common", "footer"]),
    "homepage": ("首页设置", ["hero", "journey", "posts", "projects"]),
    "profile": ("关于我资料", ["name", "identity", "direction", "goal", "skills", "links"]),
}


@app.get(ap("/config/{name}"), response_class=HTMLResponse)
def config_edit(request: Request, name: str):
    require_login(request)
    if name not in CONFIG_PAGES:
        raise HTTPException(404)
    label, keys = CONFIG_PAGES[name]
    data = store.load_yaml(name)
    fields = []
    for key in keys:
        value = data.get(key, {})
        if isinstance(value, (dict, list)):
            value = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
            fields.append({"name": key, "label": key, "type": "textarea", "value": value})
        else:
            fields.append({"name": key, "label": key, "type": "text", "value": value if value is not None else ""})
    return render(request, "config_form.html", {"name": name, "label": label, "fields": fields})


@app.post(ap("/config/{name}"))
async def config_save(request: Request, name: str, csrf_token: str = Form("", alias="_csrf")):
    require_login(request)
    if name not in CONFIG_PAGES or not csrf_ok(request, {"_csrf": csrf_token}):
        return RedirectResponse(ap(f"/config/{name}?error=会话失效"), status_code=303)
    form = await request.form()
    data = store.load_yaml(name)
    label, keys = CONFIG_PAGES[name]
    for key in keys:
        raw = form.get(key, "")
        if isinstance(data.get(key), (dict, list)) or str(raw).lstrip().startswith(("-", "{", "[")):
            parsed, err = parse_yaml_block(str(raw), key)
            if err:
                return RedirectResponse(ap(f"/config/{name}?error={err}"), status_code=303)
            data[key] = parsed
        else:
            data[key] = str(raw)
    store.save_yaml(name, data)
    return after_build_redirect(f"/config/{name}")
