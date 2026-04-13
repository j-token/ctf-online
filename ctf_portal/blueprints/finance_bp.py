"""Challenge 4: Payroll Race (상태 정합성 미검증)
승인/취소 상태 정합성 검증 없이 스냅샷이 생성됨.
"""
import json

from flask import Blueprint, Response, current_app, flash, g, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('finance', __name__, url_prefix='/finance')


@bp.route('/')
@login_required
def finance_index():
    db = get_db()
    requests_list = db.execute(
        'SELECT pr.*, u.nickname AS employee_name '
        'FROM payroll_requests pr '
        'JOIN users u ON pr.employee_id = u.id '
        'ORDER BY pr.created_at DESC'
    ).fetchall()
    return render_template('finance/index.html', requests=requests_list)


@bp.route('/approve', methods=['POST'])
@login_required
def finance_approve():
    request_id = request.form.get('request_id', type=int)
    db = get_db()

    # 취약점: 현재 상태 검증 없이 approve_count만 증가
    db.execute(
        "UPDATE payroll_requests "
        "SET status = 'approved', approve_count = approve_count + 1, "
        "    approved_by = ?, updated_at = datetime('now') "
        "WHERE id = ?",
        (g.user['id'], request_id)
    )
    db.commit()
    flash('정산 요청이 승인되었습니다.', 'success')
    return redirect(url_for('finance.finance_index'))


@bp.route('/cancel', methods=['POST'])
@login_required
def finance_cancel():
    request_id = request.form.get('request_id', type=int)
    db = get_db()

    # 취약점: 현재 상태 검증 없이 cancel_count만 증가
    db.execute(
        "UPDATE payroll_requests "
        "SET status = 'cancelled', cancel_count = cancel_count + 1, "
        "    updated_at = datetime('now') "
        "WHERE id = ?",
        (request_id,)
    )
    db.commit()
    flash('정산 요청이 취소되었습니다.', 'warning')
    return redirect(url_for('finance.finance_index'))


@bp.route('/snapshot', methods=['POST'])
@login_required
def finance_snapshot():
    request_id = request.form.get('request_id', type=int)
    db = get_db()

    pr = db.execute(
        'SELECT * FROM payroll_requests WHERE id = ?', (request_id,)
    ).fetchone()

    if pr is None:
        flash('정산 요청을 찾을 수 없습니다.', 'danger')
        return redirect(url_for('finance.finance_index'))

    # 취약점: 승인과 취소가 모두 발생한 모순 상태에서 FLAG 노출
    if pr['approve_count'] > 0 and pr['cancel_count'] > 0:
        flag = generate_flag('payroll_race', g.user['id'], current_app.config['SECRET_KEY'])
        snapshot = json.dumps({
            'anomaly': True,
            'flag': flag,
            'detail': 'Integrity violation: request was both approved and cancelled',
            'approve_count': pr['approve_count'],
            'cancel_count': pr['cancel_count']
        }, ensure_ascii=False)
    else:
        snapshot = json.dumps({
            'amount': pr['amount'],
            'status': pr['status'],
            'employee_id': pr['employee_id']
        }, ensure_ascii=False)

    db.execute(
        "UPDATE payroll_requests SET snapshot_data = ?, updated_at = datetime('now') WHERE id = ?",
        (snapshot, request_id)
    )
    db.commit()
    flash('정산 스냅샷이 생성되었습니다.', 'info')
    return redirect(url_for('finance.finance_index'))


@bp.route('/snapshot/<int:request_id>')
@login_required
def finance_snapshot_detail(request_id):
    """스냅샷 JSON 원본 반환. 이상 탐지 시 FLAG가 포함됨."""
    db = get_db()
    pr = db.execute(
        'SELECT snapshot_data FROM payroll_requests WHERE id = ?', (request_id,)
    ).fetchone()

    if pr is None or pr['snapshot_data'] is None:
        return Response('{"error": "snapshot not found"}', mimetype='application/json', status=404)

    return Response(pr['snapshot_data'], mimetype='application/json')
