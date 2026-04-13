"""Challenge 6: Nonce Museum (XOR nonce 재사용)
서로 다른 문서에 동일 nonce가 재사용되어 서명을 위조할 수 있음.
"""
from flask import Blueprint, current_app, flash, g, render_template, request

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('verify', __name__, url_prefix='/verify')


def xor_sign(message_bytes, nonce_bytes):
    """XOR 기반 서명 생성."""
    sig = bytearray(len(message_bytes))
    for i in range(len(message_bytes)):
        sig[i] = message_bytes[i] ^ nonce_bytes[i % len(nonce_bytes)]
    return bytes(sig)


def verify_signature(message, signature_hex, nonce_hex):
    """메시지와 서명을 nonce로 검증."""
    nonce = bytes.fromhex(nonce_hex)
    expected_sig = xor_sign(message.encode('utf-8'), nonce)
    return expected_sig == bytes.fromhex(signature_hex)


@bp.route('/')
@login_required
def verify_index():
    db = get_db()
    samples = db.execute(
        'SELECT * FROM verification_samples WHERE is_public = 1'
    ).fetchall()
    return render_template('verify/index.html', samples=samples)


@bp.route('/', methods=['POST'])
@login_required
def verify_submit():
    message = request.form.get('message', '').strip()
    signature = request.form.get('signature', '').strip()
    db = get_db()

    samples = db.execute(
        'SELECT * FROM verification_samples WHERE is_public = 1'
    ).fetchall()

    if message != 'approval:finance:admin':
        flash('검증 대상: approval:finance:admin', 'warning')
        return render_template('verify/index.html', samples=samples)

    if not signature:
        flash('서명을 입력해 주세요.', 'danger')
        return render_template('verify/index.html', samples=samples)

    # 공개 샘플과 동일한 nonce로 검증 (취약점: nonce 재사용)
    sample = db.execute(
        'SELECT nonce FROM verification_samples WHERE is_public = 1 LIMIT 1'
    ).fetchone()

    if sample is None:
        flash('검증 샘플이 없습니다.', 'danger')
        return render_template('verify/index.html', samples=samples)

    try:
        if verify_signature(message, signature, sample['nonce']):
            flag = generate_flag('nonce_museum', g.user['id'], current_app.config['SECRET_KEY'])
            flash(f'검증 성공! {flag}', 'success')
        else:
            flash('서명이 올바르지 않습니다.', 'danger')
    except (ValueError, Exception):
        flash('서명 형식이 올바르지 않습니다.', 'danger')

    return render_template('verify/index.html', samples=samples)
