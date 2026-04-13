import base64
import functools
import hashlib
import hmac
import json
import time

from flask import current_app, g, redirect, request, session, url_for

from .db import get_db


# === JWT 유틸리티 (Ch2: alg:none 취약점 포함) ===


def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s):
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def create_jwt(payload, secret):
    """HS256 JWT 생성."""
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header).encode())
    p = _b64url_encode(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    s = _b64url_encode(sig)
    return f"{h}.{p}.{s}"


def verify_jwt(token, secret):
    """JWT 검증. 취약점: alg:none을 허용하여 서명 없이 통과 가능."""
    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
    except (json.JSONDecodeError, Exception):
        return None

    # 취약점: alg가 none이면 서명 검증을 건너뜀
    alg = header.get("alg", "").lower()
    if alg == "none":
        return payload

    if alg == "hs256":
        expected_sig = hmac.new(
            secret.encode(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(parts[2])
        if hmac.compare_digest(expected_sig, actual_sig):
            return payload

    return None


# === 사용자 로드 ===


def get_current_user():
    """JWT 쿠키 또는 세션에서 현재 사용자를 로드."""
    if "user" not in g:
        g.user = None
        g.jwt_payload = None

        # 1차: JWT 쿠키 (ic_token)
        token = request.cookies.get("ic_token")
        if token:
            payload = verify_jwt(token, current_app.config["SECRET_KEY"])
            if payload and "user_id" in payload:
                g.jwt_payload = payload
                g.user = (
                    get_db()
                    .execute("SELECT * FROM users WHERE id = ?", (payload["user_id"],))
                    .fetchone()
                )
                if g.user:
                    # JWT의 role을 g에 저장 (취약점: JWT에서 온 role을 신뢰)
                    g.jwt_role = payload.get("role", g.user["role"])
                    return g.user

        # 2차: 세션 기반 (fallback)
        user_id = session.get("user_id")
        if user_id is not None:
            g.user = (
                get_db()
                .execute("SELECT * FROM users WHERE id = ?", (user_id,))
                .fetchone()
            )
            if g.user:
                g.jwt_role = g.user["role"]
                return g.user

    return g.user


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_current_user() is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
