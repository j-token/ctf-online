from flask import Blueprint, g, render_template

from ..auth import login_required
from ..db import get_db

bp = Blueprint('leaderboard', __name__)


@bp.route('/leaderboard')
@login_required
def leaderboard():
    db = get_db()

    rankings = db.execute(
        'SELECT u.id, u.nickname, u.role, '
        '  COALESCE(SUM(c.points), 0) AS total_score, '
        '  MIN(sc.solved_at) AS first_solve, '
        '  COUNT(sc.id) AS solve_count '
        'FROM users u '
        'LEFT JOIN solved_challenges sc ON u.id = sc.user_id '
        'LEFT JOIN challenges c ON sc.challenge_id = c.id '
        'GROUP BY u.id '
        'ORDER BY total_score DESC, first_solve ASC'
    ).fetchall()

    return render_template('leaderboard.html',
                           rankings=rankings,
                           current_user_id=g.user['id'])
