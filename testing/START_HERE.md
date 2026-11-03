# 지금 테스트 시작하기

2026-11-03. 준비한 환경은 **가상 데이터 PostgreSQL**이며 실제 사내 DB가 아닙니다.

- 대시보드: http://127.0.0.1:18863
- 가상 데이터: 운영 이력 2,400행·연락처 200행·급여 100행.
- 기동 점검: 게이트웨이·보안 에이전트·보호 DB·감사 DB·감사 무결성 모두 통과.
- 기존 테스트 이력을 보존했으므로 처음부터 위험도·사용량·감사 기록이 0일 필요는 없습니다.
- 준비 상태의 기동 점검은 로컬 `testing/.runtime/postgresql-validation/manual-ready.json`에 저장했습니다. 포트·실행 프로세스는 같은 폴더의 `lab/session.json`이 기준입니다.

## 1. 화면과 자동 허용 확인

1. 대시보드 왼쪽 **작동 테스트**에서 **전체 작동 점검**을 누릅니다. 모든 항목이 정상이어야 합니다.
2. 같은 페이지에서 일반 요청을 생성합니다. **자동 허용**이어야 하며 승인 검토 대기 목록에 나타나지 않습니다.
3. 민감 또는 대량 요청을 생성합니다. **승인 대기**이며 승인 검토에서 열 수 있어야 합니다.
4. 비정상 요청을 생성합니다. **차단**이어야 하며 사람이 허용으로 바꿀 수 없습니다.

화면에서 요청을 생성하는 것과 실제 데이터를 받는 것은 별도입니다. ‘허용’은 아직 조회 완료를 뜻하지 않습니다. 실제 SQL과 예산 차감은 다음 절에서 확인합니다.

## 2. 실제 에이전트가 25행 받기

프로젝트 루트에서 새 PowerShell을 열고 실행합니다. 아래 로컬 토큰 파일은 이번 준비에서 만들거나 재사용했으며 Git에는 포함하지 않았습니다. 값을 화면에 출력할 필요가 없습니다.

```powershell
$TestLab = Get-Content 'testing/.runtime/postgresql-validation/lab/session.json' -Raw | ConvertFrom-Json
$env:GATEWAY_URL = $TestLab.gateway
$env:AGENT_ALICE_TOKEN = (Get-Content 'testing/.runtime/postgresql-validation/agent-token.txt' -Raw).Trim()
.\.venv\Scripts\python.exe -m demo_agent.db_client --row-limit 25
```

예상 결과는 접수 HTTP 200, 자동 허용, 실행 SUCCEEDED와 가상 운영 이력 최대 25행입니다. 승인 검토의 누적 예산에는 실제 반환량과 1회가 반영됩니다.

## 3. 사람이 반복 업무 승인하기

같은 PowerShell에서 다음 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m demo_agent.db_client --row-limit 25 --columns ticket_id description
```

1. description은 자동 허용 열이 아니므로 HTTP 202로 대기합니다. 클라이언트 창은 열어 둡니다.
2. 브라우저의 승인 검토에서 해당 요청을 열어 주체·목적·열·행 수·분석을 읽습니다.
3. 반복 업무 승인을 선택하고 10분·20회·2,000행과 판단 근거를 입력해 승인합니다.
4. 클라이언트가 실제 데이터를 받고 종료하는지, 보고서와 사용량이 갱신되는지 확인합니다.
5. 위 명령을 다시 실행합니다. 동일 범위와 남은 한도 안에서는 추가 사람 승인 없이 조회됩니다.
6. 승인 검토 하단에서 해당 반복 승인을 취소합니다. 사용 기록은 남고, 이후 같은 description 명령은 다시 사람 검토를 기다립니다.

취소는 그 반복 승인에 적용됩니다. 기본 자동 정책에 해당하는 일반 조회까지 취소하는 것은 아닙니다. 기존 미실행 요청의 만료, 빈도·누적 예산 초과 등이 있으면 화면의 실제 근거를 먼저 확인하세요.

## 4. 감사와 자동 검증

감사 기록에서 오늘 날짜를 선택하고 요청 보고서를 열어 요청자·출처·분석·승인·실행·취소를 확인합니다. 보고서는 반환 행 본문을 검토자에게 보여주지 않습니다.

전체 자동 재검증은 **같은 DB의 대시보드를 종료한 뒤** 실행해야 합니다.

```powershell
.\testing\run_tests.ps1
.\.venv\Scripts\python.exe -m testing.postgresql_checks --keep-db --reuse --policy-controls
```

예상 결과는 로컬·실행파일 31단계(회귀 118개 포함), 보존형 PostgreSQL 32단계 PASS입니다. 가상 데이터를 재시드하거나 기존 감사 기록을 삭제하지 않습니다. 상세 예상값·실제 보고서·문제 해결은 [TEST_GUIDE.md](TEST_GUIDE.md)와 [VALIDATION_DB_GUIDE.md](VALIDATION_DB_GUIDE.md)를 따릅니다.

## 5. 중지와 다시 시작

현재 대시보드는 창을 띄우지 않는 별도 프로세스로 실행했습니다. 중지할 때는 기록된 PID와 명령을 확인합니다.

```powershell
$TestSession = Get-Content 'testing/.runtime/postgresql-validation/lab/session.json' -Raw | ConvertFrom-Json
$TestProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($TestSession.pid)"
if ($TestProcess -and $TestProcess.Name -match '^python' -and $TestProcess.CommandLine -like '*testing.validation_dashboard*') {
    Stop-Process -Id $TestSession.pid
}
```

이후 같은 토큰으로 다시 시작하려면 다음을 실행합니다. 이때는 실행한 콘솔에서 Ctrl+C로 종료할 수 있습니다. DB와 볼륨은 남습니다.

```powershell
$env:ASG_LAB_ALICE_TOKEN = (Get-Content 'testing/.runtime/postgresql-validation/agent-token.txt' -Raw).Trim()
.\.venv\Scripts\python.exe -m testing.validation_dashboard
```

새 PC에는 로컬 DB·비밀 파일이 전달되지 않습니다. 새 환경 구축은 [검증 DB 설명서](VALIDATION_DB_GUIDE.md)의 최초 생성 절차부터 수행하세요.
