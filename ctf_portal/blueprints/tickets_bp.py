"""Challenge 2: Ticket Ghost (권한 미검증 + 상태 전이 오류)
닫힌 티켓을 재오픈하면 내부 메모가 노출됨.
"""
from flask import Blueprint, current_app, flash, g, redirect, render_template, url_for

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('tickets', __name__, url_prefix='/tickets')


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

    # 재오픈된 티켓에서 내부 메모 동적 플래그 삽입
    internal_memo = None
    if ticket['status'] == 'reopened' and ticket['internal_memo']:
        internal_memo = ticket['internal_memo']
        if '{{FLAG}}' in internal_memo:
            flag = generate_flag('ticket_ghost', g.user['id'], current_app.config['SECRET_KEY'])
            internal_memo = internal_memo.replace('{{FLAG}}', flag)

    return render_template('tickets/detail.html', ticket=ticket, internal_memo=internal_memo)


@bp.route('/<int:ticket_id>/reopen', methods=['POST'])
@login_required
def ticket_reopen(ticket_id):
    # 취약점: 권한 검증 없음 — 누구나 어떤 티켓이든 재오픈 가능
    db = get_db()
    db.execute(
        "UPDATE tickets SET status = 'reopened', updated_at = datetime('now') WHERE id = ?",
        (ticket_id,)
    )
    db.commit()
    flash('티켓이 재오픈되었습니다.', 'warning')
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))
