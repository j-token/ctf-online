from flask import Blueprint, current_app, flash, g, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import create_jwt
from ..db import get_db

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    # session.get('user_id') 대신 g.user 사용: DB 미존재 사용자(Railway 재배포 후 세션 잔류)로 인한 무한 리디렉션 방지
    if g.user:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        db = get_db()
        error = None

        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            error = '사용자명 또는 비밀번호가 올바르지 않습니다.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']

            # JWT 쿠키 발행 (Ch2 공격 표면)
            jwt_payload = {
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'iat': __import__('time').time()
            }
            token = create_jwt(jwt_payload, current_app.config['SECRET_KEY'])

            resp = make_response(redirect(url_for('dashboard.dashboard')))
            resp.set_cookie('ic_token', token, httponly=True, samesite='Lax')
            return resp

        flash(error, 'danger')

    return render_template('login.html')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if g.user:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        nickname = request.form.get('nickname', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        db = get_db()
        error = None

        if not username:
            error = '사용자명을 입력해 주세요.'
        elif not nickname:
            error = '닉네임을 입력해 주세요.'
        elif not password:
            error = '비밀번호를 입력해 주세요.'
        elif len(password) < 4:
            error = '비밀번호는 4자 이상이어야 합니다.'
        elif password != confirm:
            error = '비밀번호가 일치하지 않습니다.'
        elif db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = f'이미 사용 중인 사용자명입니다: {username}'

        if error is None:
            db.execute(
                'INSERT INTO users (username, password, nickname, role) VALUES (?, ?, ?, ?)',
                (username, generate_password_hash(password), nickname, 'employee')
            )
            db.commit()
            flash('회원가입이 완료되었습니다. 로그인해 주세요.', 'success')
            return redirect(url_for('auth.login'))

        flash(error, 'danger')

    return render_template('register.html')


@bp.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('auth.login')))
    resp.delete_cookie('ic_token')
    return resp
