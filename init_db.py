"""IntraCore DB 초기화 스크립트.
schema.sql → seed.sql 실행 후, 비밀번호 해시/XOR 서명 등 동적 시드 데이터를 삽입.
"""
import os
import sqlite3
import secrets

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'portal.sqlite3')
SCHEMA_PATH = os.path.join(BASE_DIR, 'ctf_portal', 'schema.sql')
SEED_PATH = os.path.join(BASE_DIR, 'ctf_portal', 'seed.sql')


def xor_sign(message_bytes, nonce_bytes):
    sig = bytearray(len(message_bytes))
    for i in range(len(message_bytes)):
        sig[i] = message_bytes[i] ^ nonce_bytes[i % len(nonce_bytes)]
    return bytes(sig)


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 기존 DB 삭제 후 재생성
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 스키마 적용
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # 시드 SQL 실행
    with open(SEED_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # === NPC 사용자 시드 (참가자는 회원가입으로 생성) ===
    users = [
        ('admin', secrets.token_hex(16), '관리자', 'admin'),        # id=1
        ('k.boan', secrets.token_hex(16), '김보안', 'employee'),    # id=2
        ('j.finance', secrets.token_hex(16), '정재무', 'finance'),  # id=3
        ('l.infra', secrets.token_hex(16), '이인프라', 'employee'), # id=4
    ]
    for username, pw, nickname, role in users:
        conn.execute(
            'INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(pw), nickname, role)
        )
    conn.commit()

    # === NPC 직원 프로필 시드 (ID는 위 사용자 삽입 순서 기준) ===
    profiles = [
        (1, '경영지원팀', '팀장', 'admin@intracore.local', '010-0000-0001',
         '시스템 관리 총괄', '관리자 접근 전용 메모'),
        (2, '보안운영팀', '선임', 'k.boan@intracore.local', '010-0000-0002',
         '보안 감사 및 모의해킹 담당',
         '보안 감사 결과 [CLASSIFIED] {{FLAG}} -- 외부 유출 시 징계 대상'),
        (3, '재무팀', '과장', 'j.finance@intracore.local', '010-0000-0003',
         '분기별 정산 관리', '분기 정산 일정 메모'),
        (4, '인프라팀', '대리', 'l.infra@intracore.local', '010-0000-0004',
         '서버 및 네트워크 관리', '서버실 출입 코드: 내부용'),
    ]
    for uid, dept, pos, email, phone, bio, note in profiles:
        conn.execute(
            'INSERT OR IGNORE INTO directory_profiles '
            '(user_id, department, position, email, phone, bio, private_note) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (uid, dept, pos, email, phone, bio, note)
        )
    conn.commit()

    # === 티켓 시드 ===
    tickets = [
        ('VPN 접속 오류', 'VPN 클라이언트가 내부 네트워크에 연결되지 않습니다. 방화벽 규칙 확인 요청드립니다.',
         'open', 4, None),                    # created_by=4 (이인프라)
        ('서버 복구 완료', '2026-03-15 새벽에 발생한 DB 서버 장애에 대한 복구 작업을 완료했습니다.',
         'closed', 1, '복구 작업 완료. 백업 키: {{FLAG}} -- 외부 노출 금지'),  # created_by=1 (관리자)
        ('프린터 장애', '3층 복합기 용지 걸림이 반복 발생합니다. 점검 요청합니다.',
         'open', 4, None),                    # created_by=4 (이인프라)
    ]
    for title, desc, status, created_by, memo in tickets:
        conn.execute(
            'INSERT OR IGNORE INTO tickets (title, description, status, created_by, internal_memo) '
            'VALUES (?, ?, ?, ?, ?)',
            (title, desc, status, created_by, memo)
        )
    conn.commit()

    # === 급여 정산 요청 시드 ===
    conn.execute(
        'INSERT OR IGNORE INTO payroll_requests (employee_id, amount, status, memo) '
        'VALUES (?, ?, ?, ?)',
        (3, 3500000, 'pending', '2026년 3월 급여 정산')  # employee_id=3 (정재무)
    )
    conn.commit()

    # === XOR 검증 샘플 시드 (Challenge 6) ===
    # 동일 nonce를 재사용하는 것이 핵심 취약점
    nonce = bytes.fromhex('a3b1c2d4e5f60718')

    sample_messages = [
        ('Sample-A', 'hello:world:test'),
        ('Sample-B', 'check:status:ok'),
    ]

    for label, message in sample_messages:
        msg_bytes = message.encode('utf-8')
        sig = xor_sign(msg_bytes, nonce)
        conn.execute(
            'INSERT OR IGNORE INTO verification_samples (label, message, nonce, signature, is_public) '
            'VALUES (?, ?, ?, ?, 1)',
            (label, message, nonce.hex(), sig.hex())
        )
    conn.commit()

    conn.close()
    print('[+] 데이터베이스 초기화 완료:', DB_PATH)
    print('[+] 참가자는 /register 에서 회원가입 후 이용 가능')


if __name__ == '__main__':
    init()
