# 가상 데이터 PostgreSQL 검증 DB와 테스트

이 환경은 실제 사내 DB와 별개입니다. PostgreSQL 17.11 전용 컨테이너와 전용 볼륨에 가상 업무 데이터를 넣었습니다. 접속은 `127.0.0.1`에만 공개하며 운영 계정·주소를 사용하지 않습니다.

## 1. 만든 DB와 데이터

| 구분 | 이름 / 내용 | 행 수 |
|---|---|---:|
| 보호 업무 DB | `asg_validation_business` | 2,700 |
| 운영 지원 이력 | `asg_access.asg_operations` | 2,400 |
| 임직원 업무 연락처 | `asg_access.asg_directory` | 200 |
| 급여·정산 | `asg_access.asg_payroll` | 100 |
| 승인·감사 DB | `asg_validation_gateway` | 테스트에 따라 누적 |

운영 이력과 연락처는 north/south 두 조직으로 나눴고, 급여·정산은 north 범위입니다. 직원명은 `가상 직원`, 이메일은 `example.test`, 계좌는 `MOCK-ACCOUNT` 표기로 생성합니다. 실제 개인정보가 아닙니다.

생성 원본은 [postgresql_validation.sql](fixtures/postgresql_validation.sql), 실제 DB에서 읽은 가상 샘플은 [data-samples.json](results/postgresql-validation/data-samples.json)입니다. 보호 계정은 SELECT만 가능하고 감사 계정과 분리합니다.

## 2. 처음 만들고 자동 테스트하기

Docker Desktop을 켜고 프로젝트 폴더에서 실행합니다.

이미 검증 대시보드가 실행 중이면 해당 서버를 종료한 뒤 자동 테스트를 실행합니다. 실행 중인 서버가 감지되면 데이터를 건드리거나 기존 PASS 보고서를 덮어쓰지 않고 안내 후 종료합니다.

```powershell
.\testing\setup.ps1
.\testing\run_validation.ps1 -TestOnly
```

처음에는 DB를 새로 만들고, 이후에는 자신이 만든 검증 DB임을 확인한 뒤 같은 데이터를 재사용합니다. 이미 만들어진 데이터나 감사 기록을 지우거나 다시 시드하지 않습니다. 재실행 간격은 1분 이상 두세요. 단시간에 여러 번 반복하면 정상적인 요청 빈도 제한이 테스트 요청에도 적용될 수 있습니다.

직접 실행하는 동일 명령은 다음과 같습니다.

```powershell
# 최초 생성
.\.venv\Scripts\python.exe -m testing.postgresql_checks --keep-db
# 기존 검증 DB를 보존한 상태로 전체 재검증
.\.venv\Scripts\python.exe -m testing.postgresql_checks --keep-db --reuse
```

예상 결과는 25단계 전부 PASS입니다. 보고서는 실행 때 갱신되므로 실패 시 FAIL과 실패 위치를 그대로 확인합니다. 기존의 자동 삭제되는 4행 최소 검증(`python -m testing.postgresql_checks`)과는 별도 환경입니다.

## 3. 순서별 테스트와 예상 결과

| 순서 | 실제 수행하는 검증 | 예상 결과 |
|---:|---|---|
| 1 | 감사 DB·보호 DB 연결과 보안 분석 점검 | 실제 PostgreSQL 연결 정상 |
| 2 | 일반 요청을 만든 직후 실행 | 승인 대기 202, 실행은 409 |
| 3 | 검토자 역할로 근거를 남겨 승인하고 실행 | 25행 반환, north 정보만 포함 |
| 4 | 동일 요청 재실행 | 같은 영수증, replayed=true |
| 5 | 상세 감사 보고서 조회 | PostgreSQL 대상, 반환량, 처리 이력 저장 |
| 6 | SQL 삽입 모양의 필터 전달 | 단순 문자열 값으로 처리, 0행 |
| 7 | 와일드카드 열 요청 | 자동 차단 403 |
| 8 | READ ONLY 연결에서 INSERT 시도 | PostgreSQL이 쓰기 거부 |
| 9 | 읽기 계정으로 DELETE 시도 | DB 권한 자체로 거부 |
| 10 | 승인 뒤 대상 ID를 변경해 실행 | 정책 변경 403 |
| 11 | 게이트웨이·도구 대상 ID 불일치 | 실행 계층에서 거부 |
| 12 | 보호 DB의 연결 포트를 일부러 틀리게 설정 | 보호 DB 빨간 상태, 비밀번호 미노출 |
| 13 | 올바른 연결로 복구 후 전체 점검 | 연결·분석·감사 무결성 정상 |
| 14 | 세 테이블의 실제 행 수와 샘플 확인 | 2,400 / 200 / 100행 |
| 15 | 업무 이메일 10행 요청·승인·실행 | 민감 요청 분류, 가상 이메일 10행 반환 |
| 16 | 급여·계좌 10행 요청·승인·실행 | 고위험 분류, 가상 급여·계좌 10행 반환 |
| 17 | 운영 이력 1,000행 요청 | 승인 전 409, 승인 후 실제 1,000행 반환 |
| 18 | 검토자가 요청 거절 후 실행 | 거절 저장, 조회는 409 |
| 19 | south 소속 에이전트의 north 급여 요청 | 자동 차단 403 |
| 20 | 검토자 토큰으로 DB 실행 | 실행 권한 없음 403 |
| 21 | 실행 계층에 south 범위 조회 | south 행만 25행 반환 |
| 22 | 한국 시간 오늘 날짜의 감사 목록 조회 | 조회 완료·거절 이력 확인 |
| 23 | 30분 위험도 조회 | 민감·대량·비정상 요청 건수 반영 |
| 24 | 전용 PostgreSQL 컨테이너 재시작 | 업무 데이터와 감사 기록 보존 |
| 25 | 테스트 후 운영 이력 재집계 | 2,400행 유지, 업무 데이터 쓰기 없음 |

