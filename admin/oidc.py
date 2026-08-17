"""Li&Pass OIDC：登录 / 绑定 / 回程登出（依据对接文档契约实现）。"""

import base64
import hashlib
import time
from typing import Optional

import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt
from fastapi import Request
from fastapi.responses import RedirectResponse

from admin.config import settings
from admin.db import connect, get_admin, set_oidc_sub
from admin.session import create_session, delete_by_oidc

_oauth: Optional[OAuth] = None

BACKCHANNEL_EVENT = "http://schemas.openid.net/event/backchannel-logout"


def oauth() -> OAuth:
    global _oauth
    if _oauth is None:
        client = OAuth()
        client.register(
            "lipass",
            client_id=settings.lipass_client_id,
            client_secret=settings.lipass_client_secret,
            server_metadata_url=settings.lipass_issuer + "/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email", "code_challenge_method": "S256"},
        )
        _oauth = client
    return _oauth


def enabled() -> bool:
    return bool(settings.lipass_issuer and settings.lipass_client_id)


def redirect_uri(request: Request) -> str:
    if settings.lipass_redirect_uri:
        return settings.lipass_redirect_uri
    return str(request.base_url).rstrip("/") + f"/{settings.admin_path}/oidc/callback"


def authorize_start(request: Request, flow: str) -> RedirectResponse:
    if not enabled():
        raise ValueError("OIDC 未配置")
    request.session["oidc_flow"] = flow
    return oauth().lipass.authorize_redirect(request, redirect_uri(request))


def _check_at_hash(access_token: str, at_hash: Optional[str]) -> bool:
    if not at_hash:
        return True
    digest = hashlib.sha256(access_token.encode("utf-8")).digest()[:16]
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode() == at_hash


async def handle_callback(request: Request):
    """返回 (status, sub, session_id, sid)；status ∈ ok/denied/bound。"""
    flow = request.session.pop("oidc_flow", "login")
    client = oauth().lipass
    token = await client.authorize_access_token(request)
    claims = client.parse_id_token(request, token)
    access_token = token.get("access_token", "")
    if not _check_at_hash(access_token, claims.get("at_hash")):
        raise ValueError("at_hash 校验失败")
    metadata = await client.load_server_metadata()
    async with httpx.AsyncClient() as hx:
        resp = await hx.get(
            metadata["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        userinfo = resp.json()
    sub = userinfo["sub"]
    sid = claims.get("sid")

    conn = connect()
    admin = get_admin(conn)
    if flow in ("setup_bind", "settings_bind"):
        if admin is None:
            conn.close()
            raise ValueError("管理员不存在")
        set_oidc_sub(conn, sub)
        conn.close()
        return "bound", sub, None, sid
    conn.close()
    if admin is None or admin["oidc_sub"] != sub:
        return "denied", sub, None, sid
    session_id = create_session("oidc", sub=sub, sid=sid)
    return "ok", sub, session_id, sid


async def backchannel_logout(request: Request) -> bool:
    form = await request.form()
    logout_token = form.get("logout_token")
    if not logout_token or not enabled():
        return False
    client = oauth().lipass
    metadata = await client.load_server_metadata()
    async with httpx.AsyncClient() as hx:
        resp = await hx.get(metadata["jwks_uri"], timeout=10)
        resp.raise_for_status()
        jwks = resp.json()
    claims = jwt.decode(logout_token, jwks)
    now = int(time.time())
    aud = claims.get("aud") or []
    if isinstance(aud, str):
        aud = [aud]
    events = claims.get("events") or {}
    valid = (
        claims.get("iss") == metadata["issuer"]
        and settings.lipass_client_id in aud
        and now - 120 <= claims.get("iat", 0) <= now
        and now - 120 <= claims.get("exp", 0) <= now
        and bool(claims.get("jti"))
        and BACKCHANNEL_EVENT in events
    )
    if not valid:
        return False
    conn = connect()
    conn.execute("INSERT OR IGNORE INTO jti_cache (jti, exp) VALUES (?, ?)", (claims["jti"], claims["exp"]))
    conn.commit()
    conn.close()
    delete_by_oidc(claims.get("sub", ""), claims.get("sid", ""))
    return True
