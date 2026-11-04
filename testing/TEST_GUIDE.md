# ASG 정책 게이트웨이 테스트 설명서

2026-11-03. 실제 실행 결과는 이 파일 하단에 자동 삽입합니다. 기본 로컬 SQLite·HTTP·독립 실행파일 검사와 실제 PostgreSQL 검사를 구분합니다.

## 1. 환경 준비

프로젝트 폴더에서 PowerShell을 열고 다음 순서로 실행합니다. 기본 실행파일과 로컬 테스트는 가상 SQLite 데이터이며 기업 DB를 사용하지 않습니다.

```powershell
.\testing\setup.ps1
.\scripts\build_exe.ps1
.\testing\run_tests.ps1
```

setup은 Python 가상 환경과 고정한 의존성을 준비하고, build는 현재 소스로 ASG.exe를 교체하며, run_tests는 회귀→실제 HTTP→분리된 실행파일 순서로 검사합니다. 예상 결과는 마지막 PASS와 32단계 PASS입니다. 실행파일을 켠 상태라 교체가 실패하면 해당 ASG 창을 종료하고 build만 다시 실행하세요. Python 명령이 Microsoft Store 안내를 띄우면 위 도구가 만든 `.venv\Scripts\python.exe`를 직접 사용합니다.

## 2. 정책 기능별 예상 결과

| 절차 | 예상 결과 |
|---|---|
| 운영 기본 열 25행 요청 | 200 자동 허용, 사람 승인 없이 원래 에이전트가 execute 가능 |
| description 등 자동 허용 밖의 유효 열 요청 | 202 승인 대기, 실행 전 409 |
| 미등록 열·다른 테넌트 요청 | 403 차단, 사람 승인으로 덮어쓰기 불가 |
| 검토자의 일회 승인 | 승인 후 요청 범위만 실행 |
| 검토자의 반복 승인 | 기간·횟수·총량 안의 동일 범위만 재사용 |
| 목적·필터·열·신원 변경 | 기존 반복 승인 적용 불가 |
| 반복 승인 취소·만료·소진 | 이후 새 실행과 취소된 승인으로 캐시 재조회 거부 |
| 작은 조회 반복 | 누적 반환·예약량 초과 시 429, 쿼리 실행하지 않음 |
| 응답 유실·실행 결과 불명 | 최대 요청량 예약 유지, 같은 실행 재시도는 이중 차감하지 않음 |
| 승인 만료 뒤 실행 영수증 대조 | 새 SQL 없이 실제 반환량 정산, 검토자에게 행 본문 미반환 |
| 독립 PostgreSQL 연결의 동시 실행 | 전체·범위 승인 한도 초과 불가 |
| 날짜별 감사·위험도 | 자동 허용·검토·차단·발급·취소·조회 이력 보존 |

## 3. 실제 PostgreSQL 재현

Docker Desktop을 시작하고 프로젝트 루트에서 실행합니다. `testing/postgresql_checks.py` 파일을 직접 실행하는 대신 `-m` 형식으로 실행해야 프로젝트 모듈을 찾습니다.

```powershell
.\.venv\Scripts\python.exe -m testing.postgresql_checks --policy-controls
```

임시 전용 DB의 정상·공격·쓰기·권한·예약·다중 연결 경쟁을 검증하며 테스트 후 자신이 만든 컨테이너만 정리합니다. 예상 결과는 **21단계 PASS**이고 결과는 `testing/results/postgresql/`입니다. Docker 연결 실패라면 Desktop의 엔진 준비를 기다리고 같은 명령을 다시 실행합니다. 실패를 성공 결과로 덮어 표시하지 말고 보고서의 실행 오류를 먼저 확인합니다.

보존형 가상 DB는 [별도 설명서](VALIDATION_DB_GUIDE.md)를 따릅니다. 기존 DB의 004 마이그레이션과 기존 서버 종료가 필요합니다. 자동 허용과 예외 시연을 구분하며 과거 모델 시험 수치를 현재 결과로 사용하지 않습니다.

