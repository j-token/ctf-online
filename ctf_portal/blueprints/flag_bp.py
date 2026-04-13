from flask import Blueprint, current_app, g, jsonify, request

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('flag', __name__)


@bp.route('/submit-flag', methods=['POST'])
@login_required
def submit_flag():
    slug = request.form.get('challenge_slug', '')
    submitted_flag = request.form.get('flag', '').strip()
    db = get_db()

    challenge = db.execute(
        'SELECT * FROM challenges WHERE slug = ?', (slug,)
    ).fetchone()

    if not challenge:
        return jsonify({'success': False, 'message': '알 수 없는 문제입니다.'}), 400

    already = db.execute(
        'SELECT id FROM solved_challenges WHERE user_id = ? AND challenge_id = ?',
        (g.user['id'], challenge['id'])
    ).fetchone()

    if already:
        return jsonify({'success': False, 'message': '이미 풀이한 문제입니다.'})

    # 동적 플래그 생성 후 비교
    expected_flag = generate_flag(slug, g.user['id'], current_app.config['SECRET_KEY'])

    if submitted_flag == expected_flag:
        db.execute(
            'INSERT INTO solved_challenges (user_id, challenge_id) VALUES (?, ?)',
            (g.user['id'], challenge['id'])
        )
        db.commit()
        return jsonify({
            'success': True,
            'message': f'정답! +{challenge["points"]}점'
        })

    return jsonify({'success': False, 'message': '올바르지 않은 플래그입니다.'})


@bp.route('/challenges-list')
@login_required
def challenges_list():
    """플래그 제출 모달에서 사용할 문제 목록 API."""
    db = get_db()
    challenges = db.execute(
        'SELECT slug, title FROM challenges ORDER BY id'
    ).fetchall()
    return jsonify([{'slug': c['slug'], 'title': c['title']} for c in challenges])