자동 테스트의 검토자 승인은 가상 검토자 계정으로 API를 호출한 것입니다. 실제 사람이 화면에서 검토하는 방법은 다음 절을 따릅니다. 처음 실행에서 Docker의 임시 호스트 포트가 재시작 시 바뀌는 문제를 발견했고, 현재는 자신의 컨테이너를 확인한 뒤 새 포트를 읽어 로컬 연결 파일만 갱신합니다.

## 4. 대시보드에서 직접 검토하기

```powershell
.\.venv\Scripts\python.exe -m testing.validation_dashboard
```

기본 주소는 `http://127.0.0.1:18863`입니다. 이미 실행 중이면 같은 창을 사용하고, 다른 포트가 필요하면 `--dashboard-port 18864`를 붙입니다. `run_validation.ps1`을 `-TestOnly` 없이 실행하면 테스트 후 대시보드도 엽니다(서버 기동 후 출력된 주소에 접속).

1. 작동 테스트에서 보호 DB가 정상인지 확인합니다.
2. 일반·민감·대량 시나리오 중 하나로 요청을 생성합니다.
3. 승인 검토에서 요청자·열·목적·보안 분석을 확인합니다.
4. 근거를 적고 승인하거나 거절합니다. 승인만으로 데이터가 조회되지는 않습니다.
5. 실제 조회는 자동 테스트의 3·15·16·17단계에서 확인합니다. 직접 에이전트 명령으로 체험하려면 아래 선택 절차를 사용합니다.
6. 감사 기록에서 날짜를 선택하고 상세 보고서를 엽니다.

이 로컬 화면은 가상 에이전트·검토자 테스트 편의를 위한 것입니다. 기업 IdP나 운영용 사람 인증을 연결한 화면은 아닙니다.

### 선택: 직접 에이전트가 25행을 받아보기

이미 실행한 검증 대시보드를 해당 콘솔의 Ctrl+C로 종료한 뒤, 첫 번째 PowerShell에서 다음을 실행합니다. 토큰 값은 출력하지 않습니다.

```powershell
$ValidationBytes = New-Object byte[] 36
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($ValidationBytes)
$env:ASG_LAB_ALICE_TOKEN = [Convert]::ToBase64String($ValidationBytes)
[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'testing/.runtime/postgresql-validation/agent-token.txt'), $env:ASG_LAB_ALICE_TOKEN)
.\.venv\Scripts\python.exe -m testing.validation_dashboard
```

두 번째 PowerShell에서 다음을 실행하고 브라우저의 승인 검토에서 승인합니다. 클라이언트가 승인을 확인하면 보존형 PostgreSQL DB에서 25행을 실제로 받아옵니다.

```powershell
$ValidationLab = Get-Content 'testing/.runtime/postgresql-validation/lab/session.json' -Raw | ConvertFrom-Json
$env:GATEWAY_URL = $ValidationLab.gateway
$env:AGENT_ALICE_TOKEN = Get-Content 'testing/.runtime/postgresql-validation/agent-token.txt' -Raw
.\.venv\Scripts\python.exe -m demo_agent.db_client --row-limit 25
```

에이전트 토큰 파일도 Git 제외 경로의 가상 환경 전용 비밀입니다. 같은 DB를 사용하는 대시보드와 자동 테스트는 동시에 띄우지 말고 기존 검증 서버를 종료한 뒤 실행하세요.