## 4. 새 통제만 순서대로 검증하기

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_db_policy_controls -v
```

이 검사는 SQLite와 모의 도구 영수증을 사용합니다. 실제 PostgreSQL이라는 증거는 앞 절의 독립 연결 시험입니다. `test_...` 이름별 결과가 출력되며 현재 22개 통제 테스트의 예상 결과는 모두 ok입니다.

| 순서 | 검증 내용 | 확인할 예상 결과 |
|---:|---|---|
| 1 | 기본 열 자동 정책 | 사람 없이 ALLOW·APPROVED, execute 성공 |
| 2 | 낮은 점수의 description 요청 | 자동 허용되지 않고 PENDING_APPROVAL |
| 3 | 자동 정책 없음·가득 찬 검토 대기열 | 정책 없음은 검토, 가득 찬 사람 대기열과 자동 허용은 분리. 자동 요청도 사람 대기열을 소모하지 않음 |
| 4 | 정책 위반·새 이상 징후 | 위반은 승인 불가, 빈도 경고는 사람 검토 |
| 5 | 요청 만료·변조·역할 변경 | 새 실행과 역할 변경 후 캐시 재조회 거부 |
| 6 | 반복 승인 발급·원래 요청 실행·같은 범위 재사용 | 원래 요청 포함 2회·300행 정산 |
| 7 | 목적·열·필터·최대량 변경 | 기존 승인을 확대 적용하지 않음 |
| 8 | 취소·만료·정책 변경·권한 없는 관리 | 실행/관리 거부, 실패한 발급은 결정까지 롤백 |
| 9 | 100행 조회 두 번, 누적 예산 150행 | 첫 실행만 성공, 두 번째 429, 실제 도구 호출 1번 |
| 10 | 100행 요청에서 실제 20행·재조회 | 총 사용 1회·20행, 이중 차감 없음 |
| 11 | 응답 유실 후 30분 경과 | 예약 100행 유지, 새 요청으로 우회 불가 |
| 12 | 완료 기록의 창 만료 | 미확정과 달리 완료분은 창에서 빠짐 |
| 13 | 10개 병렬 조회에 예산 300행 | 3건만 성공, 7건 429 |
| 14 | 범위 승인 마지막 슬롯 | 같은 승인을 두 번 소모하지 못함. 실제 경쟁은 PostgreSQL 보고서 확인 |
| 15 | 승인 만료 후 저장 영수증 대조 | 새 SQL 없이 정산, 검토자에게 행 본문 미반환 |

PostgreSQL 추가 7단계는 자동 실제 SELECT, 두 연결의 전체 예산 경쟁, 범위 승인 마지막 슬롯 경쟁, 다른 연결에서의 취소 반영, 유실 응답 대조, 자동 요청 40건(동시성 8), 다중 연결 감사 체인을 검사합니다. 경쟁 시험의 예상 HTTP는 각각 200 하나와 429 하나입니다. 단위 테스트 통과를 이 실제 경쟁 시험의 대체로 보지 않습니다.

## 5. 화면에서 사람의 판단과 반복 승인을 체험하기

1. `ASG.exe`를 실행하고 왼쪽 작동 테스트에서 일반·민감·대량·비정상 가상 요청을 만듭니다. 일반은 자동 허용, 민감·대량은 검토 대기, 비정상은 차단이어야 합니다.
2. 승인 검토에서 최신순·오래된순·위험순을 바꿉니다. 자동 허용된 일반 요청은 대기 목록에 없어야 합니다.
3. 민감 요청을 열어 시각·IP·주체·목적·열·최대 행 수와 보안 에이전트의 분석·추천을 읽습니다. 판단 근거 없이 결정하면 저장되지 않아야 합니다.
4. 반복 업무 승인을 선택하고 10분·20회·2,000행, 근거를 입력합니다. 원래 요청의 최대 행 수와 동일 범위 조건을 확인하고 승인합니다.
5. 같은 시나리오를 다시 생성합니다. 목적·열·필터·신원이 동일하고 새 이상 징후가 없으면 범위 승인으로 허용됩니다. 다른 목적이면 새 검토입니다.
6. 실제 행 반환·차감은 에이전트의 execute가 필요합니다. 아래 PostgreSQL 수동 절차 또는 자동 통합 검사를 사용합니다. ‘허용’만 보이는 상태를 ‘조회 완료’로 판단하지 마세요.
7. 승인 검토 하단에서 사용량을 보고 취소를 펼쳐 이유를 입력합니다. 상태가 취소로 바뀌고 기존 사용 기록은 남아야 합니다.
8. 감사 기록에서 오늘 날짜·상세 보고서를 열어 발급·자동 허용·취소·실행 기록을 확인합니다. 작동 테스트의 원클릭 점검은 연결과 분석 상태를 검사하며 요청을 승인하지 않습니다.

실제 PostgreSQL에 대해 같은 체험을 하려면 [검증 DB 설명서](VALIDATION_DB_GUIDE.md)의 토큰 생성·별도 에이전트 실행 절차를 따릅니다. 기본 클라이언트는 자동 허용이므로 사람 검토를 보려면 `--columns ticket_id description`을 지정합니다. 클라이언트 실행을 반복할 때 목적·열을 동일하게 유지해야 반복 승인이 적용됩니다.

## 6. 기존 가상 DB를 지우지 않고 재검증하기

```powershell
.\.venv\Scripts\python.exe -m testing.postgresql_checks --keep-db --reuse --policy-controls
```

이미 만들어 둔 전용 검증 DB에만 사용합니다. 같은 DB의 검증 대시보드 콘솔을 먼저 종료하세요. 소유권·컨테이너 라벨·볼륨·루프백 주소를 확인하고, 필요한 004 마이그레이션을 적용하며 재시드하지 않습니다. 기본 25단계와 추가 정책 7단계, 총 **32단계 PASS**가 예상됩니다. 운영 이력 2,400·연락처 200·급여 100행과 기존 감사 기록이 DB 재시작 후 유지되어야 합니다.

단시간 반복 실행으로 빈도·누적 한도가 작동하면 해당 증거와 이전 예약을 조사하고 정책 창을 기다립니다. DB를 삭제해 제한을 피하는 방식으로 시험하지 않습니다. 미확정 예약은 창이 지나도 자동 해제되지 않습니다.

## 7. 결과 읽기와 범위

이 파일 하단은 32단계의 예상값·실제 응답·PASS/FAIL을 자동 삽입한 보고서입니다. PostgreSQL의 실제 관찰값은 별도 두 보고서와 검증 DB 설명서 하단에 있습니다. 최신 회귀 수는 하단 T01을 기준으로 확인합니다. 화면 검토 증거는 [POLICY_UI_REVIEW.md](POLICY_UI_REVIEW.md)에 분리했습니다.

단위 테스트의 통과는 생산 처리량이나 모든 네트워크 경계를 증명하지 않습니다. PostgreSQL 보고서에는 실제 독립 연결 수·요청 수·동시성·관찰 시간을 기록합니다. 미확정 예약을 임의로 환급하거나 승인 대기 시간 초과를 자동 허용으로 처리하지 않습니다.

<!-- ASG_RESULT_BEGIN -->

## 11. 실제 테스트 결과보고서

- 실행 ID: `20261104-153859-9fe3b8f3`
- 기준 커밋: `8a52afb4a2e0f31a19a967d4a3413e7dd45fedcc` / 미커밋 수정: True
- 실행 소스 SHA-256: `b3bff0e4e71dc4f72eee61b64647b8d99f73eb7fc003196792bf3da8df4a0506`
- 실행: 2026-11-04 15:38:59 ~ 15:40:00 (Asia/Seoul)
- 전체 판정: **PASS**
- Python: 3.12.14 / win32
- 로컬 HTTP·SQLite·모의 전송함을 사용했습니다. 실제 외부 발송은 없습니다.

| ID | 테스트 | 결과 |
|---|---|---|
| T01 | 기존·추가 회귀 테스트 | PASS |
| T02 | 3개 서비스 준비 확인 | PASS |
| T03 | 배정 문서 읽기 | PASS |
| T04 | 테넌트 경계와 부작용 | PASS |
| T05 | 프롬프트 인젝션 | PASS |
| T06 | 유니코드 은닉 | PASS |
| T07 | 정상 입력 검사 | PASS |
| T08 | 실제 산출물 생성과 승인 대기 | PASS |
| T09 | 승인 전 실행 차단 | PASS |
| T10 | 검토자 승인 | PASS |
| T11 | 승인 후 실행·재실행 중복 방지 | PASS |
| T12 | 감사 해시 연결 | PASS |
| T13 | 다른 사이트에서 테스트 실행 차단 | PASS |
| T14 | 도구 직접 접근 인증 | PASS |
| T15 | 대시보드 감사 연결 | PASS |
| T16 | DB 접근 요청·보안 에이전트 분석 | PASS |
| T17 | 사람 승인 전 DB 조회 차단 | PASS |
| T18 | 판단 근거를 포함한 사람 승인 | PASS |
| T19 | 승인 후 실제 SQL 조회·영수증 재사용 | PASS |
| T20 | DB 분석 시나리오 sensitive | PASS |
| T21 | DB 분석 시나리오 bulk | PASS |
| T22 | DB 분석 시나리오 abnormal | PASS |
| T23 | 30분 위험도 증가·감쇠·소멸 | PASS |
| T24 | 현재 위험도·일일 처리 집계 | PASS |
| T25 | 언제·어디서·누가·무엇·결과의 보고서 | PASS |
| T26 | 원클릭 실제 작동 점검 | PASS |
| T27 | 동시 대시보드 조회 인증 안정성 | PASS |
| T28 | 정상 종료 시 포트 반환 | PASS |
| T29 | 독립 EXE 기동과 6개 시나리오 | PASS |
| T30 | 독립 EXE의 DB 요청·분석·작동 진단 | PASS |
| T31 | EXE 자동 종료 | PASS |
| T32 | 시험 중 실행 소스 일치 | PASS |

### T01. 기존·추가 회귀 테스트

- 예상 결과: 전체 테스트 성공
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "exit_code": 0,
  "tests": 142
}
```

### T02. 3개 서비스 준비 확인

- 예상 결과: 200 ready
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": "ready",
  "policy_version": "demo-v2"
}
```

### T03. 배정 문서 읽기

- 예상 결과: 200 ALLOW SUCCEEDED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "NORMAL_READ",
  "name": "정상 문서 읽기 (Alice -> report-alice-001)",
  "expected": "ALLOW (200 OK)",
  "status": 200,
  "result": {
    "action_id": "cee3e85d-62f2-4e2c-acc4-2babdf0f264d",
    "decision": "ALLOW",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": null,
    "approval_state": null,
    "execution_id": "6b599eeb-7781-4679-8076-2a44c3ab9ac4",
    "trace_id": "1955d317-f146-4f20-92ce-7547b48e00c0",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-04c8fdbf-d0f1-4855-97c4-54e149f7dfb0",
      "execution_id": "6b599eeb-7781-4679-8076-2a44c3ab9ac4",
      "result": {
        "document_id": "report-alice-001",
        "content": "Quarterly operations report for Alice (fictional)\n\nAll values in this exercise are synthetic. Service availability was 99.2 percent in the fictional sample period. Three maintenance tasks were completed. The next review is scheduled for the end of the fictional quarter.\n",
        "content_hash": "ac3fdcc25b70106571b34ea4c44dbff52308baf5d40091546c63fd23f6a64e89"
      }
    }
  },
  "mitre": "None (Benign)",
  "severity": "INFO"
}
```

