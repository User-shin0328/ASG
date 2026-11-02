# PostgreSQL 연결 실제 검증 결과

- 판정: **PASS**
- 시작: 2026-11-02T17:51:22.096272+09:00
- 임시 PostgreSQL 17.11, 가상 데이터, 게이트웨이 감사 DB와 보호 DB 분리. 운영 DB 미접속.

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
| 보호 DB 행 보존 | PASS |

관찰값: [results.json](results.json)

운영 인증서 배포·사내 DB·기업 IdP·Docker 네트워크 격리는 이 결과의 검증 범위가 아닙니다.
