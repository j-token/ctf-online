import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "intracore-ctf-secret-key-2026")
    # DB 경로: instance 폴더 내에 위치하되, 웹 서버에서 .sqlite3 접근 차단 필요
    # 프로덕션: 웹 루트 외부 경로 권장 (예: /var/lib/intracore/)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INSTANCE_PATH = os.path.join(BASE_DIR, "instance")
    DATABASE = os.path.join(INSTANCE_PATH, "portal.sqlite3")
    STORAGE_PATH = os.path.join(BASE_DIR, "seed_storage")

    # 보안 설정
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB 파일 업로드 제한
