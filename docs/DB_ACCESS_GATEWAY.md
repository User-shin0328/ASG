# DB 접근 게이트웨이: 판단 근거·승인·위험도·연동

## 1. 구조에 대한 판단

요청한 **사내 에이전트 → 보안 에이전트 분석 → 사람 승인 → DB 조회** 구조를 채택했습니다. 다만 보안 에이전트의 추천이 실제 접근 권한을 생성하지 않도록 역할을 나눴습니다.

보안 에이전트는 요청한 대상·열·조회량·목적과 최근 요청 빈도를 분석합니다. 게이트웨이가 인증·테넌트·역할·등록된 조회 범위·승인 스냅샷·만료·실행 중복을 강제합니다. 검토자는 분석 근거와 추천 대응을 읽고 이유를 남겨 승인하거나 거절합니다. 실제 DB 조회는 원래 요청한 에이전트의 별도 실행 요청으로 수행합니다.

판단 근거는 명확합니다. 분석 내용이 바뀌거나 오류가 나더라도 그것만으로 조회가 실행되어서는 안 됩니다. 사용자에게 승인받은 열·필터·조회량이 실행 때 달라지는 것도 막아야 합니다. 따라서 모든 유효 DB 조회는 사람 승인이 필요하고, 정책 위반은 사람이 승인으로 덮어쓸 수 없습니다. 범위를 바꾸려면 새 요청을 제출합니다.

현재 보안 에이전트는 `security_agent/assessment.py`의 **설명 가능한 정책·행위 규칙 엔진**입니다. 실제로 실행되는 분석기이며, LLM을 연결했다고 표시하지 않습니다. 사내 데이터와 연결 정보가 제공되지 않았으므로 보호 DB는 가상 데이터가 담긴 실제 SQLite 검증 DB입니다. 실제 사내 DB 연결과 기업 IdP 연동은 완료했다고 주장하지 않습니다.

## 2. 정책 결정의 뜻

| 표현 | 의미 |
|---|---|
| 승인 대기 | 구조·권한 검사를 통과했지만 사람이 아직 결정하지 않은 유효 요청 |
| 허용 | 사람이 승인한 요청. 실행 대기·실행 중·조회 완료·결과 확인 필요를 포함 |
| 차단 | 등록 범위 위반, 잘못된 요청, 검토자 거절 또는 승인 만료 |
| 오늘 DB 조회 요청 | 한국 시간 오늘 접수된 DB 조회 요청 수. 실제 반환 행 수가 아님 |

화면의 `YY.MM.DD HH:mm 기준`은 서버가 계산한 기준 시각입니다. 오늘 접수 건만 대기·허용·차단으로 나누므로 세 항목의 합이 오늘 요청 수와 일치합니다. 승인 검토 메뉴의 수는 날짜와 관계없이 현재 유효한 전체 대기 요청입니다.

## 3. 허용하는 DB 요청 범위

임의 SQL은 받지 않습니다. 클라이언트는 서버에 등록된 데이터 ID, 열, 필터와 최대 행 수만 요청합니다. 테이블 이름은 서버 코드가 결정하고 필터 값은 SQL 매개변수로 전달합니다. SQL 작성, DDL/DML, 와일드카드, 등록되지 않은 열, 다른 테넌트 정보는 허용하지 않습니다.

| 데이터 ID | 내용 | 예시 열 | 범위 |
|---|---|---|---|
| `operations` | 가상 운영 지원 이력 | ticket_id, category, status, description | north/south 각자의 행 |
| `employee-directory` | 가상 업무 연락처 | employee_id, name, department, work_email | 허용 역할·테넌트 |
| `payroll` | 가상 급여·정산 | employee_id, department, salary, bank_account | north의 report-submitter |

한 번의 조회는 최대 5,000행, 1,000행 이상은 대량 요청입니다. 현재 검증 데이터의 실제 행 수가 이보다 작으면 요청량보다 적게 반환합니다. 요청량과 반환량을 구분해 기록합니다. `example.test`, `MOCK-ACCOUNT` 등은 가상 데이터입니다.

## 4. 30분 위험도

각 요청이 최근 30분 동안 지표에 기여합니다.

```text
요청 기여도 = (민감정보 여부×12 + 대량조회 여부×10 + 비정상 여부×20)
              × max(0, 1 - 경과초/1800)
현재 위험도 = min(100, 최근 30분 요청 기여도의 합)
```

