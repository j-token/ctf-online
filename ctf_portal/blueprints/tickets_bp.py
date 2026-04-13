"""Challenge 2: Ticket Ghost (300pt)
JWT alg:none 위조 → 권한 상승 → 상태 전이 + XOR 암호화 메모 복호화.
재오픈은 admin role만 가능. JWT의 role을 admin으로 변조하여 우회.
내부 메모는 XOR 인코딩되어 노출, 키는 SHA256(ticket_id)[:16].
"""
import hashlib

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('tickets', __name__, url_prefix='/tickets')


def _xor_encode(data_bytes, key_bytes):
    return bytes(d ^ key_bytes[i % len(key_bytes)] for i, d in enumerate(data_bytes))


@bp.route('/')
@login_required
def ticket_list():
    db = get_db()
    tickets = db.execute(
        'SELECT t.*, u.nickname AS creator_name '
        'FROM tickets t '
        'JOIN users u ON t.created_by = u.id '
        'ORDER BY t.updated_at DESC'
    ).fetchall()
    return render_template('tickets/list.html', tickets=tickets)


@bp.route('/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    db = get_db()
    ticket = db.execute(
        'SELECT t.*, u.nickname AS creator_name '
        'FROM tickets t '
        'JOIN users u ON t.created_by = u.id '
        'WHERE t.id = ?',
        (ticket_id,)
    ).fetchone()

    if ticket is None:
        flash('티켓을 찾을 수 없습니다.', 'danger')
        return redirect(url_for('tickets.ticket_list'))

    # JWT에서 가져온 role 확인
    is_admin = getattr(g, 'jwt_role', None) == 'admin'

    # 재오픈된 티켓: 암호화된 내부 메모 표시
    encrypted_memo = None
    memo_key_hint = None
    if ticket['status'] == 'reopened' and ticket['internal_memo']:
        raw_memo = ticket['internal_memo']
        # {{FLAG}} 플레이스홀더 치환
        if '{{FLAG}}' in raw_memo:
            flag = generate_flag('ticket_ghost', g.user['id'], current_app.config['SECRET_KEY'])
            raw_memo = raw_memo.replace('{{FLAG}}', flag)

        # XOR 인코딩 (키: SHA256(ticket_id)[:16])
        key = hashlib.sha256(str(ticket_id).encode()).hexdigest()[:16].encode()
        encrypted_memo = _xor_encode(raw_memo.encode('utf-8'), key).hex()
        memo_key_hint = f'SHA256("{ticket_id}") 앞 16바이트'

    return render_template('tickets/detail.html',
                           ticket=ticket,
                           is_admin=is_admin,
                           encrypted_memo=encrypted_memo,
                           memo_key_hint=memo_key_hint)


@bp.route('/<int:ticket_id>/reopen', methods=['POST'])
@login_required
def ticket_reopen(ticket_id):
    # admin role만 재오픈 가능 (JWT role 기반 검사)
    jwt_role = getattr(g, 'jwt_role', None)
    if jwt_role != 'admin':
        return jsonify({
            'error': 'admin 권한이 필요합니다.',
            'your_role': jwt_role,
            'hint': '인증 토큰의 권한 정보를 확인하세요.'
        }), 403

    db = get_db()
    db.execute(
        "UPDATE tickets SET status = 'reopened', updated_at = datetime('now') WHERE id = ?",
        (ticket_id,)
    )
    db.commit()
    flash('티켓이 재오픈되었습니다.', 'warning')
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))
