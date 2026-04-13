"""Challenge 4: Payroll Race (400pt)
Real Race Condition (TOCTOU) → 불가능한 상태 → anomaly 스냅샷.
3단계 결재. 같은 사용자 연속 승인 불가이지만, non-atomic 체크로 race condition 우회 가능.
"""
import json
import time

from flask import Blueprint, Response, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('finance', __name__, url_prefix='/finance')

REQUIRED_APPROVALS = 3


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
    return render_template('finance/index.html', requests=requests_list,
                           required_approvals=REQUIRED_APPROVALS)


@bp.route('/approve', methods=['POST'])
@login_required
def finance_approve():
    request_id = request.form.get('request_id', type=int)
    db = get_db()

    pr = db.execute('SELECT * FROM payroll_requests WHERE id = ?', (request_id,)).fetchone()
    if pr is None:
        return jsonify({'error': '정산 요청을 찾을 수 없습니다.'}), 404

    # 승인 체인 로드
    chain = json.loads(pr['approval_chain'])

    # 같은 사용자 중복 체크 (TOCTOU 취약: read → check → sleep → write)
    user_id = g.user['id']
    if user_id in chain:
        return jsonify({
            'error': '동일 사용자의 연속 승인은 불가합니다.',
            'your_id': user_id,
            'current_chain': chain,
            'processing_time_ms': 50,
            'policy': '3단계 다중 결재 필수. 동시 접근 시 예기치 않은 동작이 발생할 수 있습니다.'
        }), 409

    # 취약점: 체크와 쓰기 사이에 의도적 지연 → race condition 가능
    # 모든 동시 요청이 여기서 대기하는 동안 모두 빈 chain을 읽은 상태
    time.sleep(0.1)

    # DB 수준에서 atomic하게 카운트 증가 (chain은 race로 중복 삽입됨)
    db.execute(
        "UPDATE payroll_requests SET "
        "approve_count = approve_count + 1, "
        "approval_chain = json_insert(approval_chain, '$[#]', ?), "
        "updated_at = datetime('now') "
        "WHERE id = ?",
        (user_id, request_id)
    )
    db.commit()

    # 최신 상태 조회
    pr = db.execute('SELECT * FROM payroll_requests WHERE id = ?', (request_id,)).fetchone()
    new_count = pr['approve_count']
    if new_count >= REQUIRED_APPROVALS:
        db.execute("UPDATE payroll_requests SET status = 'final_approved' WHERE id = ?", (request_id,))
        db.commit()
        new_status = 'final_approved'
    else:
        new_status = 'partial_approved'
        db.execute("UPDATE payroll_requests SET status = 'partial_approved' WHERE id = ?", (request_id,))
        db.commit()

    return jsonify({
        'success': True,
        'approve_count': new_count,
        'required': REQUIRED_APPROVALS,
        'status': new_status,
        'message': f'{new_count}/{REQUIRED_APPROVALS} 단계 승인 완료'
    })


@bp.route('/snapshot', methods=['POST'])
@login_required
def finance_snapshot():
    request_id = request.form.get('request_id', type=int)
    db = get_db()

    pr = db.execute('SELECT * FROM payroll_requests WHERE id = ?', (request_id,)).fetchone()
    if pr is None:
        return jsonify({'error': '정산 요청을 찾을 수 없습니다.'}), 404

    chain = json.loads(pr['approval_chain'])

    # anomaly 감지: 같은 사용자가 3번 이상 승인 (race condition으로만 가능)
    from collections import Counter
    user_counts = Counter(chain)
    has_anomaly = any(count >= REQUIRED_APPROVALS for count in user_counts.values())

    if has_anomaly and pr['status'] == 'final_approved':
        flag = generate_flag('payroll_race', g.user['id'], current_app.config['SECRET_KEY'])
        snapshot = json.dumps({
            'anomaly': True,
            'integrity_check': 'same_user_multi_approve',
            'flag': flag,
            'detail': 'TOCTOU violation: same user approved multiple times via race condition',
            'approval_chain': chain,
            'user_frequency': dict(user_counts)
        }, ensure_ascii=False)
    else:
        snapshot = json.dumps({
            'amount': pr['amount'],
            'status': pr['status'],
            'approve_count': pr['approve_count'],
            'approval_chain': chain,
            'anomaly': False
        }, ensure_ascii=False)

    db.execute(
        "UPDATE payroll_requests SET snapshot_data = ?, updated_at = datetime('now') WHERE id = ?",
        (snapshot, request_id)
    )
    db.commit()

    return jsonify(json.loads(snapshot))


@bp.route('/snapshot/<int:request_id>')
@login_required
def finance_snapshot_detail(request_id):
    db = get_db()
    pr = db.execute('SELECT snapshot_data FROM payroll_requests WHERE id = ?', (request_id,)).fetchone()
    if pr is None or pr['snapshot_data'] is None:
        return jsonify({'error': 'snapshot not found'}), 404
    return Response(pr['snapshot_data'], mimetype='application/json')
