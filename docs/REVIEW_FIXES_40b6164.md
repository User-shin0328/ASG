# 40b6164 검토 사항 수정 결과

2026-11-04. 최신 커밋을 로컬에 반영한 뒤 검토에서 확인한 여섯 가지 사항을 수정했습니다. 기본 규칙 기반 권한 정책과 사람 승인 범위는 확대하지 않았습니다.

## 1. 위험도 등급 일치

게이트웨이의 30분 관제 위험도 응답에 `level`을 추가했습니다. 기존 대시보드의 기준인 30점 미만 ‘낮음’, 30점 이상 ‘주의’, 70점 이상 ‘높음’을 서버에서 계산합니다. 대시보드와 시뮬레이터가 이 값을 함께 사용합니다. 등급이 없는 응답은 ‘확인 불가’로 표시하며 ‘정상’을 추정하지 않습니다. 요청 하나의 분석 위험 등급과 30분 관제 등급은 서로 다른 수치입니다.

## 2. 실제 요청 결과만 안내

시나리오마다 HTTP·요청 ID·서버 상태를 확인하고 승인 대기, 정책 차단, 실행 확인 실패를 구분합니다. 조회 완료는 `SUCCEEDED`, 실행 영수증과 실제 반환량을 확인했을 때만 출력합니다. 대기열 한도로 차단된 민감 요청을 승인 대기로 안내하지 않습니다.

`--auto`는 초기 5개 시나리오의 예상 접수 상태와 정상 요청의 실제 조회 성공을 검사합니다. 실패하면 종료값 1과 FAIL 보고서를 남깁니다. 사람 승인 대기로 끝나는 민감·대량 시나리오를 실제 조회까지 완료했다고 주장하지 않습니다. 대화형 반복 실행은 현재 유효한 범위 승인이나 정책 차단 같은 실제 응답을 그대로 표시합니다.

## 3. 승인 뒤 오류 복구

처리 완료 표시는 실행 전에 저장하지 않습니다. 승인 대기 요청을 관찰하다가 승인되면 원래 에이전트 자격으로 실행합니다. 응답 유실 뒤에는 같은 요청의 상태를 다시 읽고, 결과가 불명이면 저장된 영수증 대조 API를 사용합니다. 대조는 새 SQL·새 승인·예약 환급을 수행하지 않습니다.

연속 확인 실패는 최대 3회입니다. 첫 실패 뒤 2초, 두 번째 실패 뒤 4초 간격을 두고 세 번째에도 실패하면 멈추고 확인 필요를 안내합니다. 메뉴의 `R`로 다시 확인할 수 있습니다. 영수증이 없으면 미확정 예약은 유지합니다. 거절·차단·만료는 감시에서 제거하며 프로그램 종료 시 감시 스레드를 종료·합류한 다음 서비스를 닫습니다.

실제 SQLite 도구의 SQL 실행 후 응답만 유실시키는 시험에서 **실제 조회 1회·반환 10행·차감 1회**를 유지한 채 저장된 영수증으로 완료 상태를 복구했습니다.

## 4. 보고서·로그를 같은 실행에 묶기

수용시험은 `testing/results/<실행 ID>/`에 독립된 결과를 만듭니다. 보고서·로그에 같은 실행 ID, 기준 Git 커밋, 수정된 작업 폴더 여부, 실행 소스 SHA-256을 기록하고 실제 시험한 실행파일 해시도 남깁니다. 회차 폴더와 latest의 깊이를 같게 유지해 보고서의 상대 링크도 두 위치에서 열립니다.

`manifest.json`은 보고서·로그·API 관찰값의 파일 해시를 묶습니다. 검증기는 로그의 실행 ID·소스 정보·시험 수·성공 여부와 JSON 보고서를 대조합니다. 같은 결과 폴더에 다른 회차 로그를 덮어쓰면 정합성 검사에 실패합니다. 여러 수용시험의 동시 쓰기도 잠금으로 막습니다.

Git에 게시하는 `testing/results/latest/`는 `.gitattributes`에서 줄바꿈 자동 변환을 끕니다. Windows의 CRLF가 다른 환경에서 LF로 바뀌어 증거 해시가 달라지지 않도록 원본 바이트를 보존합니다. 푸시 전에는 스테이징된 Git 원본으로 결과 폴더를 복원해 정합성을 다시 검사합니다.

검증을 마친 회차만 `latest`로 게시합니다. 이전 latest는 `history/previous-latest-…`에 보존하며 삭제하지 않습니다. 이전 커밋의 불일치 증거도 이 이력에 남습니다. 해시 검사는 자료의 정합성 확인이며 전자서명이나 외부 불변 저장소를 대체하지 않습니다.

