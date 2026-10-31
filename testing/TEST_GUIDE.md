# ASG DB 접근 게이트웨이 테스트 설명서

작성일: 2026-10-31 (Asia/Seoul)

이 파일에는 **환경 구축, 순서별 상세 절차, 예상 결과와 11절의 실제 결과보고서**를 함께 넣습니다. [보고서만 별도로 보기](results/latest/REPORT.md)도 가능합니다. 실제 사내 DB는 연결하지 않았으며 테스트는 가상 데이터 SQLite DB를 사용합니다.

## 1. 준비와 환경

| 목적 | 필요 환경 |
|---|---|
| 화면·실행파일 사용 | Windows 64비트, `ASG.exe`, 브라우저. Python/Docker 불필요 |
| 소스 테스트 | Python 3.10 이상, `.venv` |
| 실행파일 재빌드 | 위 환경과 `testing/build-requirements.lock`의 PyInstaller 도구 |
| 실제 운영 DB 연동 | DB 종류·계정·네트워크·업무 카탈로그를 별도로 지정해야 함 |

```powershell
# 프로젝트 루트에서 실행
.\testing\setup.ps1
.\scripts\build_exe.ps1
.\testing\run_tests.ps1
```

setup은 테스트용 가상 환경을 만들고 검증한 빌드 의존성을 설치합니다. 빌드 후에는 단일 `ASG.exe`가 생성됩니다. 설치에만 네트워크가 필요하며 기본 로컬 시나리오는 외부 LLM이나 서버를 필요로 하지 않습니다.

```text
ASG.exe                       단일 실행파일
security_agent/               카탈로그·분석·안전한 SQL 조회
gateway/app/db_access.py      요청·사람 승인·실행·감사 이력·위험도
dashboard/                    현황·승인·감사·작동 테스트
tests/test_db_access.py        새 보안·이력·동시성 검증
testing/results/latest/       실제 결과와 원본 로그
testing/results/<시각>/        회차별 증거 보관
testing/.runtime/              별도 수동 실험 데이터
```

## 2. 실행파일 기동

1. `ASG.exe`를 더블클릭합니다.
2. 실행 창의 `ASG READY http://127.0.0.1:18511`을 확인합니다.
3. 자동으로 열린 브라우저에서 왼쪽의 보안 현황·승인 검토·감사 기록·작동 테스트 메뉴를 확인합니다.
4. 초록불은 해당 시각의 실제 점검 성공, 빨간불은 실패, 회색은 확인 불가입니다.
5. 새 데이터에서는 수치가 0입니다. 이전 데이터를 사용하면 기록이 유지됩니다.

**예상 결과:** 실제 세 서비스의 준비 확인 이후에만 READY가 표시됩니다. 화면의 값은 저장된 요청으로 계산하며 가상 공격 수치나 고정 탐지 정확도를 넣지 않습니다.

기본 데이터 위치는 `%LOCALAPPDATA%\ASG\lab`입니다. 새 실험은 데이터 삭제 대신 별도 폴더와 포트를 사용하세요.

```powershell
.\ASG.exe --dashboard-port 18512 --data-dir .\testing\.runtime\manual-db
```

실행 창의 Ctrl+C로 종료합니다. 게이트웨이·도구 포트는 자동 배정되고 데이터 폴더의 `session.json`에서 주소를 확인합니다. 원본 소스 폴더 없이 EXE만 옮겨도 동작하는지는 독립 실행 검증에 기록합니다.

## 3. 화면의 뜻과 판정 기준

- **정책 결정:** 요청을 승인 대기·허용·차단으로 분류하는 것. 보안 분석 추천과 실제 실행 권한은 분리합니다.
- **승인 대기:** 오늘 접수했으며 아직 유효한 사람 결정을 기다리는 요청
- **허용:** 오늘 접수하여 사람이 승인한 요청. 조회가 끝났다는 뜻으로만 사용하지 않음
- **차단:** 오늘 접수한 정책 위반·검토자 거절·승인 만료 요청
- **오늘 DB 조회 요청:** 오늘 접수 건수. 실제 반환 행 수가 아님
- **현재 위험도:** 최근 30분의 요청을 시간 감쇠하여 계산한 운영 지표. 침해 확률이 아님

메인 집계의 대기+허용+차단=오늘 요청 수를 확인합니다. 승인 메뉴의 수는 날짜와 무관한 현재 전체 유효 대기 건수여서 메인 일일 집계와 다를 수 있습니다.

## 4. 수동 시나리오: 요청과 보안 분석

### 4-1. 일반 요청

1. 작동 테스트 메뉴를 엽니다.
2. `일반 정보 25행 요청`을 선택하고 `검증 요청 보내기`를 누릅니다.
3. 결과의 HTTP 202와 승인 대기를 확인합니다.
4. 승인 검토 메뉴에서 시간순으로 해당 요청을 찾고 검토를 누릅니다.

**예상:** 정상 소량 읽기도 자동 실행하지 않습니다. 보고서에 요청 시각, 서버가 관찰한 IP, agent-alice/alice, north, 조회 대상과 열·행 수·업무 목적이 나타납니다. 기본 개별 위험도는 15점이며 근거와 추천 대응을 표시합니다.

