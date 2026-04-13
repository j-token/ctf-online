-- 시드 데이터: 사용자, 문제, 직원 프로필, 티켓, 문서, 급여 정산
-- 비밀번호 해시는 init_db.py에서 동적 생성. 여기서는 문제/문서/기타 시드만 삽입.

-- 문제 정의 (flag 컬럼 없음 — 동적 생성)
INSERT OR IGNORE INTO challenges (slug, title, description, category, points) VALUES
('employee_directory_leak', '직원 정보 열람', '직원 디렉토리에서 비공개 정보를 확인하세요.', 'HR', 100),
('ticket_ghost', '복구 티켓 검토', '헬프데스크에서 숨겨진 복구 기록을 찾으세요.', 'IT', 150),
('archive_smuggler', '문서 보관소 점검', '문서 보관소의 접근 제어를 점검하세요.', 'IT', 200),
('payroll_race', '정산 시스템 감사', '급여 정산 프로세스의 정합성을 검증하세요.', 'Finance', 250),
('report_relay', '신고 리뷰 파이프라인', '신고 시스템의 렌더링 파이프라인을 점검하세요.', 'Compliance', 300),
('nonce_museum', '레거시 검증기 감사', '레거시 서명 검증 시스템의 보안을 감사하세요.', 'Security', 350);

-- 문서 보관소 메타데이터
INSERT OR IGNORE INTO documents (filename, display_name, category, is_public) VALUES
('onboarding_guide.txt', '신입사원 온보딩 가이드', 'HR', 1),
('vpn_setup.txt', 'VPN 설정 매뉴얼', 'IT', 1),
('holiday_schedule.txt', '2026년 휴일 일정표', 'General', 1),
('board_minutes.txt', '이사회 회의록', 'Executive', 0);
