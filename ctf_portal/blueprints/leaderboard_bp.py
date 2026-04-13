from flask import Blueprint, g, render_template

from ..auth import login_required
from ..db import get_db

bp = Blueprint("leaderboard", __name__)


@bp.route("/leaderboard")
@login_required
def leaderboard():
    db = get_db()

    # 순위표 쿼리 개선:
    # 1. 풀이한 사용자만 집계 (LEFT JOIN -> INNER JOIN for solved_challenges)
    # 2. NULL first_solve 처리: COALESCE로 '9999-12-31' 대체 후 정렬
    # 3. 점수 0인 사용자는 순위에서 제외 (의도: 실제 풀이자만 표시)
    rankings = db.execute(
        "SELECT u.id, u.nickname, u.role, "
        "  SUM(c.points) AS total_score, "
        "  MIN(sc.solved_at) AS first_solve, "
        "  COUNT(sc.id) AS solve_count "
        "FROM users u "
        "JOIN solved_challenges sc ON u.id = sc.user_id "
        "JOIN challenges c ON sc.challenge_id = c.id "
        "GROUP BY u.id "
        "HAVING total_score > 0 "
        "ORDER BY total_score DESC, first_solve ASC"
    ).fetchall()

    # 현재 사용자가 순위권에 없을 경우 별도 조회 (자신의 순위 확인용)
    current_user_rank = None
    current_user_id = g.user["id"]

    # 현재 사용자 점수 조회
    user_score = db.execute(
        "SELECT COALESCE(SUM(c.points), 0) AS total_score, "
        "       COUNT(sc.id) AS solve_count, "
        "       MIN(sc.solved_at) AS first_solve "
        "FROM solved_challenges sc "
        "JOIN challenges c ON sc.challenge_id = c.id "
        "WHERE sc.user_id = ?",
        (current_user_id,),
    ).fetchone()

    return render_template(
        "leaderboard.html",
        rankings=rankings,
        current_user_id=current_user_id,
        current_user_score=user_score,
    )
