"""IntraCore DB 초기화 스크립트.
schema.sql → seed.sql 실행 후, 동적 시드 데이터를 삽입.
Ch3 fragment .enc 파일도 생성.
"""
import base64
import hashlib
import os
import sqlite3
import secrets

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'portal.sqlite3')
SCHEMA_PATH = os.path.join(BASE_DIR, 'ctf_portal', 'schema.sql')
SEED_PATH = os.path.join(BASE_DIR, 'ctf_portal', 'seed.sql')
STORAGE_PATH = os.path.join(BASE_DIR, 'seed_storage')


def xor_bytes(data, key):
    """XOR data with repeating key."""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    with open(SEED_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # === NPC 사용자 (참가자는 /register로 생성) ===
    users = [
        ('admin', secrets.token_hex(16), '관리자', 'admin'),        # id=1
        ('k.boan', secrets.token_hex(16), '김보안', 'employee'),    # id=2
        ('j.finance', secrets.token_hex(16), '정재무', 'finance'),  # id=3
        ('l.infra', secrets.token_hex(16), '이인프라', 'employee'), # id=4
        ('s.legacy', secrets.token_hex(16), '송레거시', 'retired'), # id=5 (퇴직자)
    ]
    for username, pw, nickname, role in users:
        conn.execute(
            'INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(pw), nickname, role)
        )
    conn.commit()

    # === NPC 직원 프로필 ===
    # Ch1: id=5 송레거시 (active=0, private_note에 Base64(FLAG 플레이스홀더))
    # 실제 FLAG는 동적 생성이므로 private_note에 고정 마커를 Base64로 저장
    # blind extraction 대상 문자열: "FLAG_MARKER:employee_directory_leak"을 Base64 인코딩
    flag_marker = base64.b64encode(b'FLAG_MARKER:employee_directory_leak').decode()
    profiles = [
        (1, '경영지원팀', '팀장', 'admin@intracore.local', '010-0000-0001',
         '시스템 관리 총괄', '관리자 접근 전용 메모', 1),
        (2, '보안운영팀', '선임', 'k.boan@intracore.local', '010-0000-0002',
         '보안 감사 및 모의해킹 담당', '보안 감사 내부 메모', 1),
        (3, '재무팀', '과장', 'j.finance@intracore.local', '010-0000-0003',
         '분기별 정산 관리', '분기 정산 일정 메모', 1),
        (4, '인프라팀', '대리', 'l.infra@intracore.local', '010-0000-0004',
         '서버 및 네트워크 관리', '서버실 출입 코드: 내부용', 1),
        (5, '보안운영팀', '전 선임연구원', 's.legacy@intracore.local', '010-0000-0005',
         '2025년 퇴직. 보안 감사 프로젝트 리드 담당.',
         flag_marker, 0),  # active=0 (퇴직자)
    ]
    for uid, dept, pos, email, phone, bio, note, active in profiles:
        conn.execute(
            'INSERT OR IGNORE INTO directory_profiles '
            '(user_id, department, position, email, phone, bio, private_note, active) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (uid, dept, pos, email, phone, bio, note, active)
        )
    conn.commit()

    # === 티켓 시드 ===
    tickets = [
        ('VPN 접속 오류', 'VPN 클라이언트가 내부 네트워크에 연결되지 않습니다.',
         'open', 4, None),
        ('서버 복구 완료', '2026-03-15 새벽에 발생한 DB 서버 장애 복구 완료.',
         'closed', 1, '복구 작업 완료. 백업 키: {{FLAG}} -- 외부 노출 금지'),
        ('프린터 장애', '3층 복합기 용지 걸림 반복. 점검 요청.',
         'open', 4, None),
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
        (3, 3500000, 'pending', '2026년 3월 급여 정산')
    )
    conn.commit()

    # === XOR 검증 샘플 (Ch6) ===
    # 공개 샘플: nonce_group=1
    nonce1 = bytes.fromhex('a3b1c2d4e5f60718')
    public_samples = [
        ('Sample-A', 'hello:world:test'),
        ('Sample-B', 'check:status:ok'),
    ]
    for label, message in public_samples:
        sig = xor_bytes(message.encode(), nonce1)
        conn.execute(
            'INSERT OR IGNORE INTO verification_samples '
            '(label, message, nonce, signature, is_public, nonce_group) '
            'VALUES (?, ?, ?, ?, 1, 1)',
            (label, message, nonce1.hex(), sig.hex())
        )

    # 비공개 샘플: nonce_group=2 (다른 nonce)
    nonce2 = bytes.fromhex('f1e2d3c4b5a69078')
    private_samples = [
        ('Internal-X', 'internal:audit:pass'),
        ('Internal-Y', 'system:health:ok'),
    ]
    for label, message in private_samples:
        sig = xor_bytes(message.encode(), nonce2)
        conn.execute(
            'INSERT OR IGNORE INTO verification_samples '
            '(label, message, nonce, signature, is_public, nonce_group) '
            'VALUES (?, ?, ?, ?, 0, 2)',
            (label, message, nonce2.hex(), sig.hex())
        )

    # 검증 로그 시드 (Ch6 SQLi 대상)
    for s in public_samples + private_samples:
        sample = conn.execute(
            'SELECT id FROM verification_samples WHERE label = ?', (s[0],)
        ).fetchone()
        if sample:
            conn.execute(
                'INSERT INTO verification_logs (sample_id, action, performed_at) VALUES (?, ?, ?)',
                (sample['id'], 'created', '2026-01-15 09:00:00')
            )
    conn.commit()

    # === Ch3: Fragment .enc 파일 생성 ===
    xor_key = b'IC-SEC-2026-A7B3'
    fragments = [b'ARCHIVE', b':VERIFIED', b':GRANTED']
    frag_dir = os.path.join(STORAGE_PATH, 'private', 'fragments')
    os.makedirs(frag_dir, exist_ok=True)

    for i, frag in enumerate(fragments, 1):
        encrypted = xor_bytes(frag, xor_key)
        frag_path = os.path.join(frag_dir, f'frag_{i:02d}.enc')
        with open(frag_path, 'wb') as f:
            f.write(encrypted)

    # board_minutes.txt 수정 (분류 코드 포함, {{FLAG}} 제거)
    board_path = os.path.join(STORAGE_PATH, 'private', 'board_minutes.txt')
    with open(board_path, 'w', encoding='utf-8') as f:
        f.write("""============================================
  IntraCore 2026년 1분기 이사회 회의록
  일시: 2026-03-28 14:00
  장소: 본사 10층 이사회실
============================================

[안건 1] 2025년 4분기 실적 보고
- 매출 전년 대비 12% 증가

[안건 2] 보안 감사 결과
- 외부 감사 결과 내부 시스템 접근 제어 미흡 발견
- 기밀 문서 조각은 fragments/ 하위에 분산 보관됨
- 문서 분류 코드: IC-SEC-2026-A7B3
- 3분기까지 개선 조치 완료 목표

[결의] 전 안건 만장일치 승인

============================================
  이 문서는 기밀 등급이며 무단 유출을 금지합니다.
============================================
""")

    # onboarding_guide.txt에 보관소 구조 힌트 추가
    onboard_path = os.path.join(STORAGE_PATH, 'public', 'onboarding_guide.txt')
    with open(onboard_path, 'w', encoding='utf-8') as f:
        f.write("""============================================
  IntraCore 신입사원 온보딩 가이드
  Version 2.1 | 2026-01-15
============================================

1. 사내 시스템 접속
   - IntraCore Portal에 발급받은 계정으로 로그인합니다.

2. VPN 설정
   - VPN 설정 매뉴얼을 참고하여 원격 접속을 설정합니다.

3. 보안 수칙
   - 사내 문서를 외부에 유출하지 않습니다.
   - 비밀번호는 90일마다 변경합니다.

4. 문서 보관소
   - 보관소는 public/(공개)과 private/(제한) 영역으로 구분됩니다.
   - 제한 영역의 문서는 관리자 승인이 필요합니다.
   - 문의: 보안운영팀 (security@intracore.local)

5. 주요 연락처
   - 인사팀: hr@intracore.local
   - 인프라팀: infra@intracore.local
   - 보안운영팀: security@intracore.local
""")

    conn.close()
    print('[+] 데이터베이스 초기화 완료:', DB_PATH)
    print('[+] Fragment 파일 생성 완료:', frag_dir)
    print(f'[+] Ch1 blind target: {flag_marker}')
    print('[+] 참가자는 /register 에서 회원가입 후 이용 가능')


if __name__ == '__main__':
    init()