## 5. 보존·중지·다시 실행

- 컨테이너 이름·현재 포트·볼륨: `testing/.runtime/postgresql-validation/session.json`
- 연결 비밀 파일과 도구 영수증: 같은 Git 제외 폴더 안에만 보존합니다. 파일 내용을 채팅이나 Git에 올리지 마세요.
- 대시보드 콘솔에서 Ctrl+C를 누르면 HTTP 서비스만 종료하고 DB·볼륨은 남깁니다.
- DB를 멈추려면 다음 명령을 사용합니다. 데이터는 보존되며 다음 대시보드 실행 시 자신의 DB를 다시 시작합니다.

```powershell
$ValidationSession = Get-Content 'testing/.runtime/postgresql-validation/session.json' -Raw | ConvertFrom-Json
docker stop $ValidationSession.container
```

운영 TLS 인증서, 사내 스키마, 기업 IdP와 컨테이너 네트워크 격리는 이번 테스트의 검증 범위가 아닙니다. 루프백 연결에 한해서만 테스트용 TLS 예외를 사용합니다.

## 6. 실제 결과보고서

[REPORT.md](results/postgresql-validation/REPORT.md)에 단계별 PASS/FAIL을, [results.json](results/postgresql-validation/results.json)에 실제 상태 코드·반환량·위험도·보존 확인값을 기록합니다.

<!-- ASG_VALIDATION_RESULT_BEGIN -->

# PostgreSQL 연결 실제 검증 결과

- 판정: **PASS**
- 시작: 2026-11-02T18:08:17.614429+09:00
- 보존형 PostgreSQL 17.11, 가상 데이터, 게이트웨이 감사 DB와 보호 DB 분리. 운영 DB 미접속.

| 검증 | 결과 |
|---|---|
| 게이트웨이 감사 DB와 보호 DB의 실제 PostgreSQL 연결 | PASS |
| 승인 전 실행 차단 | PASS |
| 사람 승인 후 실제 SELECT와 테넌트 범위 | PASS |
| 재실행 영수증 재사용 | PASS |
| PostgreSQL 감사 상세 보고서 | PASS |
| 필터 SQL 삽입을 값으로 처리 | PASS |
| 등록되지 않은 열은 승인 전에 차단 | PASS |
| DB 트랜잭션 자체가 쓰기 차단 | PASS |
| 읽기 계정의 DB 쓰기 권한 없음 | PASS |
| 승인 이후 대상 변경 거부 | PASS |
| 실행 계층도 대상 불일치 거부 | PASS |
| 연결 장애는 빨간 상태이며 인증정보 미노출 | PASS |
| 복구 후 원클릭 실제 진단과 감사 체인 | PASS |
| 세 종류 가상 데이터 2,700행 적재 | PASS |
| 민감 연락처의 승인 후 실제 조회 | PASS |
| 고위험 급여·계좌 가상 데이터 조회 | PASS |
| 대량 요청의 승인 전 차단·승인 후 1,000행 조회 | PASS |
| 사람이 거절한 요청은 조회 불가 | PASS |
| 다른 테넌트 급여 요청 자동 차단 | PASS |
| 검토자에게 DB 실행 권한을 주지 않음 | PASS |
| 실행 계층의 south 행 범위 | PASS |
| 날짜별 감사 DB에서 완료·거절 이력 조회 | PASS |
| 민감·대량·비정상 요청이 30분 위험도에 반영 | PASS |
| DB 재시작 후 가상 데이터·감사 기록 보존 | PASS |
| 보호 DB 행 보존 | PASS |

관찰값: [results.json](results/postgresql-validation/results.json)

운영 인증서 배포·사내 DB·기업 IdP·Docker 네트워크 격리는 이 결과의 검증 범위가 아닙니다.

## 보존된 검증 환경

- 보호 DB: `asg_validation_business`
- 감사 DB: `asg_validation_gateway`
- 가상 운영 이력 2,400행 / 임직원 연락처 200행 / 급여·정산 100행
- DB와 전용 볼륨은 테스트 후에도 보존합니다. 접속 비밀 파일은 Git 제외 경로에만 있습니다.
- 단계별 재현·예상 결과: [검증 DB 설명서](VALIDATION_DB_GUIDE.md)

