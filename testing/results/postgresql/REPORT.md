# PostgreSQL 연결 실제 검증 결과

- 판정: **PASS**
- 시작: 2026-11-04T00:03:24.017027+09:00
- 임시 PostgreSQL 17.11, 게이트웨이 감사 DB와 보호 DB 분리. 운영 DB 미접속.

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
| 명시적 자동 정책으로 실제 PostgreSQL 조회 | PASS |
| 독립 PostgreSQL 연결의 누적 예산 경쟁 | PASS |
| 범위 승인 마지막 횟수의 PostgreSQL 경쟁 | PASS |
| 다른 게이트웨이 연결에서도 취소가 즉시 적용 | PASS |
| 응답 유실 예약과 만료 후 영수증 대조 | PASS |
| 자동 허용 40건을 사람 검토 없이 실행 | PASS |
| 다중 연결 처리 후 감사 해시 체인 | PASS |
| 보호 DB 행 보존 | PASS |

## 1. 게이트웨이 감사 DB와 보호 DB의 실제 PostgreSQL 연결

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "version": "17.11",
  "target": {
    "backend": "postgresql",
    "id": "pg-functional-v1"
  },
  "items": [
    {
      "key": "gateway",
      "name": "게이트웨이",
      "status": "up",
      "detail": "ready",
      "checked_at": 1793718207.1046708,
      "latency_ms": 2.38
    },
    {
      "key": "security_agent",
      "name": "보안 에이전트",
      "status": "up",
      "engine": "db-security-rules-v2",
      "checked_at": 1793718207.105208,
      "last_analysis_at": null,
      "latency_ms": 0.5,
      "detail": "정상·정책 위반 입력 분석 자체 점검 통과"
    },
    {
      "key": "protected_db",
      "name": "보호 DB",
      "status": "up",
      "detail": "PostgreSQL 읽기 전용 연결·등록 대상 권한 정상",
      "checked_at": 1793718207.1658163,
      "latency_ms": 60.73
    },
    {
      "key": "audit_db",
      "name": "감사 DB",
      "status": "up",
      "detail": "감사 기록 저장소 연결됨",
      "checked_at": 1793718207.1677842,
      "latency_ms": 1.97
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
  "row_count": 2,
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
      "latency_ms": 1.69
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
      "latency_ms": 44.11
    },
    {
      "name": "감사 DB",
      "passed": true,
      "detail": "감사 기록 저장소 연결됨",
      "latency_ms": 1.02
    },
    {
      "name": "감사 로그 무결성",
      "passed": true,
      "detail": "11개 해시 연결 검증, 변조 의심 0건"
    }
  ]
}
```

## 14. 명시적 자동 정책으로 실제 PostgreSQL 조회

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "state": "SUCCEEDED",
  "authorization": {
    "mode": "automatic",
    "rule_id": "operations-basic-v1",
    "role": "report-submitter"
  },
  "rows": 2
}
```

## 15. 독립 PostgreSQL 연결의 누적 예산 경쟁

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "statuses": [
    200,
    429
  ],
  "used": {
    "used_calls": 1,
    "used_rows": 2,
    "window_seconds": 1800,
    "max_calls": 1000,
    "max_rows": 3
  }
}
```

## 16. 범위 승인 마지막 횟수의 PostgreSQL 경쟁

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "statuses": [
    200,
    429
  ],
  "usage": {
    "calls": 1,
    "rows": 1
  }
}
```

## 17. 다른 게이트웨이 연결에서도 취소가 즉시 적용

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": 403,
  "error": "SCOPE_GRANT_INVALID"
}
```

## 18. 응답 유실 예약과 만료 후 영수증 대조

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "initial_status": 503,
  "reserved_rows": 2,
  "reconciled_rows": 2
}
```

## 19. 자동 허용 40건을 사람 검토 없이 실행

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "requests": 40,
  "success": 40,
  "elapsed_seconds": 3.244,
  "concurrency": 8,
  "note": "기능 검증 부하이며 운영 처리량 보증이 아닙니다."
}
```

## 20. 다중 연결 처리 후 감사 해시 체인

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "status": "VALID",
  "records": 196
}
```

## 21. 보호 DB 행 보존

- 실제 판정: **PASS**
- 실제 관찰값:

```json
{
  "rows_after_all_checks": 4
}
```

관찰값: [results.json](results.json)

운영 인증서 배포·사내 DB·기업 IdP·Docker 네트워크 격리는 이 결과의 검증 범위가 아닙니다.
