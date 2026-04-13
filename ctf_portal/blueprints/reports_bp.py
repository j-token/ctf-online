"""Challenge 5: Report Relay (Server-Side Template Injection)
사용자 입력을 Jinja2 템플릿으로 직접 렌더링함.
"""
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from jinja2 import Template

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('reports', __name__, url_prefix='/reports')


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

    db = get_db()
    db.execute(
        'INSERT INTO reports (title, content, submitted_by) VALUES (?, ?, ?)',
        (title, content, g.user['id'])
    )
    db.commit()
    flash('신고가 접수되었습니다. 관리자 미리보기에서 검토됩니다.', 'success')
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

    # 취약점: 사용자 입력을 Jinja2 템플릿으로 직접 렌더링 (SSTI)
    review_flag = generate_flag('report_relay', g.user['id'], current_app.config['SECRET_KEY'])
    try:
        rendered_content = Template(report['content']).render(
            review_flag=review_flag,
            report=report
        )
    except Exception:
        rendered_content = report['content']

    return render_template('reports/preview.html',
                           report=report,
                           rendered_content=rendered_content)