```powershell
.\testing\run_tests.ps1
.\.venv\Scripts\python.exe -m testing.report_evidence
```

예상 결과는 전체 수용시험 PASS와 정합성 `VALID`입니다. 기준 커밋과 작업 폴더 수정 여부를 함께 보아야 하며, 미커밋 소스를 시험했다면 Git 커밋만으로 그 시험 소스를 식별했다고 판단하지 않습니다.

## 5. 테스트 순서 독립

가상 DB 테스트는 각 테스트마다 자기 환경을 만들고 정리합니다. 대시보드 집계 테스트는 필요한 정상·민감·대량·비정상·의심 지시문 요청을 직접 생성합니다. 전체 실행과 개별 선택 실행에 같은 전제 조건이 적용됩니다.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_virtual_agent_db.TestVirtualAgentAndDB.test_06_dashboard_shows_live_metrics_and_pending_requests -v
.\.venv\Scripts\python.exe -m unittest tests.test_simulation_reliability tests.test_report_evidence -v
```

별도 오류 회귀 테스트는 실제 시뮬레이터 함수를 호출합니다. 위험도 100점 표시, 통신 503, 실행 실패, 대기열 차단, 제한된 재확인, 종료 정리, 실제 유실 응답 복구와 보고서 혼합 검출을 확인합니다.

## 6. 승인 창 가독성

최대 폭은 720px로 조정하고 주요 본문은 14px, 결정 버튼은 최소 44px 높이로 키웠습니다. 모바일 검토 입력은 16px이며, 닫기 버튼이 세로로 줄바꿈되지 않도록 최소 폭과 줄바꿈 방지를 적용했습니다. 요청 해시와 기술 상세는 기존 접기 안에 유지했습니다.

1440·768·390px에서 반복 승인 입력란과 결정 버튼을 확인했습니다. 실제 측정은 본문 14px, 결정 버튼 높이 44px, 모바일 입력 16px, 모바일 가로 넘침 없음입니다. 처음 발견한 모바일 닫기 버튼 줄바꿈을 한 번 보완한 뒤 확인 검사를 마쳤습니다.

승인 목록 inspector는 세 폭 모두 0 FAIL이며 기존 보조 글씨와 빈 상태 패널의 여백 경고 2종을 남겼습니다. 보조 글씨는 기존 메타데이터이고 빈 패널은 데이터가 없음을 설명하는 상태입니다. 이를 승인 양식의 14/16px 측정과 혼동하지 않습니다. 기존 디자인 sidecar의 시점 차이는 재생성하지 않았습니다.

증거: `testing/screenshots/fixed-review-desktop.png`, `fixed-review-desktop-form.png`, `fixed-review-tablet.png`, `fixed-review-mobile-top.png`, `fixed-review-mobile.png`. 검사기 원본은 Git 제외 경로 `testing/.runtime/fix-ui-inspect/`에 보존했습니다.

## 결과와 재현

최종 실제 결과: **회귀 142개 PASS, 로컬 HTTP·독립 실행파일·소스 일치 32단계 PASS, 실제 임시 PostgreSQL 21단계 PASS, 보고서 정합성 VALID**. 기존 보존형 PostgreSQL의 운영 이력 2,400·연락처 200·급여 100행과 작동 점검 정상도 재확인했습니다. 보존형 DB의 32단계 전체를 이번 수정 후 다시 수행했다고 표현하지 않습니다.

- 전체 실제 결과: [테스트 설명서·보고서](../testing/TEST_GUIDE.md), [JSON 결과](../testing/results/latest/results.json), [증거 manifest](../testing/results/latest/manifest.json).
- 실제 PostgreSQL 기능 검증: [별도 보고서](../testing/results/postgresql/REPORT.md).
- 가상 요청 체험: 아래 명령 또는 기존 `tests/RUN_SIMULATION.bat`.

```powershell
.\.venv\Scripts\python.exe -m tests.virtual_agent_simulation --auto --no-browser
.\.venv\Scripts\python.exe -m tests.virtual_agent_simulation
```

시뮬레이터 관찰 결과는 `testing/results/simulation-latest.json`입니다. 기본 임시 SQLite 시뮬레이션은 종료 시 정리되며, 2,700행 보존형 PostgreSQL 검증 DB는 [별도 안내](../testing/VALIDATION_DB_GUIDE.md)를 사용합니다. 사내 DB·기업 IdP·운영 처리량을 검증한 결과로 확대하지 않습니다.
