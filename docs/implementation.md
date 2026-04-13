# 구현 명세

## 애플리케이션 구조

- 엔트리포인트: `app.py`
- 앱 패키지: `ctf_portal`
- 템플릿: `ctf_portal/templates`
- 정적 파일: `static`
- 저장소 파일: `seed_storage`
- SQLite DB: `instance/portal.sqlite3`

## 주요 라우트

- `/login`
- `/dashboard`
- `/leaderboard`
- `/directory`
- `/directory/<user_id>`
- `/tickets`
- `/tickets/<ticket_id>`
- `/archive`
- `/archive/download`
- `/finance`
- `/reports`
- `/reports/<report_id>/preview`
- `/verify`
- `/submit-flag`

## 점수 및 랭킹

- 점수는 해결한 문제 점수의 합계입니다.
- 랭킹은 전체 사용자 기준으로 계산합니다.
- 동점이면 더 먼저 푼 사용자가 상위입니다.
- `/dashboard`에서는 닉네임, 역할, 현재 점수, 현재 랭킹을 표시합니다.

## 데이터 엔터티

- `users`
- `challenges`
- `solved_challenges`
- `directory_profiles`
- `tickets`
- `documents`
- `payroll_requests`
- `reports`
- `verification_samples`
