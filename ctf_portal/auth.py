import functools

from flask import g, redirect, session, url_for

from .db import get_db


def get_current_user():
    """세션에서 현재 로그인 사용자를 조회하여 g.user에 캐시."""
    if 'user' not in g:
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            g.user = get_db().execute(
                'SELECT * FROM users WHERE id = ?', (user_id,)
            ).fetchone()
    return g.user


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_current_user() is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