## 1. 게이트웨이 감사 DB와 보호 DB의 실제 PostgreSQL 연결

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "version": "17.11",
  "target": {
    "backend": "postgresql",
    "id": "asg-validation-1159bc02b6"
  },
  "items": [
    {
      "key": "gateway",
      "name": "게이트웨이",
      "status": "up",
      "detail": "ready",
      "checked_at": 1793610497.9134436,
      "latency_ms": 2.04
    },
    {
      "key": "security_agent",
      "name": "보안 에이전트",
      "status": "up",
      "engine": "db-security-rules-v1",
      "checked_at": 1793610497.9139671,
      "last_analysis_at": null,
      "latency_ms": 0.48,
      "detail": "정상·정책 위반 입력 분석 자체 점검 통과"
    },
    {
      "key": "protected_db",
      "name": "보호 DB",
      "status": "up",
      "detail": "PostgreSQL 읽기 전용 연결·등록 대상 권한 정상",
      "checked_at": 1793610497.9378207,
      "latency_ms": 23.9
    },
    {
      "key": "audit_db",
      "name": "감사 DB",
      "status": "up",
      "detail": "감사 기록 저장소 연결됨",
      "checked_at": 1793610497.9394267,
      "latency_ms": 1.93
    }
  ]
}
```

## 2. 승인 전 실행 차단

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "request": 202,
  "execute_before_approval": 409
}
```

## 3. 사람 승인 후 실제 SELECT와 테넌트 범위

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "approved": 200,
  "execute": 200,
  "row_count": 25,
  "state": "SUCCEEDED"
}
```

## 4. 재실행 영수증 재사용

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "replayed": true
}
```

## 5. PostgreSQL 감사 상세 보고서

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "mode": "postgresql",
  "events": 4
}
```

## 6. 필터 SQL 삽입을 값으로 처리

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "row_count": 0
}
```

## 7. 등록되지 않은 열은 승인 전에 차단

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": 403,
  "state": "DENIED"
}
```

## 8. DB 트랜잭션 자체가 쓰기 차단

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "read_only_transaction_enforced": true
}
```

## 9. 읽기 계정의 DB 쓰기 권한 없음

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "db_grant_denies_delete": true
}
```

## 10. 승인 이후 대상 변경 거부

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": 403
}
```

## 11. 실행 계층도 대상 불일치 거부

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "target_mismatch_denied": true
}
```

## 12. 연결 장애는 빨간 상태이며 인증정보 미노출

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "protected_db": "down"
}
```

## 13. 복구 후 원클릭 실제 진단과 감사 체인

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "checks": [
    {
      "name": "게이트웨이",
      "passed": true,
      "detail": "ready",
      "latency_ms": 1.66
    },
    {
      "name": "보안 에이전트",
      "passed": true,
      "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
      "latency_ms": 0.22
    },
    {
      "name": "보호 DB",
      "passed": true,
      "detail": "PostgreSQL 읽기 전용 연결·등록 대상 권한 정상",
      "latency_ms": 20.44
    },
    {
      "name": "감사 DB",
      "passed": true,
      "detail": "감사 기록 저장소 연결됨",
      "latency_ms": 0.66
    },
    {
      "name": "감사 로그 무결성",
      "passed": true,
      "detail": "39개 해시 연결 검증, 변조 의심 0건"
    }
  ]
}
```

## 14. 세 종류 가상 데이터 2,700행 적재

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "asg_operations": 2400,
  "asg_directory": 200,
  "asg_payroll": 100
}
```

## 15. 민감 연락처의 승인 후 실제 조회

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "row_count": 10,
  "sensitive": true
}
```

## 16. 고위험 급여·계좌 가상 데이터 조회

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "row_count": 10,
  "risk_score": 70
}
```

## 17. 대량 요청의 승인 전 차단·승인 후 1,000행 조회

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "before_approval": 409,
  "row_count": 1000
}
```

## 18. 사람이 거절한 요청은 조회 불가

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "decision": 200,
  "execute": 409
}
```

## 19. 다른 테넌트 급여 요청 자동 차단

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": 403,
  "state": "DENIED"
}
```

## 20. 검토자에게 DB 실행 권한을 주지 않음

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": 403
}
```

## 21. 실행 계층의 south 행 범위

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "row_count": 25,
  "tenant": "south"
}
```

## 22. 날짜별 감사 DB에서 완료·거절 이력 조회

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "date": "2026-11-02",
  "request_count": 16
}
```

## 23. 민감·대량·비정상 요청이 30분 위험도에 반영

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "score": 100,
  "factors": {
    "sensitive": 4,
    "bulk": 2,
    "abnormal": 2
  },
  "window_seconds": 1800
}
```

## 24. DB 재시작 후 가상 데이터·감사 기록 보존

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "operations_rows": 2400,
  "audit_events": 56
}
```

## 25. 보호 DB 행 보존

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "rows_after_all_checks": 2400
}
```

<!-- ASG_VALIDATION_RESULT_END -->
