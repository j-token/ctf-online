"""Challenge 3: Archive Smuggler (Path Traversal)
다운로드 경로 검증이 약해 상대 경로 우회가 가능함.
"""
import os

from flask import Blueprint, Response, current_app, g, render_template, request, abort

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint('archive', __name__, url_prefix='/archive')


@bp.route('/')
@login_required
def archive_list():
    db = get_db()
    documents = db.execute(
        'SELECT * FROM documents WHERE is_public = 1 ORDER BY uploaded_at DESC'
    ).fetchall()
    return render_template('archive/list.html', documents=documents)


@bp.route('/download')
@login_required
def archive_download():
    filename = request.args.get('name', '')

    if not filename:
        abort(400)

    # 취약점: null byte만 차단, realpath 검증 생략 → path traversal 가능
    if '\x00' in filename:
        abort(400)

    base_path = os.path.join(current_app.config['STORAGE_PATH'], 'public')
    filepath = os.path.join(base_path, filename)

    # 디렉토리 접근 시 파일 목록 반환 (취약점: 디렉토리 리스팅)
    if os.path.isdir(filepath):
        files = os.listdir(filepath)
        listing = '\n'.join(files)
        return Response(
            f'Directory listing: {filename}\n\n{listing}\n',
            mimetype='text/plain'
        )

    if not os.path.isfile(filepath):
        abort(404)

    # 파일 내용을 읽어서 {{FLAG}} 플레이스홀더를 동적 치환
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        # 바이너리 파일은 그대로 전송
        from flask import send_file
        return send_file(filepath, as_attachment=True)

    if '{{FLAG}}' in content:
        flag = generate_flag('archive_smuggler', g.user['id'], current_app.config['SECRET_KEY'])
        content = content.replace('{{FLAG}}', flag)

    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{os.path.basename(filepath)}"'}
    )