### 4-2. 민감정보 요청

1. 작동 테스트에서 `급여·계좌 정보 요청`을 보냅니다.
2. 승인 목록을 `위험도 높은 순`으로 정렬합니다.
3. 요청 보고서에서 salary·bank_account와 분석 근거를 확인합니다.

**예상:** 승인 대기이며 restricted 열은 일반 요청보다 높은 70점입니다. 메인 30분 위험도에서는 민감정보 요인이 증가합니다. 점수만으로 DB 접근을 허용하지 않습니다.

### 4-3. 대량 요청

1. `대량 정보 2,000행 요청`을 보냅니다.
2. 보고서의 요청량과 대량 조회 경고를 확인합니다.

**예상:** 개별 위험도 40점, 승인 대기입니다. 대량 기준은 1,000행이고 최대 5,000행입니다. 실제 가상 DB는 요청보다 행이 적을 수 있습니다. 요청량과 반환량을 구분합니다.

### 4-4. 비정상 요청

1. `미등록 열·와일드카드 요청`을 보냅니다.
2. 자동 차단·HTTP 403과 보고서의 사유를 확인합니다.

**예상:** password 또는 * 열은 등록되지 않았으므로 거부합니다. 해당 보고서에는 사람의 승인 버튼이 없어야 합니다. 수정한 범위의 새 요청을 제출해야 합니다.

## 5. 수동 시나리오: 사람의 판단과 처리 이력

### 5-1. 거절

1. 민감정보 요청 보고서를 엽니다.
2. 분석 결과와 추천 대응, 업무 목적을 읽습니다.
3. 판단 근거에 `운영 지원 조회 목적에 급여·계좌 정보가 필요하지 않아 거절합니다.`를 입력합니다.
4. 요청 거절을 누릅니다.

**예상:** 상태가 검토자 차단으로 바뀌고, reviewer-demo·판단 사유·결정 시각과 처리 이력이 보존됩니다. 목록의 대기 수가 줄어듭니다.

### 5-2. 승인

1. 일반 요청 보고서를 엽니다.
2. 업무 필요성과 열·조회량을 확인합니다.
3. 3자 이상의 판단 근거를 입력하고 조회 승인을 누릅니다.

**예상:** 허용·실행 대기로 바뀝니다. **승인만으로 DB 조회는 실행되지 않습니다.** 원래 에이전트가 별도로 execute를 요청해야 합니다. 승인 전 실행, 승인 후 변조·만료, 다른 에이전트 실행은 자동 테스트에서 거부됨을 확인합니다.

### 5-3. 감사 기록

1. 감사 기록 메뉴에서 오늘 날짜를 선택합니다.
2. 처리된 요청의 보고서를 엽니다.
3. 언제·어디서·누가·무엇을 요청했는지와 분석·사람 결정·실행 결과를 확인합니다.
4. 다른 날짜를 선택해 빈 상태 또는 과거 기록을 확인합니다.
5. 50건을 넘으면 페이지를 이동합니다.

**예상:** 한국 시간 자정을 기준으로 접수일별 기록을 조회합니다. 최신 200건으로 잘리지 않으며 서버 재시작 후에도 남습니다. 실제 DB 결과 행 본문이나 토큰은 보고서에 표시하지 않습니다. 프록시·시뮬레이터의 IP가 기록될 수 있으며 이를 실제 외부 에이전트 원본 IP라고 꾸미지 않습니다.

## 6. 30분 위험도 검증

```text
요청 기여도 = (민감×12 + 대량×10 + 비정상×20) × (1-경과초/1800)
현재 위험도 = min(100, 최근 30분 요청 기여도의 합)
```

한 요청이 세 조건을 모두 가지면 최초 42점, 15분 뒤 21점, 30분 뒤 0점이 됩니다. 자동 검증은 실제 30분을 기다리는 대신 입력 사건 시각과 평가 시각을 통제하여 경계값을 확인합니다. 실제 화면은 서버의 현재 시각으로 계산하고 10초마다 갱신합니다.

**예상:** 민감·대량·비정상 요청이 추가되면 해당 요인이 증가하고, 새 위험 요청이 없으면 점수가 줄어들며 30분 후 해당 요청의 기여도가 사라집니다. 최대 100점을 넘지 않습니다. 분석 당시의 개별 요청 위험도는 보고서 증거이므로 그대로 보존합니다.

## 7. 원클릭 작동 점검

1. 작동 테스트에서 `전체 작동 점검`을 누릅니다.
2. 게이트웨이, 보안 에이전트, 보호 DB, 감사 DB, 감사 로그 무결성의 결과를 확인합니다.
3. 다른 메뉴와 새로고침을 사용해도 실제 연결 상태가 표시되는지 확인합니다.

**예상:** 정상일 때 다섯 항목을 통과합니다. 보안 에이전트는 정상·위반 입력을 실제로 분석하는 자체 점검을 수행합니다. 의존성 연결 실패 시 빨간불과 실패 사유를 표시합니다. 자동 통합 테스트에서는 도구 연결을 끊은 조건을 만들어 오탐 정상 표시가 없는지도 검증합니다.