### T04. 테넌트 경계와 부작용

- 예상 결과: 403 DENY, 산출물/전송함/영수증 증가 없음
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "response": {
    "scenario": "CROSS_TENANT_VIOLATION",
    "name": "타 테넌트 자원 무단 접근 (Alice -> Bob's South doc)",
    "expected": "DENY (403 Forbidden)",
    "status": 403,
    "result": {
      "action_id": "f7ec6fa1-043d-4a33-bb02-f345a15e22a1",
      "decision": "DENY",
      "state": "DENIED",
      "reason_codes": [
        "RESOURCE_OUT_OF_SCOPE"
      ],
      "approval_id": null,
      "approval_state": null,
      "execution_id": "6d49fb5d-333b-4ef5-a7b8-13102794ef76",
      "trace_id": "fa5364db-cd7c-430e-b26c-4c78ecb3c858",
      "policy_version": "demo-v2",
      "result": null
    },
    "mitre": "T1078 (Valid Accounts / Cross-Scope)",
    "severity": "HIGH"
  },
  "before": [
    0,
    0,
    1
  ],
  "after": [
    0,
    0,
    1
  ]
}
```

### T05. 프롬프트 인젝션

- 예상 결과: 200 SUSPICIOUS
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "PROMPT_INJECTION",
  "name": "간접 프롬프트 인젝션 패턴 검사 (다층 탐지)",
  "expected": "SUSPICIOUS (200 OK with flag)",
  "status": 200,
  "result": {
    "inspection_id": "369f2fb3-393f-4a0c-9085-7926c3cb5fc4",
    "verdict": "SUSPICIOUS",
    "reason_codes": [
      "PROMPT_INJECTION_PATTERN"
    ],
    "scanner_version": "rules-v2",
    "content_hash": "62a0ea7039eab31e4d18dd14c79a2fb6511c856476a1783c2c9d935682feb1f8"
  },
  "mitre": "T1059 (Command & Scripting Interpreter / Injection)",
  "severity": "CRITICAL"
}
```

### T06. 유니코드 은닉

- 예상 결과: 200 SUSPICIOUS
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "UNICODE_OBFUSCATION",
  "name": "유니코드 제로너비 공백 은닉 인젝션 공격",
  "expected": "SUSPICIOUS (정규화 후 탐지)",
  "status": 200,
  "result": {
    "inspection_id": "2e5d8698-d8dd-497d-86ed-d3423566a174",
    "verdict": "SUSPICIOUS",
    "reason_codes": [
      "PROMPT_INJECTION_PATTERN"
    ],
    "scanner_version": "rules-v2",
    "content_hash": "dbeb472e2555566603fd205c2f711bf5cc85cfe948dcc003ce4a1c8c8eac8060"
  },
  "mitre": "T1027 (Obfuscated / Encrypted Information)",
  "severity": "HIGH"
}
```

### T07. 정상 입력 검사

- 예상 결과: 200 CLEAR
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "CUSTOM_PROMPT",
  "name": "사용자 직접 입력 검사 (Please summarize the assigned ...)",
  "expected": "CLEAR or SUSPICIOUS",
  "status": 200,
  "result": {
    "inspection_id": "23c2b915-90e2-4802-acb3-da0eddeec9a6",
    "verdict": "CLEAR",
    "reason_codes": [],
    "scanner_version": "rules-v2",
    "content_hash": "b30f8abfc14924819693b743cba3061fe173a1bbf137ade96685a3936dcce779"
  },
  "mitre": "None",
  "severity": "INFO"
}
```

### T08. 실제 산출물 생성과 승인 대기

- 예상 결과: 202 REQUIRE_APPROVAL PENDING_APPROVAL
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "UNAPPROVED_HIGH_RISK_ACTION",
  "name": "미승인 고위험 보고서 전송 시도",
  "expected": "REQUIRE_APPROVAL (202 Accepted)",
  "status": 202,
  "result": {
    "action_id": "01f2696a-2736-409e-a684-9055377144ee",
    "decision": "REQUIRE_APPROVAL",
    "state": "PENDING_APPROVAL",
    "reason_codes": [],
    "approval_id": "22c9b006-54fb-42a7-93f7-88e244fa879e",
    "approval_state": "PENDING",
    "execution_id": "02304d3e-d7ac-4f65-8a9e-e9780b7f4204",
    "trace_id": "0d3ba7cd-828b-4a2c-8ed4-527d7a9a4e48",
    "policy_version": "demo-v2",
    "result": null
  },
  "mitre": "T1048 (Exfiltration Over Alternative Protocol)",
  "severity": "HIGH"
}
```

### T09. 승인 전 실행 차단

- 예상 결과: 409 ACTION_NOT_EXECUTABLE, outbox 0건
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 409,
  "response": {
    "error": "ACTION_NOT_EXECUTABLE",
    "message": "Action is not approved and ready to execute"
  },
  "outbox": 0
}
```

### T10. 검토자 승인

- 예상 결과: 200 APPROVED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "response": {
    "approval_id": "22c9b006-54fb-42a7-93f7-88e244fa879e",
    "action_id": "01f2696a-2736-409e-a684-9055377144ee",
    "state": "APPROVED"
  }
}
```

### T11. 승인 후 실행·재실행 중복 방지

- 예상 결과: 200 SUCCEEDED, 재실행 후에도 outbox 1건
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "response": {
    "action_id": "01f2696a-2736-409e-a684-9055377144ee",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "22c9b006-54fb-42a7-93f7-88e244fa879e",
    "approval_state": "CONSUMED",
    "execution_id": "02304d3e-d7ac-4f65-8a9e-e9780b7f4204",
    "trace_id": "0d3ba7cd-828b-4a2c-8ed4-527d7a9a4e48",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-41d0148b-8be3-44c5-bd13-b1ba2cc7c1f0",
      "execution_id": "02304d3e-d7ac-4f65-8a9e-e9780b7f4204",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-43f4227b-deda-4f72-b511-2daef6c16e04",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      }
    }
  },
  "repeat_status": 200,
  "repeat": {
    "action_id": "01f2696a-2736-409e-a684-9055377144ee",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "22c9b006-54fb-42a7-93f7-88e244fa879e",
    "approval_state": "CONSUMED",
    "execution_id": "02304d3e-d7ac-4f65-8a9e-e9780b7f4204",
    "trace_id": "0d3ba7cd-828b-4a2c-8ed4-527d7a9a4e48",
    "policy_version": "demo-v2",
    "result": {
      "execution_id": "02304d3e-d7ac-4f65-8a9e-e9780b7f4204",
      "action_id": "01f2696a-2736-409e-a684-9055377144ee",
      "receipt_id": "receipt-41d0148b-8be3-44c5-bd13-b1ba2cc7c1f0",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-43f4227b-deda-4f72-b511-2daef6c16e04",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      },
      "created": 1793774376.325793
    }
  },
  "outbox": 1
}
```

### T12. 감사 해시 연결

- 예상 결과: 200 VALID, 검증 건수 > 0, 변조 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenario": "AUDIT_VERIFY",
  "name": "감사 로그 Merkle Hash Chain 무결성 검증",
  "expected": "VALID (200 OK)",
  "status": 200,
  "result": {
    "status": "VALID",
    "total_records": 14,
    "chained_records": 14,
    "tampered_record_ids": [],
    "latest_chain_hash": "046104c0c275c2143b16e854c6d7a0c51427b0a233de32b4675f81e479f6c798"
  },
  "mitre": "T1562 (Impair Defenses / Audit Tampering)",
  "severity": "INFO"
}
```

### T13. 다른 사이트에서 테스트 실행 차단

- 예상 결과: 403 SAME_ORIGIN_REQUIRED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 403,
  "response": {
    "error": "SAME_ORIGIN_REQUIRED"
  }
}
```

