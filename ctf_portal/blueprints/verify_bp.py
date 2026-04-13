"""Challenge 6: Nonce Museum (500pt)
Known-plaintext XOR Recovery → SQLi (검증 로그) → 비공개 nonce 추출
→ 시간 제한 챌린지-응답 → FLAG.
"""
import time
import secrets

from flask import Blueprint, current_app, flash, g, jsonify, render_template, request, session

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('verify', __name__, url_prefix='/verify')


def xor_sign(message_bytes, nonce_bytes):
    sig = bytearray(len(message_bytes))
    for i in range(len(message_bytes)):
        sig[i] = message_bytes[i] ^ nonce_bytes[i % len(nonce_bytes)]
    return bytes(sig)


@bp.route('/')
@login_required
def verify_index():
    db = get_db()
    # 공개 샘플: nonce 컬럼 숨김 (message + signature만 노출)
    samples = db.execute(
        'SELECT id, label, message, signature FROM verification_samples WHERE is_public = 1'
    ).fetchall()
    return render_template('verify/index.html', samples=samples)


@bp.route('/logs')
@login_required
def verify_logs():
    """검증 로그 조회. 취약점: 날짜 파라미터가 SQL에 직접 삽입 (SQLi)."""
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')

    if not date_from or not date_to:
        return jsonify({
            'error': '날짜 범위를 지정하세요.',
            'example': '/verify/logs?from=2026-01-01&to=2026-12-31'
        }), 400

    db = get_db()

    # 취약점: 파라미터를 쿼리에 직접 삽입 (prepared statement 미사용)
    query = (
        "SELECT vl.id, vl.sample_id, vl.action, vl.performed_at, vs.label "
        "FROM verification_logs vl "
        "JOIN verification_samples vs ON vl.sample_id = vs.id "
        f"WHERE vl.performed_at >= '{date_from}' AND vl.performed_at <= '{date_to}' "
        "ORDER BY vl.performed_at DESC"
    )

    try:
        results = db.execute(query).fetchall()
        return jsonify({
            'count': len(results),
            'logs': [
                {
                    'id': r['id'],
                    'sample_id': r['sample_id'],
                    'action': r['action'],
                    'performed_at': r['performed_at'],
                    'label': r['label']
                }
                for r in results
            ]
        })
    except Exception as e:
        return jsonify({'error': f'쿼리 오류: {str(e)}'}), 500


@bp.route('/challenge')
@login_required
def verify_challenge():
    """시간 제한 챌린지 발급. 60초 내에 서명을 제출해야 함."""
    # 챌린지 메시지 생성
    timestamp = int(time.time())
    challenge_msg = f'verify:audit:{timestamp}'
    nonce_group = secrets.choice([1, 2])

    # 세션에 챌린지 저장
    session['verify_challenge'] = {
        'message': challenge_msg,
        'nonce_group': nonce_group,
        'expires_at': timestamp + 60
    }

    return jsonify({
        'message': challenge_msg,
        'nonce_group': nonce_group,
        'expires_in': 60,
        'instruction': '이 메시지에 대한 유효한 XOR 서명을 생성하여 제출하세요.'
    })


@bp.route('/', methods=['POST'])
@login_required
def verify_submit():
    message = request.form.get('message', '').strip()
    signature = request.form.get('signature', '').strip()
    db = get_db()

    samples = db.execute(
        'SELECT id, label, message, signature FROM verification_samples WHERE is_public = 1'
    ).fetchall()

    # 챌린지 확인
    challenge = session.get('verify_challenge')
    if not challenge:
        return jsonify({
            'error': 'no_active_challenge',
            'hint': 'GET /verify/challenge 로 챌린지를 먼저 발급받으세요.'
        }), 400

    if int(time.time()) > challenge['expires_at']:
        session.pop('verify_challenge', None)
        return jsonify({
            'error': 'challenge_expired',
            'hint': '챌린지가 만료되었습니다. 새 챌린지를 발급받으세요.'
        }), 400

    if message != challenge['message']:
        return jsonify({
            'error': 'message_mismatch',
            'expected_message': challenge['message'],
            'hint': '챌린지에서 받은 메시지를 그대로 사용하세요.'
        }), 400

    if not signature:
        flash('서명을 입력해 주세요.', 'danger')
        return render_template('verify/index.html', samples=samples)

    # 해당 nonce_group의 nonce로 검증
    nonce_row = db.execute(
        'SELECT nonce FROM verification_samples WHERE nonce_group = ? LIMIT 1',
        (challenge['nonce_group'],)
    ).fetchone()

    if nonce_row is None:
        return jsonify({'error': 'nonce_group not found'}), 500

    nonce = bytes.fromhex(nonce_row['nonce'])

    try:
        expected_sig = xor_sign(message.encode('utf-8'), nonce)
        if expected_sig == bytes.fromhex(signature):
            session.pop('verify_challenge', None)
            flag = generate_flag('nonce_museum', g.user['id'], current_app.config['SECRET_KEY'])
            return jsonify({'success': True, 'flag': flag, 'message': '서명 검증 성공!'})
        else:
            return jsonify({
                'error': 'signature_mismatch',
                'hint': f'nonce_group {challenge["nonce_group"]}에 해당하는 올바른 nonce를 사용하세요.',
                'nonce_count': 2
            }), 400
    except (ValueError, Exception):
        return jsonify({'error': '서명 형식이 올바르지 않습니다. hex 인코딩된 문자열을 입력하세요.'}), 400
