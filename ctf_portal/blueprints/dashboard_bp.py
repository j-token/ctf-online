from flask import Blueprint, g, render_template

from ..auth import login_required
from ..db import get_db

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user_id = g.user['id']

    # 현재 사용자 총점
    score_row = db.execute(
        'SELECT COALESCE(SUM(c.points), 0) AS total '
        'FROM solved_challenges sc '
        'JOIN challenges c ON sc.challenge_id = c.id '
        'WHERE sc.user_id = ?',
        (user_id,)
    ).fetchone()
    total_score = score_row['total']

    # 랭킹 계산 (점수 내림차순, 동점 시 첫 풀이 시각 오름차순)
    rankings = db.execute(
        'SELECT u.id, u.nickname, '
        '  COALESCE(SUM(c.points), 0) AS total_score, '
        '  MIN(sc.solved_at) AS first_solve '
        'FROM users u '
        'LEFT JOIN solved_challenges sc ON u.id = sc.user_id '
        'LEFT JOIN challenges c ON sc.challenge_id = c.id '
        'GROUP BY u.id '
        'ORDER BY total_score DESC, first_solve ASC'
    ).fetchall()

    rank = 1
    for i, r in enumerate(rankings):
        if r['id'] == user_id:
            rank = i + 1
            break

    # 최근 풀이 내역
    recent_solves = db.execute(
        'SELECT c.title, c.points, sc.solved_at '
        'FROM solved_challenges sc '
        'JOIN challenges c ON sc.challenge_id = c.id '
        'WHERE sc.user_id = ? '
        'ORDER BY sc.solved_at DESC LIMIT 5',
        (user_id,)
    ).fetchall()

    # 전체 문제 수
    total_challenges = db.execute('SELECT COUNT(*) AS cnt FROM challenges').fetchone()['cnt']
    solved_count = db.execute(
        'SELECT COUNT(*) AS cnt FROM solved_challenges WHERE user_id = ?',
        (user_id,)
    ).fetchone()['cnt']

    return render_template('dashboard.html',
                           total_score=total_score,
                           rank=rank,
                           total_users=len(rankings),
                           recent_solves=recent_solves,
                           total_challenges=total_challenges,
                           solved_count=solved_count)