### T14. 도구 직접 접근 인증

- 예상 결과: 401 UNAUTHENTICATED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 401,
  "response": {
    "error": "UNAUTHENTICATED"
  }
}
```

### T15. 대시보드 감사 연결

- 예상 결과: 200, 실제 감사 이벤트 > 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "count": 14
}
```

### T16. DB 접근 요청·보안 에이전트 분석

- 예상 결과: 202 PENDING_APPROVAL, 분석 근거와 추천 대응 제공
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793774376.3800018,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793775276.3800018,
  "reviewer": null,
  "review_reason": null,
  "decided_at": null,
  "result_count": null,
  "trace_id": "5fcf18ec-bf2d-42a2-8977-427b34709afb",
  "request_id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
  "state": "PENDING_APPROVAL",
  "arguments": {
    "dataset_id": "operations",
    "columns": [
      "ticket_id",
      "status",
      "description"
    ],
    "filters": {},
    "row_limit": 25,
    "purpose": "승인 기반 DB 조회 통합 검증입니다."
  },
  "analysis": {
    "engine": "db-security-rules-v2",
    "method": "policy_and_behavior_rules",
    "risk_score": 15,
    "risk_level": "low",
    "sensitive": false,
    "bulk": false,
    "abnormal": false,
    "reason_codes": [],
    "reasons": [
      "등록된 데이터와 열, 조회량 범위 안의 읽기 요청입니다."
    ],
    "recommendation": "업무 목적과 요청자의 담당 범위를 확인한 뒤 일회성 조회를 승인하세요.",
    "decision": "REQUIRE_APPROVAL",
    "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
    "db_target": {
      "backend": "sqlite",
      "id": "sqlite-lab-v1"
    },
    "authorization": {
      "mode": "human",
      "role": "report-submitter"
    }
  },
  "dataset_name": "운영 지원 이력",
  "database_name": "사내 검증 DB",
  "mode": "sqlite",
  "execution_id": "08a52494-b2f1-4380-8c96-e8731ee2f3d3",
  "receipt_id": null,
  "authorization": {
    "mode": "human",
    "role": "report-submitter"
  },
  "approval_binding": {
    "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
    "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911",
    "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
  },
  "timeline": [
    {
      "at": 1793774376.3816223,
      "actor": "agent-alice",
      "event": "DB_REQUESTED",
      "details": {
        "dataset_id": "operations",
        "decision": "REQUIRE_APPROVAL",
        "risk_score": 15,
        "source_ip": "127.0.0.1",
        "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
        "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
      }
    }
  ]
}
```

### T17. 사람 승인 전 DB 조회 차단

- 예상 결과: 409 DB_APPROVAL_REQUIRED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "http": 409,
  "response": {
    "error": "DB_APPROVAL_REQUIRED",
    "message": "유효한 정책 허용 또는 승인 없이는 DB를 조회할 수 없습니다."
  }
}
```

### T18. 판단 근거를 포함한 사람 승인

- 예상 결과: 200 APPROVED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793774376.3800018,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793775276.3800018,
  "reviewer": "reviewer-demo",
  "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
  "decided_at": 1793774376.40969,
  "result_count": null,
  "trace_id": "5fcf18ec-bf2d-42a2-8977-427b34709afb",
  "request_id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
  "state": "APPROVED",
  "arguments": {
    "dataset_id": "operations",
    "columns": [
      "ticket_id",
      "status",
      "description"
    ],
    "filters": {},
    "row_limit": 25,
    "purpose": "승인 기반 DB 조회 통합 검증입니다."
  },
  "analysis": {
    "engine": "db-security-rules-v2",
    "method": "policy_and_behavior_rules",
    "risk_score": 15,
    "risk_level": "low",
    "sensitive": false,
    "bulk": false,
    "abnormal": false,
    "reason_codes": [],
    "reasons": [
      "등록된 데이터와 열, 조회량 범위 안의 읽기 요청입니다."
    ],
    "recommendation": "업무 목적과 요청자의 담당 범위를 확인한 뒤 일회성 조회를 승인하세요.",
    "decision": "REQUIRE_APPROVAL",
    "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
    "db_target": {
      "backend": "sqlite",
      "id": "sqlite-lab-v1"
    },
    "authorization": {
      "mode": "human",
      "role": "report-submitter"
    }
  },
  "dataset_name": "운영 지원 이력",
  "database_name": "사내 검증 DB",
  "mode": "sqlite",
  "execution_id": "08a52494-b2f1-4380-8c96-e8731ee2f3d3",
  "receipt_id": null,
  "authorization": {
    "mode": "human",
    "role": "report-submitter"
  },
  "approval_binding": {
    "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
    "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911",
    "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
  },
  "timeline": [
    {
      "at": 1793774376.3816223,
      "actor": "agent-alice",
      "event": "DB_REQUESTED",
      "details": {
        "dataset_id": "operations",
        "decision": "REQUIRE_APPROVAL",
        "risk_score": 15,
        "source_ip": "127.0.0.1",
        "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
        "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
      }
    },
    {
      "at": 1793774376.4108763,
      "actor": "reviewer-demo",
      "event": "DB_APPROVED",
      "details": {
        "reason": "업무 범위와 열·조회량을 확인했습니다.",
        "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
      }
    }
  ]
}
```

### T19. 승인 후 실제 SQL 조회·영수증 재사용

- 예상 결과: 25행 조회, 동일 영수증으로 재실행 응답
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "http": 200,
  "row_count": 25,
  "receipt_id": "receipt-bf50761d-315e-4079-9197-7085e729f802",
  "repeat_receipt": "receipt-bf50761d-315e-4079-9197-7085e729f802",
  "replayed": true
}
```

### T20. DB 분석 시나리오 sensitive