- 민감정보: 카탈로그가 sensitive/restricted로 분류한 열을 요청
- 대량조회: 요청 최대 행 수가 1,000 이상
- 비정상: 등록되지 않은 대상·열, 잘못된 형식·범위, 의심 지시, 요청 급증 또는 대기 한도 초과
- 비정상 빈도: 같은 에이전트가 최근 1분 10건 이상 요청하면 표시, 30건 이상이면 차단
- 세 조건은 중복 적용됩니다. 모두 해당하면 최초 42점, 15분 후 21점, 30분 후 0점입니다.
- 정상적인 소량 요청만 있으면 0점일 수 있습니다. 0점은 모든 위협이 없다는 보증이 아닙니다.

현재 위험도 구간은 30점 미만 낮음, 30~69.9점 주의, 70점 이상 높음입니다. 표시되는 값은 운영 지표이고 침해 확률이나 AI 모델의 신뢰도가 아닙니다. 아직 인증되지 않은 외부 트래픽 전체를 탐지·집계하는 IDS는 아닙니다.

승인 목록의 **개별 요청 위험도**는 별도 값입니다. 기본 15점에 민감 열 35점(급여·계좌 등 restricted 열은 55점), 대량 조회 25점, 비정상 40점을 가산하고 100점으로 제한합니다. 개별 요청 점수는 당시 분석 근거로 보존하고, 메인 화면의 시간 감쇠 지표는 현재 시각에 재계산합니다.

## 5. 승인과 실행의 결합

- 요청자의 서버 소유 principal·tenant·task, 정규화된 요청, 분석 결과, 정책·카탈로그 버전을 해시로 묶습니다.
- 승인 전에 요청 내용이 바뀌면 승인할 수 없습니다.
- 승인 후 인자·분석·정책이 바뀌면 실행을 거부합니다.
- 승인 만료는 기존 정책의 `approval_seconds`를 사용하며 기본 900초입니다.
- 승인과 거절은 원자적으로 한 번만 결정됩니다. 에이전트 토큰으로는 승인할 수 없습니다.
- 조회 실행은 원래 요청자만 할 수 있습니다. 같은 실행 ID의 재요청은 기존 영수증을 반환합니다.
- 분석 오류는 차단으로 기록합니다. 사람의 결정에는 3~1,000자의 판단 근거가 필요합니다.
- 승인만 클릭했을 때 DB 결과가 조회되지 않습니다. 에이전트가 별도로 execute를 호출합니다.

## 6. 저장소와 감사 보고서

게이트웨이 DB에 `db_access_requests`와 `db_access_events`를 추가했습니다. 전자는 요청·분석·승인·실행 상태, 후자는 추가 전용 처리 이력을 저장합니다. 기존 해시 체인 감사에도 DB 요청 이벤트를 연결합니다. SQLite에서는 자동으로 추가하며, PostgreSQL용 스키마는 `migrations/003_db_access.sql`입니다.

기록은 재시작 후에도 보존됩니다. 감사 조회는 검토자의 테넌트 범위와 한국 시간 자정~다음 자정으로 제한하고 50건 단위 페이지를 제공합니다. 이전 화면의 최근 200건 제한에 의존하지 않습니다. 보고서는 언제·어디서·누가·어느 데이터의 무엇을·어떤 목적으로 요청했는지, 분석 근거·추천 대응·판단 사유·실행 결과·처리 이력을 보여줍니다. 실제 조회된 행 본문은 보고서에 포함하지 않습니다.

`source_ip`는 게이트웨이가 관찰한 접속 IP입니다. 프록시나 로컬 시뮬레이터를 통하면 해당 프록시/루프백 IP가 나타납니다. 클라이언트가 임의로 보낸 X-Forwarded-For를 신뢰하지 않습니다.

## 7. API

인증된 에이전트는 bearer 토큰으로 요청하며, 클라이언트가 자기 역할이나 테넌트를 지정할 수 없습니다.

```http
POST /v1/db/requests
Authorization: Bearer <agent token>
Idempotency-Key: <unique request key>
Content-Type: application/json

{"dataset_id":"operations","columns":["ticket_id","status"],"filters":{},"row_limit":25,"purpose":"월간 운영 지원 현황 확인을 위한 조회입니다."}
```