현재 엔진은 정책·행위 규칙 모듈이며 별도 LLM 서버가 동작한다고 표시하지 않습니다. 진단은 연결과 분석 자체 점검이며 전체 네트워크 격리나 외부 공격 전체 방어를 증명하지 않습니다.

## 8. 자동 검증 순서와 예상 결과

```powershell
.\testing\run_tests.ps1
```

| ID | 범위 | 예상 결과 |
|---|---|---|
| T01 | 전체 회귀 테스트 | 기존·신규 테스트 전부 성공 |
| T02~T15 | 기존 문서 도구·승인·입력 검사·감사 | 기존 기능의 보안 경계와 부작용 보존 |
| T16 | DB 요청과 분석 | 202 승인 대기, 근거·추천 대응 제공 |
| T17 | 승인 전 DB 실행 | 409 DB_APPROVAL_REQUIRED |
| T18 | 사람 승인 | 판단 근거와 APPROVED 보존 |
| T19 | 실제 DB 조회·재시도 | 25행, 재시도는 동일 영수증 사용 |
| T20~T22 | 민감·대량·비정상 | 민감/대량 승인 대기, 비정상 차단 |
| T23 | 시간 감쇠 | 42→21→0 |
| T24 | 집계·위험도 | 실제 요인과 정확한 일일 합계 |
| T25 | 상세보고서 | 요청·분석·결정·실행 이력 보존 |
| T26 | 원클릭 진단 | 모든 실제 점검 성공 |
| T27 | 동시 조회 | 동시 대시보드 HTTP 80건 모두 200 |
| T28 | 정상 종료 | 세 포트 반환 |
| T29 | 독립 EXE | 원본 폴더 없이 기존 여섯 시나리오 동작 |
| T30 | EXE DB 기능 | 새 네 DB 시나리오와 진단 동작 |
| T31 | EXE 종료 | 종료 코드 0 |

새 회귀 테스트는 승인 전 실행, 사람 권한 분리, 테넌트·열 범위, 임의 SQL, 요청·정책·분석 스냅샷, 만료·중복 결정, 영수증, 한국 시간 날짜 경계, 200건을 넘는 이력, 재시작 보존, 보안 분석 실패 차단, 의존성 고장과 동시 인증을 확인합니다.

실행파일이 아직 없을 때는 `run_tests.ps1 -SkipExe`로 소스만 검증할 수 있습니다. 이 경우 EXE 검증은 NOT_RUN이고 전체 판정은 PARTIAL입니다. FAIL은 실제 불일치, NOT_RUN은 미실행입니다.

## 9. 사내 에이전트 API 예제