- 예상 결과: PENDING_APPROVAL
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 202,
  "request": {
    "id": "5dfe5a4d-815e-4892-b1aa-9996769c0369",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793774376.4905577,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 70,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793775276.4905577,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "45066ba5-f952-4586-99fb-9d0e821d43f1",
    "request_id": "5dfe5a4d-815e-4892-b1aa-9996769c0369",
    "state": "PENDING_APPROVAL",
    "arguments": {
      "dataset_id": "payroll",
      "columns": [
        "employee_id",
        "salary",
        "bank_account"
      ],
      "filters": {},
      "row_limit": 25,
      "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
    },
    "analysis": {
      "engine": "db-security-rules-v2",
      "method": "policy_and_behavior_rules",
      "risk_score": 70,
      "risk_level": "high",
      "sensitive": true,
      "bulk": false,
      "abnormal": false,
      "reason_codes": [],
      "reasons": [
        "민감·고위험 열의 정보 조회를 요청했습니다."
      ],
      "recommendation": "범위를 줄인 새 요청을 요구하거나, 현재 범위의 업무 필요성이 확인될 때만 승인하세요.",
      "decision": "REQUIRE_APPROVAL",
      "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
      "db_target": {
        "backend": "sqlite",
        "id": "sqlite-lab-v1"
      },
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    "dataset_name": "급여·정산 정보",
    "database_name": "사내 검증 DB",
    "mode": "sqlite",
    "execution_id": "0e845cf8-6ba7-43c9-8fae-82a06e0a15f8",
    "receipt_id": null,
    "authorization": {
      "mode": "human",
      "role": "report-submitter"
    },
    "approval_binding": {
      "request_hash": "38c95eb4f6e4f9108506920c59425a3bfbe2c7dd07ce80cf03b94cf0506175b1",
      "snapshot_hash": "34f5f3de5d5db16d6c4db2120075adb160decc7f7838664ac2919459e32174c0",
      "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
    },
    "timeline": [
      {
        "at": 1793774376.491122,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "payroll",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 70,
          "source_ip": "127.0.0.1",
          "request_hash": "38c95eb4f6e4f9108506920c59425a3bfbe2c7dd07ce80cf03b94cf0506175b1",
          "snapshot_hash": "34f5f3de5d5db16d6c4db2120075adb160decc7f7838664ac2919459e32174c0"
        }
      }
    ]
  }
}
```

### T21. DB 분석 시나리오 bulk

- 예상 결과: PENDING_APPROVAL
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 202,
  "request": {
    "id": "e6330bbf-fc0e-4364-ab9b-987c77c7c107",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793774376.498064,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 40,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793775276.498064,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "50973c76-6059-4404-a408-9ed571303e39",
    "request_id": "e6330bbf-fc0e-4364-ab9b-987c77c7c107",
    "state": "PENDING_APPROVAL",
    "arguments": {
      "dataset_id": "operations",
      "columns": [
        "ticket_id",
        "category",
        "status"
      ],
      "filters": {},
      "row_limit": 2000,
      "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
    },
    "analysis": {
      "engine": "db-security-rules-v2",
      "method": "policy_and_behavior_rules",
      "risk_score": 40,
      "risk_level": "medium",
      "sensitive": false,
      "bulk": true,
      "abnormal": false,
      "reason_codes": [],
      "reasons": [
        "한 번에 2,000행을 요청해 대량 조회 기준(1,000행)에 해당합니다."
      ],
      "recommendation": "범위를 줄인 새 요청을 요구하거나, 현재 범위의 업무 필요성이 확인될 때만 승인하세요.",
      "decision": "REQUIRE_APPROVAL",
      "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
      "db_target": {
        "backend": "sqlite",
        "id": "sqlite-lab-v1"
      },
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "sqlite",
    "execution_id": "a5dc0796-bcf0-43c1-b83b-678ea95f26d9",
    "receipt_id": null,
    "authorization": {
      "mode": "human",
      "role": "report-submitter"
    },
    "approval_binding": {
      "request_hash": "106d67b2aee90f729b0938ba7b2e858455699365c42ae043aaeffffdcde0a902",
      "snapshot_hash": "f1233b5c06832b962d61183525a52584739e2ff88b211159a0401cf9d1dc8114",
      "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
    },
    "timeline": [
      {
        "at": 1793774376.499148,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 40,
          "source_ip": "127.0.0.1",
          "request_hash": "106d67b2aee90f729b0938ba7b2e858455699365c42ae043aaeffffdcde0a902",
          "snapshot_hash": "f1233b5c06832b962d61183525a52584739e2ff88b211159a0401cf9d1dc8114"
        }
      }
    ]
  }
}
```

### T22. DB 분석 시나리오 abnormal

- 예상 결과: DENIED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 403,
  "request": {
    "id": "19b8bb8f-4909-49d5-9fd2-ba3d512b83da",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793774376.5062761,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 55,
    "decision": "DENY",
    "expires_at": 1793775276.5062761,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "9781ee8e-d589-4912-9325-4ce902b58220",
    "request_id": "19b8bb8f-4909-49d5-9fd2-ba3d512b83da",
    "state": "DENIED",
    "arguments": {
      "dataset_id": "operations",
      "columns": [
        "password",
        "*"
      ],
      "filters": {},
      "row_limit": 25,
      "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
    },
    "analysis": {
      "engine": "db-security-rules-v2",
      "method": "policy_and_behavior_rules",
      "risk_score": 55,
      "risk_level": "medium",
      "sensitive": false,
      "bulk": false,
      "abnormal": true,
      "reason_codes": [
        "COLUMN_NOT_REGISTERED"
      ],
      "reasons": [
        "필수 정책 위반: COLUMN_NOT_REGISTERED"
      ],
      "recommendation": "차단 유지. 요청 범위와 목적을 수정한 뒤 새로 요청하세요.",
      "decision": "DENY",
      "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
      "db_target": {
        "backend": "sqlite",
        "id": "sqlite-lab-v1"
      },
      "authorization": {
        "mode": "denied",
        "role": "report-submitter"
      }
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "sqlite",
    "execution_id": "edf1fa19-9c53-47a6-aafc-3df2f91f7741",
    "receipt_id": null,
    "authorization": {
      "mode": "denied",
      "role": "report-submitter"
    },
    "approval_binding": {
      "request_hash": "b98c01d76be37c04e87dd027f55f1977ab2d8f8da34b61131900c320e99f8796",
      "snapshot_hash": "96e3b44dc998dcbc554b9c71a525dc7ee059e5ce1f0f9019296a596679ef53e4",
      "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
    },
    "timeline": [
      {
        "at": 1793774376.506795,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "DENY",
          "risk_score": 55,
          "source_ip": "127.0.0.1",
          "request_hash": "b98c01d76be37c04e87dd027f55f1977ab2d8f8da34b61131900c320e99f8796",
          "snapshot_hash": "96e3b44dc998dcbc554b9c71a525dc7ee059e5ce1f0f9019296a596679ef53e4"
        }
      }
    ]
  }
}
```

### T23. 30분 위험도 증가·감쇠·소멸

- 예상 결과: 42 → 21 → 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
[
  42.0,
  21.0,
  0.0
]
```

### T24. 현재 위험도·일일 처리 집계

