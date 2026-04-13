"""Challenge 5: Report Relay (450pt)
SSTI + attr() + hex escape(\x5f) 필터 우회 → Python internals → 플래그 파일 읽기.
블랙리스트: '.', '_', '[]', 주요 키워드. 우회: attr() + \x5f.
flag_path 변수로 플래그 파일 경로 노출 → RCE로 파일 읽기.
"""
import os
import re

from flask import Blueprint, current_app, flash, g, redirect, render_template, render_template_string, request, url_for

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('reports', __name__, url_prefix='/reports')

# SSTI 블랙리스트 (우회 대상)
# '.' 과 '__'(더블 언더스코어)를 차단. 단일 '_'는 허용 (flag_path 등 접근 가능)
BLACKLIST = ['.', '__', '[', ']', '+', 'class', 'subclasses', 'globals',
             'builtins', 'import', 'config', 'review_flag', 'os', 'eval', 'exec']


def _check_blacklist(content):
    """입력 내용에서 블랙리스트 키워드 검사. 위반 시 차단 목록 반환."""
    found = []
    for keyword in BLACKLIST:
        if keyword in content:
            found.append(keyword)
    return found


@bp.route('/')
@login_required
def report_list():
    db = get_db()
    reports = db.execute(
        'SELECT r.*, u.nickname AS submitter_name '
        'FROM reports r '
        'JOIN users u ON r.submitted_by = u.id '
        'ORDER BY r.created_at DESC'
    ).fetchall()
    return render_template('reports/list.html', reports=reports)


@bp.route('/', methods=['POST'])
@login_required
def report_create():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if not title or not content:
        flash('제목과 내용을 모두 입력해 주세요.', 'danger')
        return redirect(url_for('reports.report_list'))

    # 블랙리스트 체크 (차단 시 전체 목록 반환 — 힌트)
    violations = _check_blacklist(content)
    if violations:
        flash(f'금지된 표현이 포함되어 있습니다. 차단 목록: {", ".join(BLACKLIST)}', 'danger')
        return redirect(url_for('reports.report_list'))

    db = get_db()
    db.execute(
        'INSERT INTO reports (title, content, submitted_by) VALUES (?, ?, ?)',
        (title, content, g.user['id'])
    )
    db.commit()
    flash('신고가 접수되었습니다.', 'success')
    return redirect(url_for('reports.report_list'))


@bp.route('/<int:report_id>/preview')
@login_required
def report_preview(report_id):
    db = get_db()
    report = db.execute(
        'SELECT r.*, u.nickname AS submitter_name '
        'FROM reports r '
        'JOIN users u ON r.submitted_by = u.id '
        'WHERE r.id = ?',
        (report_id,)
    ).fetchone()

    if report is None:
        flash('신고를 찾을 수 없습니다.', 'danger')
        return redirect(url_for('reports.report_list'))

    # 동적 플래그 파일 생성 (/tmp/report_flag_<user_id>.txt)
    flag = generate_flag('report_relay', g.user['id'], current_app.config['SECRET_KEY'])
    flag_dir = os.path.join(current_app.instance_path, 'flags')
    os.makedirs(flag_dir, exist_ok=True)
    flag_path = os.path.join(flag_dir, f'report_flag_{g.user["id"]}.txt')
    with open(flag_path, 'w') as f:
        f.write(flag)

    # SSTI: render_template_string으로 사용자 입력 렌더링 (취약점)
    # 블랙리스트는 저장 시에만 체크, 렌더링 시에는 체크하지 않음
    # (이미 저장된 content는 블랙리스트를 통과한 것이므로)
    try:
        template_str = (
            '{% extends "reports/preview_base.html" %}'
            '{% block rendered_content %}' + report['content'] + '{% endblock %}'
        )
        rendered = render_template_string(
            template_str,
            report=report,
            flag_path=flag_path,
            review_flag=flag,
        )
        return rendered
    except Exception as e:
        return render_template('reports/preview.html',
                               report=report,
                               rendered_content=f'렌더링 오류: {str(e)}')
