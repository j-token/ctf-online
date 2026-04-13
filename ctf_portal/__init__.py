import os

from flask import Flask, redirect, url_for

from .auth import get_current_user


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder='../static'
    )

    # Railway: PORT 환경변수 사용, SECRET_KEY 환경변수 우선
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'intracore-ctf-secret-key-2026'),
        DATABASE=os.path.join(app.instance_path, 'portal.sqlite3'),
        STORAGE_PATH=os.path.join(os.path.dirname(app.root_path), 'seed_storage'),
    )

    if test_config:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from .db import init_app
    init_app(app)

    # Railway: DB 파일이 없으면 자동 초기화
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        with app.app_context():
            _auto_init_db(app)

    @app.before_request
    def load_user():
        get_current_user()

    from .blueprints import (
        auth_bp, dashboard_bp, leaderboard_bp, directory_bp,
        tickets_bp, archive_bp, finance_bp, reports_bp,
        verify_bp, flag_bp
    )
    app.register_blueprint(auth_bp.bp)
    app.register_blueprint(dashboard_bp.bp)
    app.register_blueprint(leaderboard_bp.bp)
    app.register_blueprint(directory_bp.bp)
    app.register_blueprint(tickets_bp.bp)
    app.register_blueprint(archive_bp.bp)
    app.register_blueprint(finance_bp.bp)
    app.register_blueprint(reports_bp.bp)
    app.register_blueprint(verify_bp.bp)
    app.register_blueprint(flag_bp.bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app


def _auto_init_db(app):
    """DB가 없을 때 자동으로 init_db.py 로직을 실행."""
    import base64
    import hashlib
    import secrets
    import sqlite3

    from werkzeug.security import generate_password_hash

    db_path = app.config['DATABASE']
    storage_path = app.config['STORAGE_PATH']
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    seed_path = os.path.join(os.path.dirname(__file__), 'seed.sql')

    def xor_bytes(data, key):
        return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    with open(seed_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # NPC 사용자
    users = [
        ('admin', secrets.token_hex(16), '관리자', 'admin'),
        ('k.boan', secrets.token_hex(16), '김보안', 'employee'),
        ('j.finance', secrets.token_hex(16), '정재무', 'finance'),
        ('l.infra', secrets.token_hex(16), '이인프라', 'employee'),
        ('s.legacy', secrets.token_hex(16), '송레거시', 'retired'),
    ]
    for username, pw, nickname, role in users:
        conn.execute(
            'INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(pw), nickname, role)
        )
    conn.commit()

    # 직원 프로필
    flag_marker = base64.b64encode(b'FLAG_MARKER:employee_directory_leak').decode()
    profiles = [
        (1, '경영지원팀', '팀장', 'admin@intracore.local', '010-0000-0001', '시스템 관리 총괄', '관리자 접근 전용 메모', 1),
        (2, '보안운영팀', '선임', 'k.boan@intracore.local', '010-0000-0002', '보안 감사 및 모의해킹 담당', '보안 감사 내부 메모', 1),
        (3, '재무팀', '과장', 'j.finance@intracore.local', '010-0000-0003', '분기별 정산 관리', '분기 정산 일정 메모', 1),
        (4, '인프라팀', '대리', 'l.infra@intracore.local', '010-0000-0004', '서버 및 네트워크 관리', '서버실 출입 코드: 내부용', 1),
        (5, '보안운영팀', '전 선임연구원', 's.legacy@intracore.local', '010-0000-0005', '2025년 퇴직.', flag_marker, 0),
    ]
    for uid, dept, pos, email, phone, bio, note, active in profiles:
        conn.execute(
            'INSERT OR IGNORE INTO directory_profiles (user_id, department, position, email, phone, bio, private_note, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (uid, dept, pos, email, phone, bio, note, active)
        )
    conn.commit()

    # 티켓
    tickets = [
        ('VPN 접속 오류', 'VPN 클라이언트가 내부 네트워크에 연결되지 않습니다.', 'open', 4, None),
        ('서버 복구 완료', '2026-03-15 새벽에 발생한 DB 서버 장애 복구 완료.', 'closed', 1, '복구 작업 완료. 백업 키: {{FLAG}} -- 외부 노출 금지'),
        ('프린터 장애', '3층 복합기 용지 걸림 반복.', 'open', 4, None),
    ]
    for title, desc, status, created_by, memo in tickets:
        conn.execute('INSERT OR IGNORE INTO tickets (title, description, status, created_by, internal_memo) VALUES (?, ?, ?, ?, ?)', (title, desc, status, created_by, memo))
    conn.commit()

    # 급여 정산
    conn.execute('INSERT OR IGNORE INTO payroll_requests (employee_id, amount, status, memo) VALUES (?, ?, ?, ?)', (3, 3500000, 'pending', '2026년 3월 급여 정산'))
    conn.commit()

    # XOR 검증 샘플
    nonce1 = bytes.fromhex('a3b1c2d4e5f60718')
    for label, message in [('Sample-A', 'hello:world:test'), ('Sample-B', 'check:status:ok')]:
        sig = xor_bytes(message.encode(), nonce1)
        conn.execute('INSERT OR IGNORE INTO verification_samples (label, message, nonce, signature, is_public, nonce_group) VALUES (?, ?, ?, ?, 1, 1)', (label, message, nonce1.hex(), sig.hex()))

    nonce2 = bytes.fromhex('f1e2d3c4b5a69078')
    for label, message in [('Internal-X', 'internal:audit:pass'), ('Internal-Y', 'system:health:ok')]:
        sig = xor_bytes(message.encode(), nonce2)
        conn.execute('INSERT OR IGNORE INTO verification_samples (label, message, nonce, signature, is_public, nonce_group) VALUES (?, ?, ?, ?, 0, 2)', (label, message, nonce2.hex(), sig.hex()))

    for lbl in ['Sample-A', 'Sample-B', 'Internal-X', 'Internal-Y']:
        s = conn.execute('SELECT id FROM verification_samples WHERE label = ?', (lbl,)).fetchone()
        if s:
            conn.execute('INSERT INTO verification_logs (sample_id, action, performed_at) VALUES (?, ?, ?)', (s['id'], 'created', '2026-01-15 09:00:00'))
    conn.commit()

    # Ch3 Fragment 파일 생성
    xor_key = b'IC-SEC-2026-A7B3'
    frag_dir = os.path.join(storage_path, 'private', 'fragments')
    os.makedirs(frag_dir, exist_ok=True)
    for i, frag in enumerate([b'ARCHIVE', b':VERIFIED', b':GRANTED'], 1):
        with open(os.path.join(frag_dir, f'frag_{i:02d}.enc'), 'wb') as f:
            f.write(xor_bytes(frag, xor_key))

    conn.close()
    print('[+] Railway auto-init: DB initialized')
