"""Challenge 3: Archive Smuggler (350pt)
Path Traversal 필터 우회 (URL 인코딩) → 디렉토리 리스팅 → Cross-file 키 추출
→ XOR 복호화 → 조각 조합 → /assemble 제출.
"""

import os
from urllib.parse import unquote

from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    render_template,
    request,
    abort,
)

from ..auth import login_required
from ..db import get_db
from ..flags import generate_flag

bp = Blueprint("archive", __name__, url_prefix="/archive")


def _xor_bytes(data, key):
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


@bp.route("/")
@login_required
def archive_list():
    db = get_db()
    documents = db.execute(
        "SELECT * FROM documents WHERE is_public = 1 ORDER BY uploaded_at DESC"
    ).fetchall()
    return render_template("archive/list.html", documents=documents)


@bp.route("/download")
@login_required
def archive_download():
    filename = request.args.get("name", "")

    if not filename:
        abort(400)

    if "\x00" in filename:
        abort(400)

    # 필터: raw query string에서 '../' 리터럴 및 URL 인코딩된 variant 차단
    raw_qs = request.query_string.decode("utf-8", errors="replace")
    # URL 디코딩된 형태도 함께 검사 (双重检查)
    decoded_qs = unquote(raw_qs)
    if (
        "../" in raw_qs
        or "../" in decoded_qs
        or "..\\" in raw_qs
        or "..\\" in decoded_qs
    ):
        return jsonify(
            {
                "error": "경로에 허용되지 않는 문자열이 포함되어 있습니다.",
                "blocked": "../",
                "filter": "literal_sequence_check",
            }
        ), 403

    # 경로 정규화 및 범위 검사 강화
    base_path = os.path.abspath(
        os.path.join(current_app.config["STORAGE_PATH"], "public")
    )
    # 사용자 입력 경로 정규화
    requested_path = os.path.normpath(os.path.join(base_path, filename))

    # 반드시 base_path 내에 있어야 함 (Path Traversal 방지)
    if (
        not requested_path.startswith(base_path + os.sep)
        and requested_path != base_path
    ):
        abort(403)

    # 화이트리스트 검사: 공개 파일만 접근 가능
    # 파일명에 위험한 문자가 있는지 추가 검사
    if any(c in filename for c in ["\x00", "\n", "\r"]):
        abort(400)

    # 정규화된 경로 사용
    filepath = requested_path

    # 디렉토리 접근 시 파일 목록 반환
    if os.path.isdir(filepath):
        try:
            entries = os.listdir(filepath)
        except OSError:
            abort(404)
        listing = "\n".join(sorted(entries))
        return Response(
            f"Directory listing: {filename}\n\n{listing}\n", mimetype="text/plain"
        )

    if not os.path.isfile(filepath):
        abort(404)

    # 텍스트 파일: 내용 읽기
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        # 바이너리 파일(.enc 등)은 raw bytes로 반환
        with open(filepath, "rb") as f:
            data = f.read()
        return Response(
            data,
            mimetype="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{os.path.basename(filepath)}"'
            },
        )

    return Response(
        content,
        mimetype="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{os.path.basename(filepath)}"'
        },
    )


@bp.route("/assemble", methods=["POST"])
@login_required
def archive_assemble():
    """조각 조합 검증. 올바른 verification_code + classification → FLAG."""
    verification_code = request.form.get("verification_code", "").strip()
    classification = request.form.get("classification", "").strip()

    if not verification_code or not classification:
        return jsonify(
            {"error": "verification_code와 classification을 모두 입력하세요."}
        ), 400

    # 검증: 조각 조합 결과 + 분류 코드
    if (
        verification_code == "ARCHIVE:VERIFIED:GRANTED"
        and classification == "IC-SEC-2026-A7B3"
    ):
        flag = generate_flag(
            "archive_smuggler", g.user["id"], current_app.config["SECRET_KEY"]
        )
        return jsonify({"success": True, "flag": flag, "message": "문서 검증 통과."})

    return jsonify(
        {"success": False, "message": "검증 코드 또는 분류 코드가 올바르지 않습니다."}
    ), 400
