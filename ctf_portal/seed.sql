-- 시드 데이터: 문제, 문서
-- 비밀번호 해시/XOR 서명 등 동적 데이터는 init_db.py에서 생성.

-- 문제 정의 (2025-2026 최상급 난이도)
INSERT OR IGNORE INTO challenges (slug, title, description, category, points) VALUES
('employee_directory_leak', '직원 정보 열람', '직원 검색 시스템의 데이터 접근 제어를 점검하세요. 일부 직원 정보가 적절히 보호되지 않을 수 있습니다.', 'HR', 250),
('ticket_ghost', '복구 티켓 검토', '헬프데스크 인증 체계와 티켓 접근 제어를 감사하세요. 권한 검증에 취약점이 있을 수 있습니다.', 'IT', 300),
('archive_smuggler', '문서 보관소 점검', '문서 보관소의 경로 필터링과 접근 제어를 점검하세요. 제한된 영역의 문서에 접근할 수 있는지 확인하세요.', 'IT', 350),
('payroll_race', '정산 시스템 감사', '급여 정산의 다중 승인 프로세스를 검증하세요. 동시 접근 시 예기치 않은 상태가 발생할 수 있습니다.', 'Finance', 400),
('report_relay', '신고 리뷰 파이프라인', '신고 시스템의 Jinja2 렌더링 파이프라인을 점검하세요. 입력 필터링을 우회할 수 있는지 확인하세요.', 'Compliance', 450),
('nonce_museum', '레거시 검증기 감사', '레거시 XOR 서명 시스템의 nonce 관리와 검증 로그를 감사하세요. 서명을 위조할 수 있는지 확인하세요.', 'Security', 500);

-- 문서 보관소 메타데이터
INSERT OR IGNORE INTO documents (filename, display_name, category, is_public) VALUES
('onboarding_guide.txt', '신입사원 온보딩 가이드', 'HR', 1),
('vpn_setup.txt', 'VPN 설정 매뉴얼', 'IT', 1),
('holiday_schedule.txt', '2026년 휴일 일정표', 'General', 1),
('board_minutes.txt', '이사회 회의록', 'Executive', 0);
