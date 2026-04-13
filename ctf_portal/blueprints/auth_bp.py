from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if session.get('user_id'):
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
            return redirect(url_for('dashboard.dashboard'))

        flash(error, 'danger')

    return render_template('login.html')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if session.get('user_id'):
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
    return redirect(url_for('auth.login'))