[구조·API 설명서](../docs/DB_ACCESS_GATEWAY.md)의 7~8절을 따릅니다. 토큰을 환경 변수에 지정하고 예제 에이전트를 실행하면 사람이 승인할 때까지 기다린 뒤 별도로 DB 조회를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m demo_agent.db_client --row-limit 25
```

먼저 GATEWAY_URL과 AGENT_ALICE_TOKEN을 지정해야 합니다. 임직원 신원·운영 DB를 실제로 연결하지 않은 상태에서는 검증 principal과 가상 데이터를 사용합니다. 실제 DB 비밀번호나 운영 데이터를 이 설명서에 적지 마세요.

## 10. 결과 읽기·오류 대응·미실행 범위

- [REPORT.md](results/latest/REPORT.md): 실제 실행 시각·판정·관찰 응답
- [results.json](results/latest/results.json): 구조화 판정과 EXE SHA-256
- [unittest.log](results/latest/unittest.log): 테스트 이름별 원본 결과
- [db-access-report.json](results/latest/db-access-report.json): 실제 DB 요청 보고서
- [exe-smoke.log](results/latest/exe-smoke.log): 독립 실행 로그
- [화면 검증 기록](DESIGN_REVIEW.md): 화면과 실제 조작의 증거·한계

| 증상 | 대응 |
|---|---|
| 포트 사용 중 | 다른 dashboard-port 사용. 다른 프로세스를 임의 종료하지 않음 |
| 데이터 폴더 사용 중 | 본인이 실행한 기존 ASG를 종료하거나 새 data-dir 사용 |
| 검토자 토큰 오류 | 컨테이너 모드에서 올바른 검토자 토큰 입력 |
| 승인 409 | 만료·이미 결정·정책 변경 여부를 확인하고 새 요청 |
| 대기 한도 초과 | 기존 요청을 검토·정리한 뒤 재요청 |
| 연결 실패 | 실행 창과 연결 상태를 확인하고 새로고침. 오래된 수치를 최신으로 해석하지 않음 |
| 테스트 FAIL | 해당 ID의 실제 응답·원본 로그 확인 후 재실행 |

현재 실제 사내 DB 연결, 기업 IdP, 외부 LLM, PostgreSQL·Docker 격리 실동작, 코드 서명과 다른 PC 실행은 별도 확인 대상입니다. 로컬 PASS를 이 범위까지 확대하지 않습니다. 기존 데이터·Docker 볼륨은 자동 삭제하지 않습니다. 기록 초기화가 필요하면 새 데이터 디렉터리를 사용합니다.

소스를 수정했다면 재빌드 후 테스트합니다. 결과의 SHA-256과 현재 실행파일을 비교해 같은 빌드인지 확인합니다. 환경·중간 빌드·원본 증거는 각각 `.venv/`, `build/`, `testing/results/`에 보존합니다.

<!-- ASG_RESULT_BEGIN -->

## 11. 실제 테스트 결과보고서

- 실행: 2026-11-01 01:45:23 ~ 01:46:09 (Asia/Seoul)
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

### T01. 기존·추가 회귀 테스트

- 예상 결과: 전체 테스트 성공
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "exit_code": 0,
  "tests": 112
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
    "action_id": "9ca7684c-89f5-47e5-bbe8-ab98e95cc2cb",
    "decision": "ALLOW",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": null,
    "approval_state": null,
    "execution_id": "c28f4a1e-40da-40dc-9c92-57b1dfe21c0c",
    "trace_id": "654bd5f1-4905-421d-973a-c585d25a8f44",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-05bdb26d-618e-40bb-ae5d-889781ee72dd",
      "execution_id": "c28f4a1e-40da-40dc-9c92-57b1dfe21c0c",
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
      "action_id": "2f0ad728-1b10-48cf-a756-3f89cc901807",
      "decision": "DENY",
      "state": "DENIED",
      "reason_codes": [
        "RESOURCE_OUT_OF_SCOPE"
      ],
      "approval_id": null,
      "approval_state": null,
      "execution_id": "a324d5fb-7b6a-4533-bc73-4c06b7d5e6a0",
      "trace_id": "70febef7-9a1b-436a-bba7-fa1c144c61ac",
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
    "inspection_id": "51bfa23b-6c39-4299-8cd1-6123ce9452fc",
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
    "inspection_id": "ed13c4f4-7e0f-4f3d-9f46-9a3d97f9dc3d",
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
    "inspection_id": "d3b57f2c-f9e6-4651-947c-8d8da57bcc40",
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
    "action_id": "c436d106-3cab-4125-a45d-c6b8d343cf6f",
    "decision": "REQUIRE_APPROVAL",
    "state": "PENDING_APPROVAL",
    "reason_codes": [],
    "approval_id": "015d466e-fd34-4ea1-9ac8-bf935fec11b5",
    "approval_state": "PENDING",
    "execution_id": "61769427-25d1-4179-8080-c8419d6781ee",
    "trace_id": "472bfb78-4411-4663-96ae-10e46c68fa3a",
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
    "approval_id": "015d466e-fd34-4ea1-9ac8-bf935fec11b5",
    "action_id": "c436d106-3cab-4125-a45d-c6b8d343cf6f",
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
    "action_id": "c436d106-3cab-4125-a45d-c6b8d343cf6f",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "015d466e-fd34-4ea1-9ac8-bf935fec11b5",
    "approval_state": "CONSUMED",
    "execution_id": "61769427-25d1-4179-8080-c8419d6781ee",
    "trace_id": "472bfb78-4411-4663-96ae-10e46c68fa3a",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-6c04122f-c0d9-4a46-97ce-5ba10c9af27d",
      "execution_id": "61769427-25d1-4179-8080-c8419d6781ee",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-eab50832-32bb-4f0c-97b7-97ff438d94f6",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      }
    }
  },
  "repeat_status": 200,
  "repeat": {
    "action_id": "c436d106-3cab-4125-a45d-c6b8d343cf6f",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "015d466e-fd34-4ea1-9ac8-bf935fec11b5",
    "approval_state": "CONSUMED",
    "execution_id": "61769427-25d1-4179-8080-c8419d6781ee",
    "trace_id": "472bfb78-4411-4663-96ae-10e46c68fa3a",
    "policy_version": "demo-v2",
    "result": {
      "execution_id": "61769427-25d1-4179-8080-c8419d6781ee",
      "action_id": "c436d106-3cab-4125-a45d-c6b8d343cf6f",
      "receipt_id": "receipt-6c04122f-c0d9-4a46-97ce-5ba10c9af27d",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-eab50832-32bb-4f0c-97b7-97ff438d94f6",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      },
      "created": 1793465145.5754404
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
    "latest_chain_hash": "f617e6757be16f181ca97c6f1d12cb04bdc2406b6816618f8617a218ad728111"
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
  "id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793465145.606736,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793466045.606736,
  "reviewer": null,
  "review_reason": null,
  "decided_at": null,
  "result_count": null,
  "trace_id": "14731f2f-1eaa-47d4-aa5d-a91e0da1be3a",
  "request_id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
  "state": "PENDING_APPROVAL",
  "arguments": {
    "dataset_id": "operations",
    "columns": [
      "ticket_id",
      "status"
    ],
    "filters": {},
    "row_limit": 25,
    "purpose": "승인 기반 DB 조회 통합 검증입니다."
  },
  "analysis": {
    "engine": "db-security-rules-v1",
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
    "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
  },
  "dataset_name": "운영 지원 이력",
  "database_name": "사내 검증 DB",
  "mode": "fictional_sqlite_lab",
  "execution_id": "c7f4a9f1-a8b0-4bcd-bc35-1bc1f4c95100",
  "receipt_id": null,
  "approval_binding": {
    "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
    "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5",
    "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
  },
  "timeline": [
    {
      "at": 1793465145.608736,
      "actor": "agent-alice",
      "event": "DB_REQUESTED",
      "details": {
        "dataset_id": "operations",
        "decision": "REQUIRE_APPROVAL",
        "risk_score": 15,
        "source_ip": "127.0.0.1",
        "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
        "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5"
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
    "message": "유효한 사람의 승인 없이는 DB를 조회할 수 없습니다."
  }
}
```

