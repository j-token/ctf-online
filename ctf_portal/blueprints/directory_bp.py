"""Challenge 1: Employee Directory Leak (250pt)
NoSQL-style Operator Injection → $regex Blind Extraction → Base64 디코딩.
JSON 기반 검색 API에서 $ne, $regex 등 연산자를 지원하되,
active 필터가 없어 퇴직자 데이터에 접근 가능.
$regex blind oracle로 private_note를 한 글자씩 추출.
"""
import re

from flask import Blueprint, current_app, g, jsonify, render_template, request

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('directory', __name__, url_prefix='/directory')

# 검색 API에서 허용하는 컬럼
SEARCHABLE_COLUMNS = {
    'user_id', 'department', 'position', 'email', 'phone',
    'bio', 'private_note', 'active', 'nickname', 'name'
}


def _build_condition(column, value):
    """JSON 값을 SQL 조건으로 변환. dict이면 연산자로 해석."""
    # 'name'은 nickname으로 매핑
    if column == 'name':
        column = 'u.nickname'
    elif column == 'nickname':
        column = 'u.nickname'
    elif column in ('user_id', 'department', 'position', 'email', 'phone', 'bio', 'private_note', 'active'):
        column = f'dp.{column}'
    else:
        return None, []

    if isinstance(value, dict):
        conditions = []
        params = []
        for op, operand in value.items():
            if op == '$ne':
                conditions.append(f'{column} != ?')
                params.append(operand)
            elif op == '$gt':
                conditions.append(f'{column} > ?')
                params.append(operand)
            elif op == '$lt':
                conditions.append(f'{column} < ?')
                params.append(operand)
            elif op == '$regex':
                # $regex를 SQLite LIKE/GLOB으로 변환
                # ^pattern → LIKE 'pattern%', pattern$ → LIKE '%pattern'
                pattern = str(operand)
                if pattern.startswith('^') and pattern.endswith('$'):
                    conditions.append(f'{column} = ?')
                    params.append(pattern[1:-1])
                elif pattern.startswith('^'):
                    conditions.append(f'{column} LIKE ?')
                    params.append(pattern[1:] + '%')
                elif pattern.endswith('$'):
                    conditions.append(f'{column} LIKE ?')
                    params.append('%' + pattern[:-1])
                else:
                    conditions.append(f'{column} LIKE ?')
                    params.append('%' + pattern + '%')
            elif op == '$exists':
                if operand:
                    conditions.append(f'{column} IS NOT NULL')
                else:
                    conditions.append(f'{column} IS NULL')
            else:
                return None, []
        return ' AND '.join(conditions) if conditions else None, params
    else:
        # 단순 값 매칭
        return f'{column} = ?', [value]


@bp.route('/')
@login_required
def directory_list():
    db = get_db()
    # 일반 목록: active=1인 직원만 표시
    profiles = db.execute(
        'SELECT dp.user_id, u.nickname, dp.department, dp.position, dp.email '
        'FROM directory_profiles dp '
        'JOIN users u ON dp.user_id = u.id '
        'WHERE dp.active = 1 '
        'ORDER BY dp.department, u.nickname'
    ).fetchall()
    total_count = db.execute('SELECT COUNT(*) as cnt FROM directory_profiles').fetchone()['cnt']
    return render_template('directory/list.html', profiles=profiles, total_count=total_count)


@bp.route('/search', methods=['POST'])
@login_required
def directory_search():
    """NoSQL-style JSON 검색 API.
    취약점: active 필터 없음 → 퇴직자 접근 가능.
    $regex blind oracle → private_note 추출 가능.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            'error': '검색 조건을 JSON으로 입력하세요.',
            'supported_operators': ['$ne', '$regex', '$gt', '$lt', '$exists'],
            'searchable_fields': sorted(SEARCHABLE_COLUMNS),
            'example': {'department': '보안', 'name': {'$regex': '^김'}}
        }), 400

    where_parts = []
    params = []

    for key, value in data.items():
        if key not in SEARCHABLE_COLUMNS:
            return jsonify({'error': f'알 수 없는 필드: {key}', 'searchable_fields': sorted(SEARCHABLE_COLUMNS)}), 400

        cond, p = _build_condition(key, value)
        if cond is None:
            return jsonify({'error': f'잘못된 연산자: {key}'}), 400
        where_parts.append(cond)
        params.extend(p)

    where_clause = ' AND '.join(where_parts) if where_parts else '1=1'

    # 취약점: active 필터 미적용 — 퇴직자 포함 전체 검색
    query = (
        'SELECT dp.user_id, u.nickname, dp.department, dp.position, dp.email, dp.active '
        'FROM directory_profiles dp '
        'JOIN users u ON dp.user_id = u.id '
        f'WHERE {where_clause} '
        'ORDER BY dp.department, u.nickname'
    )

    try:
        results = get_db().execute(query, params).fetchall()
    except Exception as e:
        return jsonify({'error': f'검색 오류: {str(e)}'}), 500

    # private_note는 응답에 포함하지 않음 (blind extraction만 가능)
    # $regex로 private_note를 검색하면 매칭 결과가 200(있음)/빈배열(없음)으로 구분됨
    return jsonify({
        'count': len(results),
        'total_in_db': get_db().execute('SELECT COUNT(*) as cnt FROM directory_profiles').fetchone()['cnt'],
        'results': [
            {
                'user_id': r['user_id'],
                'nickname': r['nickname'],
                'department': r['department'],
                'position': r['position'],
                'email': r['email'],
                'active': bool(r['active'])
            }
            for r in results
        ]
    })


@bp.route('/<int:user_id>')
@login_required
def directory_profile(user_id):
    db = get_db()
    profile = db.execute(
        'SELECT dp.*, u.nickname '
        'FROM directory_profiles dp '
        'JOIN users u ON dp.user_id = u.id '
        'WHERE dp.user_id = ?',
        (user_id,)
    ).fetchone()

    if profile is None:
        return render_template('directory/list.html', profiles=[], total_count=0,
                               error='프로필을 찾을 수 없습니다.')

    # 퇴직자 프로필은 제한된 정보만 표시 (private_note 미노출)
    if not profile['active']:
        return render_template('directory/profile.html', profile=profile,
                               private_note=None, is_retired=True)

    return render_template('directory/profile.html', profile=profile,
                           private_note=None, is_retired=False)
