from flask import Blueprint, g, render_template

from ..auth import login_required
from ..db import get_db

bp = Blueprint("leaderboard", __name__)


@bp.route("/leaderboard")
@login_required
def leaderboard():
    db = get_db()

    # LEFT JOIN으로 미풀이 사용자도 포함. COALESCE로 NULL first_solve 처리(동점 시 정렬용)
    rankings = db.execute(
        "SELECT u.id, u.nickname, u.role, "
        "  COALESCE(SUM(c.points), 0) AS total_score, "
        "  MIN(sc.solved_at) AS first_solve, "
        "  COUNT(sc.id) AS solve_count "
        "FROM users u "
        "LEFT JOIN solved_challenges sc ON u.id = sc.user_id "
        "LEFT JOIN challenges c ON sc.challenge_id = c.id "
        "GROUP BY u.id "
        "ORDER BY total_score DESC, COALESCE(first_solve, '9999-12-31') ASC"
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