- 예상 결과: 대기+허용+차단=오늘 요청 수, 실제 위험 요인 포함
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "as_of": 1793774376.5314398,
  "timezone": "Asia/Seoul",
  "day_start": 1793718000.0,
  "metrics": {
    "pending": 2,
    "allowed": 1,
    "blocked": 1,
    "today_total": 4
  },
  "risk": {
    "score": 42.0,
    "level": "주의",
    "raw_score": 42.0,
    "factors": {
      "sensitive": 1,
      "bulk": 1,
      "abnormal": 1
    },
    "components": {
      "sensitive": 12.0,
      "bulk": 10.0,
      "abnormal": 20.0
    },
    "weights": {
      "sensitive": 12,
      "bulk": 10,
      "abnormal": 20
    },
    "window_seconds": 1800,
    "formula": "min(100, Σ[(민감×12 + 대량×10 + 비정상×20) × (1-경과초/1800)])",
    "meaning": "운영 위험 지표이며 침해 확률이나 모델의 신뢰도가 아닙니다."
  },
  "activity": [
    {
      "at": 1793772636.5314398,
      "count": 0
    },
    {
      "at": 1793772696.5314398,
      "count": 0
    },
    {
      "at": 1793772756.5314398,
      "count": 0
    },
    {
      "at": 1793772816.5314398,
      "count": 0
    },
    {
      "at": 1793772876.5314398,
      "count": 0
    },
    {
      "at": 1793772936.5314398,
      "count": 0
    },
    {
      "at": 1793772996.5314398,
      "count": 0
    },
    {
      "at": 1793773056.5314398,
      "count": 0
    },
    {
      "at": 1793773116.5314398,
      "count": 0
    },
    {
      "at": 1793773176.5314398,
      "count": 0
    },
    {
      "at": 1793773236.5314398,
      "count": 0
    },
    {
      "at": 1793773296.5314398,
      "count": 0
    },
    {
      "at": 1793773356.5314398,
      "count": 0
    },
    {
      "at": 1793773416.5314398,
      "count": 0
    },
    {
      "at": 1793773476.5314398,
      "count": 0
    },
    {
      "at": 1793773536.5314398,
      "count": 0
    },
    {
      "at": 1793773596.5314398,
      "count": 0
    },
    {
      "at": 1793773656.5314398,
      "count": 0
    },
    {
      "at": 1793773716.5314398,
      "count": 0
    },
    {
      "at": 1793773776.5314398,
      "count": 0
    },
    {
      "at": 1793773836.5314398,
      "count": 0
    },
    {
      "at": 1793773896.5314398,
      "count": 0
    },
    {
      "at": 1793773956.5314398,
      "count": 0
    },
    {
      "at": 1793774016.5314398,
      "count": 0
    },
    {
      "at": 1793774076.5314398,
      "count": 0
    },
    {
      "at": 1793774136.5314398,
      "count": 0
    },
    {
      "at": 1793774196.5314398,
      "count": 0
    },
    {
      "at": 1793774256.5314398,
      "count": 0
    },
    {
      "at": 1793774316.5314398,
      "count": 0
    },
    {
      "at": 1793774376.5314398,
      "count": 4
    }
  ],
  "risk_trend": [
    {
      "at": 1793772576.5314398,
      "score": 0.0
    },
    {
      "at": 1793772636.5314398,
      "score": 0.0
    },
    {
      "at": 1793772696.5314398,
      "score": 0.0
    },
    {
      "at": 1793772756.5314398,
      "score": 0.0
    },
    {
      "at": 1793772816.5314398,
      "score": 0.0
    },
    {
      "at": 1793772876.5314398,
      "score": 0.0
    },
    {
      "at": 1793772936.5314398,
      "score": 0.0
    },
    {
      "at": 1793772996.5314398,
      "score": 0.0
    },
    {
      "at": 1793773056.5314398,
      "score": 0.0
    },
    {
      "at": 1793773116.5314398,
      "score": 0.0
    },
    {
      "at": 1793773176.5314398,
      "score": 0.0
    },
    {
      "at": 1793773236.5314398,
      "score": 0.0
    },
    {
      "at": 1793773296.5314398,
      "score": 0.0
    },
    {
      "at": 1793773356.5314398,
      "score": 0.0
    },
    {
      "at": 1793773416.5314398,
      "score": 0.0
    },
    {
      "at": 1793773476.5314398,
      "score": 0.0
    },
    {
      "at": 1793773536.5314398,
      "score": 0.0
    },
    {
      "at": 1793773596.5314398,
      "score": 0.0
    },
    {
      "at": 1793773656.5314398,
      "score": 0.0
    },
    {
      "at": 1793773716.5314398,
      "score": 0.0
    },
    {
      "at": 1793773776.5314398,
      "score": 0.0
    },
    {
      "at": 1793773836.5314398,
      "score": 0.0
    },
    {
      "at": 1793773896.5314398,
      "score": 0.0
    },
    {
      "at": 1793773956.5314398,
      "score": 0.0
    },
    {
      "at": 1793774016.5314398,
      "score": 0.0
    },
    {
      "at": 1793774076.5314398,
      "score": 0.0
    },
    {
      "at": 1793774136.5314398,
      "score": 0.0
    },
    {
      "at": 1793774196.5314398,
      "score": 0.0
    },
    {
      "at": 1793774256.5314398,
      "score": 0.0
    },
    {
      "at": 1793774316.5314398,
      "score": 0.0
    },
    {
      "at": 1793774376.5314398,
      "score": 42.0
    }
  ],
  "recent": [
    {
      "id": "19b8bb8f-4909-49d5-9fd2-ba3d512b83da",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793774376.5062761,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 55,
      "decision": "DENY",
      "expires_at": 1793775276.5062761,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "9781ee8e-d589-4912-9325-4ce902b58220",
      "request_id": "19b8bb8f-4909-49d5-9fd2-ba3d512b83da",
      "state": "DENIED",
      "arguments": {
        "dataset_id": "operations",
        "columns": [
          "password",
          "*"
        ],
        "filters": {},
        "row_limit": 25,
        "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
      },
      "analysis": {
        "engine": "db-security-rules-v2",
        "method": "policy_and_behavior_rules",
        "risk_score": 55,
        "risk_level": "medium",
        "sensitive": false,
        "bulk": false,
        "abnormal": true,
        "reason_codes": [
          "COLUMN_NOT_REGISTERED"
        ],
        "reasons": [
          "필수 정책 위반: COLUMN_NOT_REGISTERED"
        ],
        "recommendation": "차단 유지. 요청 범위와 목적을 수정한 뒤 새로 요청하세요.",
        "decision": "DENY",
        "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
        "db_target": {
          "backend": "sqlite",
          "id": "sqlite-lab-v1"
        },
        "authorization": {
          "mode": "denied",
          "role": "report-submitter"
        }
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "sqlite",
      "execution_id": "edf1fa19-9c53-47a6-aafc-3df2f91f7741",
      "receipt_id": null,
      "authorization": {
        "mode": "denied",
        "role": "report-submitter"
      }
    },
    {
      "id": "e6330bbf-fc0e-4364-ab9b-987c77c7c107",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793774376.498064,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 40,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793775276.498064,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "50973c76-6059-4404-a408-9ed571303e39",
      "request_id": "e6330bbf-fc0e-4364-ab9b-987c77c7c107",
      "state": "PENDING_APPROVAL",
      "arguments": {
        "dataset_id": "operations",
        "columns": [
          "ticket_id",
          "category",
          "status"
        ],
        "filters": {},
        "row_limit": 2000,
        "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
      },
      "analysis": {
        "engine": "db-security-rules-v2",
        "method": "policy_and_behavior_rules",
        "risk_score": 40,
        "risk_level": "medium",
        "sensitive": false,
        "bulk": true,
        "abnormal": false,
        "reason_codes": [],
        "reasons": [
          "한 번에 2,000행을 요청해 대량 조회 기준(1,000행)에 해당합니다."
        ],
        "recommendation": "범위를 줄인 새 요청을 요구하거나, 현재 범위의 업무 필요성이 확인될 때만 승인하세요.",
        "decision": "REQUIRE_APPROVAL",
        "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
        "db_target": {
          "backend": "sqlite",
          "id": "sqlite-lab-v1"
        },
        "authorization": {
          "mode": "human",
          "role": "report-submitter"
        }
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "sqlite",
      "execution_id": "a5dc0796-bcf0-43c1-b83b-678ea95f26d9",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "5dfe5a4d-815e-4892-b1aa-9996769c0369",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793774376.4905577,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 70,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793775276.4905577,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "45066ba5-f952-4586-99fb-9d0e821d43f1",
      "request_id": "5dfe5a4d-815e-4892-b1aa-9996769c0369",
      "state": "PENDING_APPROVAL",
      "arguments": {
        "dataset_id": "payroll",
        "columns": [
          "employee_id",
          "salary",
          "bank_account"
        ],
        "filters": {},
        "row_limit": 25,
        "purpose": "월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다."
      },
      "analysis": {
        "engine": "db-security-rules-v2",
        "method": "policy_and_behavior_rules",
        "risk_score": 70,
        "risk_level": "high",
        "sensitive": true,
        "bulk": false,
        "abnormal": false,
        "reason_codes": [],
        "reasons": [
          "민감·고위험 열의 정보 조회를 요청했습니다."
        ],
        "recommendation": "범위를 줄인 새 요청을 요구하거나, 현재 범위의 업무 필요성이 확인될 때만 승인하세요.",
        "decision": "REQUIRE_APPROVAL",
        "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
        "db_target": {
          "backend": "sqlite",
          "id": "sqlite-lab-v1"
        },
        "authorization": {
          "mode": "human",
          "role": "report-submitter"
        }
      },
      "dataset_name": "급여·정산 정보",
      "database_name": "사내 검증 DB",
      "mode": "sqlite",
      "execution_id": "0e845cf8-6ba7-43c9-8fae-82a06e0a15f8",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793774376.3800018,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 15,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793775276.3800018,
      "reviewer": "reviewer-demo",
      "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
      "decided_at": 1793774376.40969,
      "result_count": 25,
      "trace_id": "5fcf18ec-bf2d-42a2-8977-427b34709afb",
      "request_id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
      "state": "SUCCEEDED",
      "arguments": {
        "dataset_id": "operations",
        "columns": [
          "ticket_id",
          "status",
          "description"
        ],
        "filters": {},
        "row_limit": 25,
        "purpose": "승인 기반 DB 조회 통합 검증입니다."
      },
      "analysis": {
        "engine": "db-security-rules-v2",
        "method": "policy_and_behavior_rules",
        "risk_score": 15,
        "risk_level": "low",
        "sensitive": false,
        "bulk": false,
        "abnormal": false,
        "reason_codes": [],
        "reasons": [
          "등록된 데이터와 열, 조회량 범위 안의 읽기 요청입니다."
        ],
        "recommendation": "업무 목적과 요청자의 담당 범위를 확인한 뒤 일회성 조회를 승인하세요.",
        "decision": "REQUIRE_APPROVAL",
        "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
        "db_target": {
          "backend": "sqlite",
          "id": "sqlite-lab-v1"
        },
        "authorization": {
          "mode": "human",
          "role": "report-submitter"
        }
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "sqlite",
      "execution_id": "08a52494-b2f1-4380-8c96-e8731ee2f3d3",
      "receipt_id": "receipt-bf50761d-315e-4079-9197-7085e729f802",
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    }
  ],
  "catalog": [
    {
      "id": "operations",
      "name": "운영 지원 이력",
      "columns": {
        "ticket_id": "internal",
        "category": "internal",
        "status": "internal",
        "description": "internal"
      }
    },
    {
      "id": "employee-directory",
      "name": "임직원 업무 연락처",
      "columns": {
        "employee_id": "internal",
        "name": "internal",
        "department": "internal",
        "work_email": "sensitive"
      }
    },
    {
      "id": "payroll",
      "name": "급여·정산 정보",
      "columns": {
        "employee_id": "internal",
        "department": "internal",
        "salary": "restricted",
        "bank_account": "restricted"
      }
    }
  ]
}
```

### T25. 언제·어디서·누가·무엇·결과의 보고서

- 예상 결과: 메타데이터, 보안 분석, 검토 근거, 처리 이력 보존
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "http": 200,
  "report": {
    "id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793774376.3800018,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 15,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793775276.3800018,
    "reviewer": "reviewer-demo",
    "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
    "decided_at": 1793774376.40969,
    "result_count": 25,
    "trace_id": "5fcf18ec-bf2d-42a2-8977-427b34709afb",
    "request_id": "9fb786ca-8cdb-4fab-ab82-c195958a02ff",
    "state": "SUCCEEDED",
    "arguments": {
      "dataset_id": "operations",
      "columns": [
        "ticket_id",
        "status",
        "description"
      ],
      "filters": {},
      "row_limit": 25,
      "purpose": "승인 기반 DB 조회 통합 검증입니다."
    },
    "analysis": {
      "engine": "db-security-rules-v2",
      "method": "policy_and_behavior_rules",
      "risk_score": 15,
      "risk_level": "low",
      "sensitive": false,
      "bulk": false,
      "abnormal": false,
      "reason_codes": [],
      "reasons": [
        "등록된 데이터와 열, 조회량 범위 안의 읽기 요청입니다."
      ],
      "recommendation": "업무 목적과 요청자의 담당 범위를 확인한 뒤 일회성 조회를 승인하세요.",
      "decision": "REQUIRE_APPROVAL",
      "limitations": "정책·행위 규칙 분석이며 위험 점수는 침해 확률이 아닙니다.",
      "db_target": {
        "backend": "sqlite",
        "id": "sqlite-lab-v1"
      },
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "sqlite",
    "execution_id": "08a52494-b2f1-4380-8c96-e8731ee2f3d3",
    "receipt_id": "receipt-bf50761d-315e-4079-9197-7085e729f802",
    "authorization": {
      "mode": "human",
      "role": "report-submitter"
    },
    "approval_binding": {
      "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
      "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911",
      "policy_hash": "8cc415fe226f517737c91a807dda9075187b8d1440bf33c16e8c4db2267b36d4"
    },
    "timeline": [
      {
        "at": 1793774376.3816223,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 15,
          "source_ip": "127.0.0.1",
          "request_hash": "a81c3f9b4544daf9eb283da019917fc95dba708d457c4ec6ba2150af22aedf1a",
          "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
        }
      },
      {
        "at": 1793774376.4108763,
        "actor": "reviewer-demo",
        "event": "DB_APPROVED",
        "details": {
          "reason": "업무 범위와 열·조회량을 확인했습니다.",
          "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
        }
      },
      {
        "at": 1793774376.4402406,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_STARTED",
        "details": {
          "execution_id": "08a52494-b2f1-4380-8c96-e8731ee2f3d3",
          "authorization": {
            "mode": "human",
            "role": "report-submitter"
          }
        }
      },
      {
        "at": 1793774376.46301,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_SUCCEEDED",
        "details": {
          "row_count": 25,
          "receipt_id": "receipt-bf50761d-315e-4079-9197-7085e729f802"
        }
      }
    ]
  }
}
```

### T26. 원클릭 실제 작동 점검

- 예상 결과: 연결·분석·DB·무결성 모든 점검 통과
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "checked_at": 1793774376.5926359,
  "passed": true,
  "checks": [
    {
      "name": "게이트웨이",
      "passed": true,
      "detail": "ready",
      "latency_ms": 1.23
    },
    {
      "name": "보안 에이전트",
      "passed": true,
      "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
      "latency_ms": 0.23
    },
    {
      "name": "보호 DB",
      "passed": true,
      "detail": "검증용 SQLite DB 읽기 연결 정상",
      "latency_ms": 13.74
    },
    {
      "name": "감사 DB",
      "passed": true,
      "detail": "감사 기록 저장소 연결됨",
      "latency_ms": 0.09
    },
    {
      "name": "감사 로그 무결성",
      "passed": true,
      "detail": "21개 해시 연결 검증, 변조 의심 0건"
    }
  ],
  "scope": "실제 연결과 분석 자체 점검입니다. 전체 네트워크 격리 검증은 포함하지 않습니다."
}
```

### T27. 동시 대시보드 조회 인증 안정성

- 예상 결과: 80개 요청 모두 200
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "total": 80,
  "successful": 80
}
```

### T28. 정상 종료 시 포트 반환

- 예상 결과: 3개 포트 모두 연결 불가
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
[
  true,
  true,
  true
]
```

### T29. 독립 EXE 기동과 6개 시나리오

- 예상 결과: 원본 폴더/Python 없이 실행, ready, 모든 시나리오 응답
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "health": {
    "status": "ready",
    "policy_version": "demo-v2"
  },
  "scenarios": {
    "normal": {
      "http": 200,
      "data": {
        "scenario": "NORMAL_READ",
        "name": "정상 문서 읽기 (Alice -> report-alice-001)",
        "expected": "ALLOW (200 OK)",
        "status": 200,
        "result": {
          "action_id": "3009792e-8b8b-489c-be22-b924ce4a2c9d",
          "decision": "ALLOW",
          "state": "SUCCEEDED",
          "reason_codes": [],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "73d6eb0c-7928-4797-af80-e94e4832518d",
          "trace_id": "95cbc53a-09ad-42ae-b058-c67ed340cdd0",
          "policy_version": "demo-v2",
          "result": {
            "receipt_id": "receipt-538e1278-9f4d-48b7-a1fb-e4440d6dcb56",
            "execution_id": "73d6eb0c-7928-4797-af80-e94e4832518d",
            "result": {
              "document_id": "report-alice-001",
              "content": "Quarterly operations report for Alice (fictional)\n\nAll values in this exercise are synthetic. Service availability was 99.2 percent in the fictional sample period. Three maintenance tasks were completed. The next review is scheduled for the end of the fictional quarter.\n",
              "content_hash": "ac3fdcc25b70106571b34ea4c44dbff52308baf5d40091546c63fd23f6a64e89"
            }
          }
        },
        "mitre": "None (Benign)",
        "severity": "INFO"
      }
    },
    "cross-tenant": {
      "http": 200,
      "data": {
        "scenario": "CROSS_TENANT_VIOLATION",
        "name": "타 테넌트 자원 무단 접근 (Alice -> Bob's South doc)",
        "expected": "DENY (403 Forbidden)",
        "status": 403,
        "result": {
          "action_id": "30adabfb-b248-4a04-87fc-14b71a85da07",
          "decision": "DENY",
          "state": "DENIED",
          "reason_codes": [
            "RESOURCE_OUT_OF_SCOPE"
          ],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "f927cb79-95ea-476b-8c51-31bb8f9cfdf9",
          "trace_id": "1c1086ed-6d5d-432a-bff6-732fe29aed6f",
          "policy_version": "demo-v2",
          "result": null
        },
        "mitre": "T1078 (Valid Accounts / Cross-Scope)",
        "severity": "HIGH"
      }
    },
    "injection": {
      "http": 200,
      "data": {
        "scenario": "PROMPT_INJECTION",
        "name": "간접 프롬프트 인젝션 패턴 검사 (다층 탐지)",
        "expected": "SUSPICIOUS (200 OK with flag)",
        "status": 200,
        "result": {
          "inspection_id": "b7b67243-4868-4e8f-aa64-f6d2f85cc469",
          "verdict": "SUSPICIOUS",
          "reason_codes": [
            "PROMPT_INJECTION_PATTERN"
          ],
          "scanner_version": "rules-v2",
          "content_hash": "62a0ea7039eab31e4d18dd14c79a2fb6511c856476a1783c2c9d935682feb1f8"
        },
        "mitre": "T1059 (Command & Scripting Interpreter / Injection)",
        "severity": "CRITICAL"
      }
    },
    "obfuscation": {
      "http": 200,
      "data": {
        "scenario": "UNICODE_OBFUSCATION",
        "name": "유니코드 제로너비 공백 은닉 인젝션 공격",
        "expected": "SUSPICIOUS (정규화 후 탐지)",
        "status": 200,
        "result": {
          "inspection_id": "bb4d7fa1-42ba-40bd-9ab5-06b640938fa2",
          "verdict": "SUSPICIOUS",
          "reason_codes": [
            "PROMPT_INJECTION_PATTERN"
          ],
          "scanner_version": "rules-v2",
          "content_hash": "dbeb472e2555566603fd205c2f711bf5cc85cfe948dcc003ce4a1c8c8eac8060"
        },
        "mitre": "T1027 (Obfuscated / Encrypted Information)",
        "severity": "HIGH"
      }
    },
    "unapproved": {
      "http": 200,
      "data": {
        "scenario": "UNAPPROVED_HIGH_RISK_ACTION",
        "name": "미승인 고위험 보고서 전송 시도",
        "expected": "REQUIRE_APPROVAL (202 Accepted)",
        "status": 202,
        "result": {
          "action_id": "8f3968c7-bd1e-45e5-bcc7-178d7da013e6",
          "decision": "REQUIRE_APPROVAL",
          "state": "PENDING_APPROVAL",
          "reason_codes": [],
          "approval_id": "2b604e96-02bc-4ef9-9fb1-fcefdd50fb22",
          "approval_state": "PENDING",
          "execution_id": "395c5c00-3620-4ba2-92ca-215aca188fbd",
          "trace_id": "1caa86e5-b279-4512-85bc-806969c14ae3",
          "policy_version": "demo-v2",
          "result": null
        },
        "mitre": "T1048 (Exfiltration Over Alternative Protocol)",
        "severity": "HIGH"
      }
    },
    "audit-verify": {
      "http": 200,
      "data": {
        "scenario": "AUDIT_VERIFY",
        "name": "감사 로그 Merkle Hash Chain 무결성 검증",
        "expected": "VALID (200 OK)",
        "status": 200,
        "result": {
          "status": "VALID",
          "total_records": 10,
          "chained_records": 10,
          "tampered_record_ids": [],
          "latest_chain_hash": "1ae1454c5dbbc8e1896a97d425d2d56806ddd8af54c05284c2426a6ac2cf38ab"
        },
        "mitre": "T1562 (Impair Defenses / Audit Tampering)",
        "severity": "INFO"
      }
    }
  },
  "binary": {
    "sha256": "9cf763756bea67bf05d18e923b51d58e68155e71dd4e0161da24597f7fbb16d6",
    "bytes": 14175820
  }
}
```

### T30. 독립 EXE의 DB 요청·분석·작동 진단

- 예상 결과: 일반은 자동 허용, 민감·대량은 승인 대기, 비정상은 차단, 진단 통과
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenarios": {
    "normal": {
      "http": 200,
      "state": "APPROVED",
      "risk": 15
    },
    "sensitive": {
      "http": 200,
      "state": "PENDING_APPROVAL",
      "risk": 70
    },
    "bulk": {
      "http": 200,
      "state": "PENDING_APPROVAL",
      "risk": 40
    },
    "abnormal": {
      "http": 200,
      "state": "DENIED",
      "risk": 55
    }
  },
  "diagnostic": {
    "checked_at": 1793774385.5680356,
    "passed": true,
    "checks": [
      {
        "name": "게이트웨이",
        "passed": true,
        "detail": "ready",
        "latency_ms": 15.15
      },
      {
        "name": "보안 에이전트",
        "passed": true,
        "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
        "latency_ms": 0.2
      },
      {
        "name": "보호 DB",
        "passed": true,
        "detail": "검증용 SQLite DB 읽기 연결 정상",
        "latency_ms": 16.38
      },
      {
        "name": "감사 DB",
        "passed": true,
        "detail": "감사 기록 저장소 연결됨",
        "latency_ms": 0.11
      },
      {
        "name": "감사 로그 무결성",
        "passed": true,
        "detail": "15개 해시 연결 검증, 변조 의심 0건"
      }
    ],
    "scope": "실제 연결과 분석 자체 점검입니다. 전체 네트워크 격리 검증은 포함하지 않습니다."
  }
}
```

### T31. EXE 자동 종료

- 예상 결과: exit 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "exit_code": 0
}
```

### T32. 시험 중 실행 소스 일치

- 예상 결과: 시작·종료 시 소스 지문 일치
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "source_sha256": "b3bff0e4e71dc4f72eee61b64647b8d99f73eb7fc003196792bf3da8df4a0506"
}
```

### 미실행 범위

- Docker 다중 네트워크 격리·사내 PostgreSQL 운영 연결(임시 PostgreSQL 기능 검증은 별도 보고서): NOT_RUN
- 코드 서명·다른 Windows PC 실행: NOT_RUN

### 재현과 증거

- 단계별 설명: [TEST_GUIDE.md](TEST_GUIDE.md)
- 구조화 결과: [results.json](results/latest/results.json)
- 회귀 테스트 로그: [unittest.log](results/latest/unittest.log)
- 감사 이벤트: [audit-events.json](results/latest/audit-events.json)
- 실행파일 로그: [exe-smoke.log](results/latest/exe-smoke.log)
- 테스트는 별도 임시 디렉터리를 사용하며 사용자 실행 데이터는 삭제하지 않습니다.

증거 파일의 정합성: [manifest.json](results/latest/manifest.json). `python -m testing.report_evidence`로 검사합니다.

<!-- ASG_RESULT_END -->