### T18. 판단 근거를 포함한 사람 승인

- 예상 결과: 200 APPROVED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793465145.606736,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793466045.606736,
  "reviewer": "reviewer-demo",
  "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
  "decided_at": 1793465145.6147366,
  "result_count": null,
  "trace_id": "14731f2f-1eaa-47d4-aa5d-a91e0da1be3a",
  "request_id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
  "state": "APPROVED",
  "arguments": {
    "dataset_id": "operations",
    "columns": [
      "ticket_id",
      "status"
    ],
    "filters": {},
    "row_limit": 25,
    "purpose": "승인 기반 DB 조회 통합 검증입니다."
  },
  "analysis": {
    "engine": "db-security-rules-v1",
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
    "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
  },
  "dataset_name": "운영 지원 이력",
  "database_name": "사내 검증 DB",
  "mode": "fictional_sqlite_lab",
  "execution_id": "c7f4a9f1-a8b0-4bcd-bc35-1bc1f4c95100",
  "receipt_id": null,
  "approval_binding": {
    "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
    "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5",
    "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
  },
  "timeline": [
    {
      "at": 1793465145.608736,
      "actor": "agent-alice",
      "event": "DB_REQUESTED",
      "details": {
        "dataset_id": "operations",
        "decision": "REQUIRE_APPROVAL",
        "risk_score": 15,
        "source_ip": "127.0.0.1",
        "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
        "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5"
      }
    },
    {
      "at": 1793465145.6147366,
      "actor": "reviewer-demo",
      "event": "DB_APPROVED",
      "details": {
        "reason": "업무 범위와 열·조회량을 확인했습니다.",
        "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5"
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
  "receipt_id": "receipt-74631052-494b-40ca-be5f-9099ba7dd585",
  "repeat_receipt": "receipt-74631052-494b-40ca-be5f-9099ba7dd585",
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
    "id": "8b4739d3-5e09-4d9e-a475-5faee41b7998",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793465145.6790197,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 70,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793466045.6790197,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "e84a0bf5-5ef5-4a87-b4b3-2d9dbca483bf",
    "request_id": "8b4739d3-5e09-4d9e-a475-5faee41b7998",
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
      "engine": "db-security-rules-v1",
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
      "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
    },
    "dataset_name": "급여·정산 정보",
    "database_name": "사내 검증 DB",
    "mode": "fictional_sqlite_lab",
    "execution_id": "a10315ad-5562-4ff3-9af4-690085ee6515",
    "receipt_id": null,
    "approval_binding": {
      "request_hash": "38c95eb4f6e4f9108506920c59425a3bfbe2c7dd07ce80cf03b94cf0506175b1",
      "snapshot_hash": "cb0edc7739efa642ec8eef2fb824bdc01b649262db16f7f423d7352256593dac",
      "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
    },
    "timeline": [
      {
        "at": 1793465145.6800206,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "payroll",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 70,
          "source_ip": "127.0.0.1",
          "request_hash": "38c95eb4f6e4f9108506920c59425a3bfbe2c7dd07ce80cf03b94cf0506175b1",
          "snapshot_hash": "cb0edc7739efa642ec8eef2fb824bdc01b649262db16f7f423d7352256593dac"
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
    "id": "5bfaf593-e291-42c0-b5ad-ea3a7c60b433",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793465145.7114353,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 40,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793466045.7114353,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "987258f0-d923-4c99-a76b-a441a42f689a",
    "request_id": "5bfaf593-e291-42c0-b5ad-ea3a7c60b433",
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
      "engine": "db-security-rules-v1",
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
      "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "fictional_sqlite_lab",
    "execution_id": "5fcb0b09-36ce-490f-ad44-78106dbfc092",
    "receipt_id": null,
    "approval_binding": {
      "request_hash": "106d67b2aee90f729b0938ba7b2e858455699365c42ae043aaeffffdcde0a902",
      "snapshot_hash": "8a69579fe75595a12d3fa121dbf8acf385ee37cd9c51ba1a305f534312acdedf",
      "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
    },
    "timeline": [
      {
        "at": 1793465145.7124343,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 40,
          "source_ip": "127.0.0.1",
          "request_hash": "106d67b2aee90f729b0938ba7b2e858455699365c42ae043aaeffffdcde0a902",
          "snapshot_hash": "8a69579fe75595a12d3fa121dbf8acf385ee37cd9c51ba1a305f534312acdedf"
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
    "id": "8bb4b81f-190d-48fe-acec-d544ba17d10b",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793465145.7184343,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 55,
    "decision": "DENY",
    "expires_at": 1793466045.7184343,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "1c1273d5-7ce4-4efd-a538-49a720c41db7",
    "request_id": "8bb4b81f-190d-48fe-acec-d544ba17d10b",
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
      "engine": "db-security-rules-v1",
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
      "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "fictional_sqlite_lab",
    "execution_id": "e93526f3-d7fd-4e57-96d1-411742ad1fb7",
    "receipt_id": null,
    "approval_binding": {
      "request_hash": "b98c01d76be37c04e87dd027f55f1977ab2d8f8da34b61131900c320e99f8796",
      "snapshot_hash": "8179d31a98bdc0f8cd1fdb5f026a71781af57415b6c91b4f924cbe6aa7ba25b1",
      "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
    },
    "timeline": [
      {
        "at": 1793465145.7194352,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "DENY",
          "risk_score": 55,
          "source_ip": "127.0.0.1",
          "request_hash": "b98c01d76be37c04e87dd027f55f1977ab2d8f8da34b61131900c320e99f8796",
          "snapshot_hash": "8179d31a98bdc0f8cd1fdb5f026a71781af57415b6c91b4f924cbe6aa7ba25b1"
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
  "as_of": 1793465145.7415075,
  "timezone": "Asia/Seoul",
  "day_start": 1793458800.0,
  "metrics": {
    "pending": 2,
    "allowed": 1,
    "blocked": 1,
    "today_total": 4
  },
  "risk": {
    "score": 42.0,
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
      "at": 1793463405.7415075,
      "count": 0
    },
    {
      "at": 1793463465.7415075,
      "count": 0
    },
    {
      "at": 1793463525.7415075,
      "count": 0
    },
    {
      "at": 1793463585.7415075,
      "count": 0
    },
    {
      "at": 1793463645.7415075,
      "count": 0
    },
    {
      "at": 1793463705.7415075,
      "count": 0
    },
    {
      "at": 1793463765.7415075,
      "count": 0
    },
    {
      "at": 1793463825.7415075,
      "count": 0
    },
    {
      "at": 1793463885.7415075,
      "count": 0
    },
    {
      "at": 1793463945.7415075,
      "count": 0
    },
    {
      "at": 1793464005.7415075,
      "count": 0
    },
    {
      "at": 1793464065.7415075,
      "count": 0
    },
    {
      "at": 1793464125.7415075,
      "count": 0
    },
    {
      "at": 1793464185.7415075,
      "count": 0
    },
    {
      "at": 1793464245.7415075,
      "count": 0
    },
    {
      "at": 1793464305.7415075,
      "count": 0
    },
    {
      "at": 1793464365.7415075,
      "count": 0
    },
    {
      "at": 1793464425.7415075,
      "count": 0
    },
    {
      "at": 1793464485.7415075,
      "count": 0
    },
    {
      "at": 1793464545.7415075,
      "count": 0
    },
    {
      "at": 1793464605.7415075,
      "count": 0
    },
    {
      "at": 1793464665.7415075,
      "count": 0
    },
    {
      "at": 1793464725.7415075,
      "count": 0
    },
    {
      "at": 1793464785.7415075,
      "count": 0
    },
    {
      "at": 1793464845.7415075,
      "count": 0
    },
    {
      "at": 1793464905.7415075,
      "count": 0
    },
    {
      "at": 1793464965.7415075,
      "count": 0
    },
    {
      "at": 1793465025.7415075,
      "count": 0
    },
    {
      "at": 1793465085.7415075,
      "count": 0
    },
    {
      "at": 1793465145.7415075,
      "count": 4
    }
  ],
  "risk_trend": [
    {
      "at": 1793463345.7415075,
      "score": 0.0
    },
    {
      "at": 1793463405.7415075,
      "score": 0.0
    },
    {
      "at": 1793463465.7415075,
      "score": 0.0
    },
    {
      "at": 1793463525.7415075,
      "score": 0.0
    },
    {
      "at": 1793463585.7415075,
      "score": 0.0
    },
    {
      "at": 1793463645.7415075,
      "score": 0.0
    },
    {
      "at": 1793463705.7415075,
      "score": 0.0
    },
    {
      "at": 1793463765.7415075,
      "score": 0.0
    },
    {
      "at": 1793463825.7415075,
      "score": 0.0
    },
    {
      "at": 1793463885.7415075,
      "score": 0.0
    },
    {
      "at": 1793463945.7415075,
      "score": 0.0
    },
    {
      "at": 1793464005.7415075,
      "score": 0.0
    },
    {
      "at": 1793464065.7415075,
      "score": 0.0
    },
    {
      "at": 1793464125.7415075,
      "score": 0.0
    },
    {
      "at": 1793464185.7415075,
      "score": 0.0
    },
    {
      "at": 1793464245.7415075,
      "score": 0.0
    },
    {
      "at": 1793464305.7415075,
      "score": 0.0
    },
    {
      "at": 1793464365.7415075,
      "score": 0.0
    },
    {
      "at": 1793464425.7415075,
      "score": 0.0
    },
    {
      "at": 1793464485.7415075,
      "score": 0.0
    },
    {
      "at": 1793464545.7415075,
      "score": 0.0
    },
    {
      "at": 1793464605.7415075,
      "score": 0.0
    },
    {
      "at": 1793464665.7415075,
      "score": 0.0
    },
    {
      "at": 1793464725.7415075,
      "score": 0.0
    },
    {
      "at": 1793464785.7415075,
      "score": 0.0
    },
    {
      "at": 1793464845.7415075,
      "score": 0.0
    },
    {
      "at": 1793464905.7415075,
      "score": 0.0
    },
    {
      "at": 1793464965.7415075,
      "score": 0.0
    },
    {
      "at": 1793465025.7415075,
      "score": 0.0
    },
    {
      "at": 1793465085.7415075,
      "score": 0.0
    },
    {
      "at": 1793465145.7415075,
      "score": 42.0
    }
  ],
  "recent": [
    {
      "id": "8bb4b81f-190d-48fe-acec-d544ba17d10b",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793465145.7184343,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 55,
      "decision": "DENY",
      "expires_at": 1793466045.7184343,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "1c1273d5-7ce4-4efd-a538-49a720c41db7",
      "request_id": "8bb4b81f-190d-48fe-acec-d544ba17d10b",
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
        "engine": "db-security-rules-v1",
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
        "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "fictional_sqlite_lab",
      "execution_id": "e93526f3-d7fd-4e57-96d1-411742ad1fb7",
      "receipt_id": null
    },
    {
      "id": "5bfaf593-e291-42c0-b5ad-ea3a7c60b433",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793465145.7114353,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 40,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793466045.7114353,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "987258f0-d923-4c99-a76b-a441a42f689a",
      "request_id": "5bfaf593-e291-42c0-b5ad-ea3a7c60b433",
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
        "engine": "db-security-rules-v1",
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
        "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "fictional_sqlite_lab",
      "execution_id": "5fcb0b09-36ce-490f-ad44-78106dbfc092",
      "receipt_id": null
    },
    {
      "id": "8b4739d3-5e09-4d9e-a475-5faee41b7998",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793465145.6790197,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 70,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793466045.6790197,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "e84a0bf5-5ef5-4a87-b4b3-2d9dbca483bf",
      "request_id": "8b4739d3-5e09-4d9e-a475-5faee41b7998",
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
        "engine": "db-security-rules-v1",
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
        "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
      },
      "dataset_name": "급여·정산 정보",
      "database_name": "사내 검증 DB",
      "mode": "fictional_sqlite_lab",
      "execution_id": "a10315ad-5562-4ff3-9af4-690085ee6515",
      "receipt_id": null
    },
    {
      "id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793465145.606736,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 15,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793466045.606736,
      "reviewer": "reviewer-demo",
      "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
      "decided_at": 1793465145.6147366,
      "result_count": 25,
      "trace_id": "14731f2f-1eaa-47d4-aa5d-a91e0da1be3a",
      "request_id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
      "state": "SUCCEEDED",
      "arguments": {
        "dataset_id": "operations",
        "columns": [
          "ticket_id",
          "status"
        ],
        "filters": {},
        "row_limit": 25,
        "purpose": "승인 기반 DB 조회 통합 검증입니다."
      },
      "analysis": {
        "engine": "db-security-rules-v1",
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
        "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
      },
      "dataset_name": "운영 지원 이력",
      "database_name": "사내 검증 DB",
      "mode": "fictional_sqlite_lab",
      "execution_id": "c7f4a9f1-a8b0-4bcd-bc35-1bc1f4c95100",
      "receipt_id": "receipt-74631052-494b-40ca-be5f-9099ba7dd585"
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
    "id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793465145.606736,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 15,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793466045.606736,
    "reviewer": "reviewer-demo",
    "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
    "decided_at": 1793465145.6147366,
    "result_count": 25,
    "trace_id": "14731f2f-1eaa-47d4-aa5d-a91e0da1be3a",
    "request_id": "f8ab1a7e-92bc-4cb2-9e21-b5d194d321e3",
    "state": "SUCCEEDED",
    "arguments": {
      "dataset_id": "operations",
      "columns": [
        "ticket_id",
        "status"
      ],
      "filters": {},
      "row_limit": 25,
      "purpose": "승인 기반 DB 조회 통합 검증입니다."
    },
    "analysis": {
      "engine": "db-security-rules-v1",
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
      "limitations": "설명 가능한 정책·행위 규칙 분석이며 학습형 LLM 확률 또는 침해 확률이 아닙니다."
    },
    "dataset_name": "운영 지원 이력",
    "database_name": "사내 검증 DB",
    "mode": "fictional_sqlite_lab",
    "execution_id": "c7f4a9f1-a8b0-4bcd-bc35-1bc1f4c95100",
    "receipt_id": "receipt-74631052-494b-40ca-be5f-9099ba7dd585",
    "approval_binding": {
      "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
      "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5",
      "policy_hash": "5d8b2bea056f668d7f1c6a868b38b0cd484735eb9f492f2ce157d978ac3da4b8"
    },
    "timeline": [
      {
        "at": 1793465145.608736,
        "actor": "agent-alice",
        "event": "DB_REQUESTED",
        "details": {
          "dataset_id": "operations",
          "decision": "REQUIRE_APPROVAL",
          "risk_score": 15,
          "source_ip": "127.0.0.1",
          "request_hash": "4e40dfbb3dd93669a66a151485af0a72f17fae69a722df51d17532a54d67d7bd",
          "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5"
        }
      },
      {
        "at": 1793465145.6147366,
        "actor": "reviewer-demo",
        "event": "DB_APPROVED",
        "details": {
          "reason": "업무 범위와 열·조회량을 확인했습니다.",
          "snapshot_hash": "c9c524b1ef038d2ad9ab1f0761e30dcb90a6fbd196cbf9fe62b6a722bba2a6a5"
        }
      },
      {
        "at": 1793465145.622735,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_STARTED",
        "details": {
          "execution_id": "c7f4a9f1-a8b0-4bcd-bc35-1bc1f4c95100"
        }
      },
      {
        "at": 1793465145.6357358,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_SUCCEEDED",
        "details": {
          "row_count": 25,
          "receipt_id": "receipt-74631052-494b-40ca-be5f-9099ba7dd585"
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
  "checked_at": 1793465145.7606406,
  "passed": true,
  "checks": [
    {
      "name": "게이트웨이",
      "passed": true,
      "detail": "ready",
      "latency_ms": 0.92
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
      "detail": "검증용 SQLite DB 읽기 연결 정상",
      "latency_ms": 1.58
    },
    {
      "name": "감사 DB",
      "passed": true,
      "detail": "감사 기록 저장소 연결됨",
      "latency_ms": 0.17
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
          "action_id": "22a66a8e-93e5-4698-aae2-83e838bf5693",
          "decision": "ALLOW",
          "state": "SUCCEEDED",
          "reason_codes": [],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "87fbc580-6a26-4a58-848b-cac7e9df6e8f",
          "trace_id": "392e96f0-4fa3-49e4-8bd9-1c639d859a81",
          "policy_version": "demo-v2",
          "result": {
            "receipt_id": "receipt-f0162f92-8128-4456-8c10-c94283bf6e69",
            "execution_id": "87fbc580-6a26-4a58-848b-cac7e9df6e8f",
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
          "action_id": "230da6af-4350-4132-9497-5e43312dbce5",
          "decision": "DENY",
          "state": "DENIED",
          "reason_codes": [
            "RESOURCE_OUT_OF_SCOPE"
          ],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "bc03f8f1-371a-4754-b1a0-4fb1998f25a2",
          "trace_id": "1383c4ad-bd22-4194-8b9c-3b6d0354ee37",
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
          "inspection_id": "33c6fcd0-d67e-49dc-a20e-b1145e4dbe03",
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
          "inspection_id": "9fb122e7-8ef7-4b9b-8a90-f832e4e727a5",
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
          "action_id": "e1f7904f-6b84-4489-92f8-e9496ba05e3a",
          "decision": "REQUIRE_APPROVAL",
          "state": "PENDING_APPROVAL",
          "reason_codes": [],
          "approval_id": "8bb76bc0-1a2c-4995-a49e-808f9f183dfd",
          "approval_state": "PENDING",
          "execution_id": "28e301c8-cf9c-4588-946c-c686bcd13f19",
          "trace_id": "7876746e-1770-4b9a-b76b-7624984eb193",
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
          "latest_chain_hash": "783772d44d32abd93bf02bcd87c7fc28a2b3010588866e205cfe9e73c7a3517b"
        },
        "mitre": "T1562 (Impair Defenses / Audit Tampering)",
        "severity": "INFO"
      }
    }
  },
  "binary": {
    "sha256": "dea844b4aeb1041ad7e903d031e25c2e7da8cf233885c0acb7103676a720d7e6",
    "bytes": 10641007
  }
}
```

### T30. 독립 EXE의 DB 요청·분석·작동 진단

- 예상 결과: 정상·민감·대량은 승인 대기, 비정상은 차단, 진단 통과
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "scenarios": {
    "normal": {
      "http": 200,
      "state": "PENDING_APPROVAL",
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
    "checked_at": 1793465154.0637705,
    "passed": true,
    "checks": [
      {
        "name": "게이트웨이",
        "passed": true,
        "detail": "ready",
        "latency_ms": 0.88
      },
      {
        "name": "보안 에이전트",
        "passed": true,
        "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
        "latency_ms": 0.21
      },
      {
        "name": "보호 DB",
        "passed": true,
        "detail": "검증용 SQLite DB 읽기 연결 정상",
        "latency_ms": 1.49
      },
      {
        "name": "감사 DB",
        "passed": true,
        "detail": "감사 기록 저장소 연결됨",
        "latency_ms": 0.13
      },
      {
        "name": "감사 로그 무결성",
        "passed": true,
        "detail": "14개 해시 연결 검증, 변조 의심 0건"
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

### 미실행 범위

- Docker 다중 네트워크 격리·PostgreSQL 실동작: NOT_RUN
- 외부 LLM 및 외부 데이터셋 평가: NOT_RUN
- 코드 서명·다른 Windows PC 실행: NOT_RUN

### 재현과 증거

- 단계별 설명: [TEST_GUIDE.md](TEST_GUIDE.md)
- 구조화 결과: [results.json](results/latest/results.json)
- 회귀 테스트 로그: [unittest.log](results/latest/unittest.log)
- 감사 이벤트: [audit-events.json](results/latest/audit-events.json)
- 실행파일 로그: [exe-smoke.log](results/latest/exe-smoke.log)
- 테스트는 별도 임시 디렉터리를 사용하며 사용자 실행 데이터는 삭제하지 않습니다.

<!-- ASG_RESULT_END -->
