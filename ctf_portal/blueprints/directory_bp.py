"""Challenge 1: Employee Directory Leak (IDOR)
소유권 검증 없이 다른 직원의 private_note가 노출됨.
"""
from flask import Blueprint, current_app, g, render_template

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('directory', __name__, url_prefix='/directory')


@bp.route('/')
@login_required
def directory_list():
    db = get_db()
    profiles = db.execute(
        'SELECT dp.user_id, u.nickname, dp.department, dp.position, dp.email '
        'FROM directory_profiles dp '
        'JOIN users u ON dp.user_id = u.id '
        'ORDER BY dp.department, u.nickname'
    ).fetchall()
    return render_template('directory/list.html', profiles=profiles)


@bp.route('/<int:user_id>')
@login_required
def directory_profile(user_id):
    db = get_db()
    profile = db.execute(
        'SELECT dp.*, u.nickname '
        'FROM directory_profiles dp '
        'JOIN users u ON dp.user_id = u.id '
        'WHERE dp.user_id = ?',
        (user_id,)
    ).fetchone()

    if profile is None:
        return render_template('directory/list.html', profiles=[], error='프로필을 찾을 수 없습니다.')

    # 취약점: 소유권 검증 없이 private_note 포함 전체 프로필 반환
    # private_note에 동적 플래그 삽입 (요청자 기준)
    private_note = profile['private_note'] or ''
    if '{{FLAG}}' in private_note:
        flag = generate_flag('employee_directory_leak', g.user['id'], current_app.config['SECRET_KEY'])
        private_note = private_note.replace('{{FLAG}}', flag)

    return render_template('directory/profile.html', profile=profile, private_note=private_note)