| API | 권한 | 동작 |
|---|---|---|
| POST `/v1/db/requests` | agent | 분석 후 202 승인 대기 또는 403 차단 |
| GET `/v1/db/requests/{id}` | 본인 agent / 같은 tenant reviewer | 상세 보고서 |
| GET `/v1/db/requests?pending=true&sort=risk` | reviewer | 현재 대기 요청, 정렬 newest/oldest/risk |
| GET `/v1/db/requests?date=2026-10-31&page=1` | reviewer | 날짜별 감사 이력, 50건 단위 |
| POST `/v1/db/requests/{id}/decision` | reviewer | `{"decision":"approve","reason":"확인한 업무 필요성"}` 또는 reject |
| POST `/v1/db/requests/{id}/execute` | 원래 agent | 승인된 범위의 실제 SELECT, 본문 `{}` |
| GET `/v1/db/overview` | reviewer | 오늘 집계, 최근 30분 위험도와 추이 |
| GET `/v1/db/status` | reviewer | 실제 연결·분석 자체 점검 |
| POST `/v1/db/diagnostics` | reviewer | 원클릭 점검, 본문 `{}` |

브라우저 대시보드를 거치는 POST에는 같은 Origin과 `X-ASG-Request: 1`이 필요합니다. 직접 게이트웨이로 보내는 인증된 에이전트 API에는 브라우저용 자동 검토자 권한이 없습니다.

## 8. 사내 에이전트와 연결하는 검증 절차

토큰은 명령 인자나 보고서에 넣지 않고 환경 변수로 전달합니다. `ASG_LAB_ALICE_TOKEN`을 지정하면 로컬 실행기가 해당 비밀값을 사용합니다. 지정하지 않으면 메모리에서 무작위로 생성합니다. 토큰 네 개는 서로 달라야 하고 각각 32자 이상이어야 합니다.

```powershell
# 같은 PowerShell에서 검증 토큰 생성 및 실행. 값 자체를 출력하지 않습니다.
$LabTokenBytes = New-Object byte[] 36
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($LabTokenBytes)
$env:ASG_LAB_ALICE_TOKEN = [Convert]::ToBase64String($LabTokenBytes)
Start-Process -FilePath '.\ASG.exe' -ArgumentList '--dashboard-port','18512','--data-dir','testing/.runtime/agent-integration' -WindowStyle Hidden

# 실행이 준비된 뒤 session.json에서 실제 게이트웨이 주소 확인
$LabSession = Get-Content '.\testing\.runtime\agent-integration\session.json' -Raw | ConvertFrom-Json
$env:GATEWAY_URL = $LabSession.gateway
$env:AGENT_ALICE_TOKEN = $env:ASG_LAB_ALICE_TOKEN
.\.venv\Scripts\python.exe -m demo_agent.db_client --row-limit 25
```

브라우저에서 18512 포트의 승인 검토를 열어 내용을 확인하고 판단 근거를 입력해 승인합니다. 클라이언트가 APPROVED를 확인하면 별도 execute를 호출해 실제 검증 DB의 결과를 받습니다. 콘솔의 요청·결과 출력은 가상 검증 데이터입니다. 종료할 때는 직접 실행한 프로세스만 종료하고 환경 변수를 정리하세요.

위 토큰은 데모 principal `agent-alice`에 연결됩니다. 실제 임직원 신원·기업 IdP·사내 DB 계정이 연결된 것은 아닙니다. 운영 연동에는 실제 DB 종류·읽기 전용 계정·네트워크 경계·카탈로그·업무 역할을 정해야 합니다. 현재 동작 범위를 운영 DB 전체에 자동 확대하지 않습니다.

## 9. 작동 상태의 의미

초록불은 그 시각의 실제 연결 또는 분석 자체 점검 통과입니다. 빨간불은 점검 실패, 회색은 확인하지 못한 상태입니다. 보안 에이전트는 같은 게이트웨이 프로세스 안의 별도 분석 모듈이며, 별도 AI 모델 서버가 켜졌다고 표시하지 않습니다.

원클릭 점검은 게이트웨이 준비 상태, 정상/위반 샘플의 보안 분석, 보호 DB 읽기 연결, 감사 저장소와 해시 연결을 확인합니다. Docker 네트워크 격리·실제 사내 DB·외부 LLM은 이 점검의 성공으로 검증되었다고 보지 않습니다.

## 10. 현재 검증 근거

[통합 설명서](../testing/TEST_GUIDE.md)에는 재현 순서와 예상·실제 결과를 함께 기록합니다. [결과보고서](../testing/results/latest/REPORT.md)는 실제 소스 테스트와 독립 실행파일 검증을 포함합니다. 같은 빌드인지 SHA-256으로 확인할 수 있습니다.
