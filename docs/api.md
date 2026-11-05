# DB 접근 API

Bearer 토큰으로 인증하며 신원·역할·테넌트는 서버가 결정합니다. 브라우저 프록시 POST에는 같은 Origin과 X-ASG-Request: 1이 필요합니다.

| API | 권한 | 내용 |
|---|---|---|
| POST /v1/db/requests | agent | 등록된 dataset_id/columns/filters/row_limit/purpose. 자동 허용 200, 검토 202, 차단 403 |
| GET /v1/db/requests/{id} | 본인 agent / 같은 tenant reviewer | 메타데이터·분석·허용 방식·처리 이력 |
| GET /v1/db/recovery?page=1 | 본인 agent | 날짜와 무관한 미완료 요청 복원, 50개씩. 현재 유효한 대기·승인과 UNKNOWN/EXECUTING |
| POST /v1/db/requests/{id}/execute | 원래 agent | 본문 {}. 현재 정책·승인·누적 예산 검사 후 실제 조회 |
| POST /v1/db/requests/{id}/decision | reviewer | decision, reason. 선택적 scope_grant로 반복 승인 |
| POST /v1/db/requests/{id}/reconcile | reviewer | 본문 {}. 결과 불명 실행의 저장된 영수증만 대조, 결과 행 미반환 |
| GET /v1/db/grants | reviewer | 같은 tenant의 최근 100개 반복 승인과 사용량 |
| POST /v1/db/grants/{id}/revoke | reviewer | reason. 취소 후 새 실행·캐시 재조회 거부 |
| GET /v1/db/budgets | reviewer | 같은 tenant의 신원별 실행 횟수·누적 행 수 |
| GET /v1/db/requests | reviewer | pending/date/sort/page 목록 |
| GET /v1/db/overview | reviewer | 일일 집계·30분 위험도 |
| POST /v1/db/diagnostics | reviewer | 실제 작동 점검 |

반복 승인 예시: `{"decision":"approve","reason":"업무 범위를 확인했습니다.","scope_grant":{"ttl_seconds":600,"max_calls":20,"max_total_rows":2000}}`.

전역·범위 예산 초과는 429, 승인 만료·미승인은 409, 실행 범위·정책 변경은 403으로 거부합니다. 거부된 요청을 수정하려면 새 요청을 제출합니다.

기존 문서·요약 저장·모의 전송함 도구 API는 유지합니다. 모델 추론 API는 제공하지 않습니다.

요청 길이·전송 방식 위반은 400, 본문 초과는 413, 본문 제한시간 초과는 408입니다. 헤더·본문 각각 기본 3초, 서버당 동시 연결 기본 32개이며 용량 초과 연결은 503입니다. 자세한 재현·예상·실제 결과는 [1~4번 수정 보고서](FIXES_1_TO_4.md)를 확인하세요.
