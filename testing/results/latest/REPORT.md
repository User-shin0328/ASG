# ASG 실제 테스트 결과보고서

- 실행: 2026-11-03 10:13:50 ~ 10:14:37 (Asia/Seoul)
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

## T01. 기존·추가 회귀 테스트

- 예상 결과: 전체 테스트 성공
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "exit_code": 0,
  "tests": 118
}
```

## T02. 3개 서비스 준비 확인

- 예상 결과: 200 ready
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": "ready",
  "policy_version": "demo-v2"
}
```

## T03. 배정 문서 읽기

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
    "action_id": "4cbdca1c-3f4a-4898-81e9-b2d90a5ea704",
    "decision": "ALLOW",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": null,
    "approval_state": null,
    "execution_id": "39941eba-5288-42f8-a71c-14d93c697d0d",
    "trace_id": "f0e3cfe6-7362-4d64-aa35-5c501928fb22",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-baa3d01a-a43c-429f-b4c0-bb6f8c0cc5ad",
      "execution_id": "39941eba-5288-42f8-a71c-14d93c697d0d",
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

## T04. 테넌트 경계와 부작용

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
      "action_id": "9fa923fa-42de-415f-880f-b09c24f95d6e",
      "decision": "DENY",
      "state": "DENIED",
      "reason_codes": [
        "RESOURCE_OUT_OF_SCOPE"
      ],
      "approval_id": null,
      "approval_state": null,
      "execution_id": "bac6863c-6ce8-49ac-a00c-7993a808752e",
      "trace_id": "4d48bb9a-0919-412a-a974-36b0183c9da1",
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

## T05. 프롬프트 인젝션

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
    "inspection_id": "bb8605eb-bfdf-45b8-bf0a-641083c118c7",
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

## T06. 유니코드 은닉

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
    "inspection_id": "d7a927f0-3b40-40fa-9493-4de5feae724f",
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

## T07. 정상 입력 검사

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
    "inspection_id": "9251fb45-a175-40c9-ad16-f0207795be54",
    "verdict": "CLEAR",
    "reason_codes": [],
    "scanner_version": "rules-v2",
    "content_hash": "b30f8abfc14924819693b743cba3061fe173a1bbf137ade96685a3936dcce779"
  },
  "mitre": "None",
  "severity": "INFO"
}
```

## T08. 실제 산출물 생성과 승인 대기

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
    "action_id": "69be9ca2-631f-4646-bd52-9c5f7b10ff29",
    "decision": "REQUIRE_APPROVAL",
    "state": "PENDING_APPROVAL",
    "reason_codes": [],
    "approval_id": "e2b45c35-6ac3-4e3f-af96-640ecc206656",
    "approval_state": "PENDING",
    "execution_id": "52938932-3574-4611-a2cb-86c43c8feb70",
    "trace_id": "1a6a09e0-2c4a-46e1-8213-071347b826e7",
    "policy_version": "demo-v2",
    "result": null
  },
  "mitre": "T1048 (Exfiltration Over Alternative Protocol)",
  "severity": "HIGH"
}
```

## T09. 승인 전 실행 차단

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

## T10. 검토자 승인

- 예상 결과: 200 APPROVED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "response": {
    "approval_id": "e2b45c35-6ac3-4e3f-af96-640ecc206656",
    "action_id": "69be9ca2-631f-4646-bd52-9c5f7b10ff29",
    "state": "APPROVED"
  }
}
```

## T11. 승인 후 실행·재실행 중복 방지

- 예상 결과: 200 SUCCEEDED, 재실행 후에도 outbox 1건
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "response": {
    "action_id": "69be9ca2-631f-4646-bd52-9c5f7b10ff29",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "e2b45c35-6ac3-4e3f-af96-640ecc206656",
    "approval_state": "CONSUMED",
    "execution_id": "52938932-3574-4611-a2cb-86c43c8feb70",
    "trace_id": "1a6a09e0-2c4a-46e1-8213-071347b826e7",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-0cfac6a9-80b5-4919-8c59-7a7d35783ee5",
      "execution_id": "52938932-3574-4611-a2cb-86c43c8feb70",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-22ea7835-48e6-4f78-8a17-b8d6f7f6f6be",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      }
    }
  },
  "repeat_status": 200,
  "repeat": {
    "action_id": "69be9ca2-631f-4646-bd52-9c5f7b10ff29",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "e2b45c35-6ac3-4e3f-af96-640ecc206656",
    "approval_state": "CONSUMED",
    "execution_id": "52938932-3574-4611-a2cb-86c43c8feb70",
    "trace_id": "1a6a09e0-2c4a-46e1-8213-071347b826e7",
    "policy_version": "demo-v2",
    "result": {
      "execution_id": "52938932-3574-4611-a2cb-86c43c8feb70",
      "action_id": "69be9ca2-631f-4646-bd52-9c5f7b10ff29",
      "receipt_id": "receipt-0cfac6a9-80b5-4919-8c59-7a7d35783ee5",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-22ea7835-48e6-4f78-8a17-b8d6f7f6f6be",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      },
      "created": 1793668452.9066672
    }
  },
  "outbox": 1
}
```

## T12. 감사 해시 연결

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
    "latest_chain_hash": "d9ac0566348f78b86ded345c4f415938c30750829916a5ded230f528d756faa4"
  },
  "mitre": "T1562 (Impair Defenses / Audit Tampering)",
  "severity": "INFO"
}
```

## T13. 다른 사이트에서 테스트 실행 차단

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

## T14. 도구 직접 접근 인증

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

## T15. 대시보드 감사 연결

- 예상 결과: 200, 실제 감사 이벤트 > 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "status": 200,
  "count": 14
}
```

## T16. DB 접근 요청·보안 에이전트 분석

- 예상 결과: 202 PENDING_APPROVAL, 분석 근거와 추천 대응 제공
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793668452.967009,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793669352.967009,
  "reviewer": null,
  "review_reason": null,
  "decided_at": null,
  "result_count": null,
  "trace_id": "832ce2f1-19e0-40f7-96f6-964509eb4d08",
  "request_id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
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
  "execution_id": "e6762e63-3900-407b-a852-de88e3c756bb",
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
      "at": 1793668452.969008,
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

## T17. 사람 승인 전 DB 조회 차단

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

## T18. 판단 근거를 포함한 사람 승인

- 예상 결과: 200 APPROVED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793668452.967009,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793669352.967009,
  "reviewer": "reviewer-demo",
  "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
  "decided_at": 1793668452.9980087,
  "result_count": null,
  "trace_id": "832ce2f1-19e0-40f7-96f6-964509eb4d08",
  "request_id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
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
  "execution_id": "e6762e63-3900-407b-a852-de88e3c756bb",
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
      "at": 1793668452.969008,
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
      "at": 1793668452.9990075,
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

## T19. 승인 후 실제 SQL 조회·영수증 재사용

- 예상 결과: 25행 조회, 동일 영수증으로 재실행 응답
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "http": 200,
  "row_count": 25,
  "receipt_id": "receipt-9bae6e87-17e6-4d59-b23d-4d7b1261987b",
  "repeat_receipt": "receipt-9bae6e87-17e6-4d59-b23d-4d7b1261987b",
  "replayed": true
}
```

## T20. DB 분석 시나리오 sensitive

- 예상 결과: PENDING_APPROVAL
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 202,
  "request": {
    "id": "1e9868de-f0ea-4231-b16d-a19293f6e8da",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793668453.0890963,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 70,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793669353.0890963,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "a90d406b-d035-41b6-80e0-41c30f189a96",
    "request_id": "1e9868de-f0ea-4231-b16d-a19293f6e8da",
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
    "execution_id": "37a84fc5-a7aa-4110-bf8d-2911d75eaf1c",
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
        "at": 1793668453.0900974,
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

## T21. DB 분석 시나리오 bulk

- 예상 결과: PENDING_APPROVAL
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 202,
  "request": {
    "id": "93842922-5922-4d0e-b42d-6a43bd3af9e9",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793668453.1210217,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 40,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793669353.1210217,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "15872599-4ce7-4fa7-9637-ad314a69d79e",
    "request_id": "93842922-5922-4d0e-b42d-6a43bd3af9e9",
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
    "execution_id": "ea03d87d-9d23-4e20-8dfb-32227a369864",
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
        "at": 1793668453.121939,
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

## T22. DB 분석 시나리오 abnormal

- 예상 결과: DENIED
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "gateway_status": 403,
  "request": {
    "id": "baa62956-abb2-41dc-a308-2fb0df8c6942",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793668453.12794,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 55,
    "decision": "DENY",
    "expires_at": 1793669353.12794,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "608c2bb0-84ed-437e-a56f-8980d568fe0f",
    "request_id": "baa62956-abb2-41dc-a308-2fb0df8c6942",
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
    "execution_id": "f11dd714-cb3e-4557-8e8a-59093cca5365",
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
        "at": 1793668453.1289406,
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

## T23. 30분 위험도 증가·감쇠·소멸

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

## T24. 현재 위험도·일일 처리 집계

- 예상 결과: 대기+허용+차단=오늘 요청 수, 실제 위험 요인 포함
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "as_of": 1793668453.1335552,
  "timezone": "Asia/Seoul",
  "day_start": 1793631600.0,
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
      "at": 1793666713.1335552,
      "count": 0
    },
    {
      "at": 1793666773.1335552,
      "count": 0
    },
    {
      "at": 1793666833.1335552,
      "count": 0
    },
    {
      "at": 1793666893.1335552,
      "count": 0
    },
    {
      "at": 1793666953.1335552,
      "count": 0
    },
    {
      "at": 1793667013.1335552,
      "count": 0
    },
    {
      "at": 1793667073.1335552,
      "count": 0
    },
    {
      "at": 1793667133.1335552,
      "count": 0
    },
    {
      "at": 1793667193.1335552,
      "count": 0
    },
    {
      "at": 1793667253.1335552,
      "count": 0
    },
    {
      "at": 1793667313.1335552,
      "count": 0
    },
    {
      "at": 1793667373.1335552,
      "count": 0
    },
    {
      "at": 1793667433.1335552,
      "count": 0
    },
    {
      "at": 1793667493.1335552,
      "count": 0
    },
    {
      "at": 1793667553.1335552,
      "count": 0
    },
    {
      "at": 1793667613.1335552,
      "count": 0
    },
    {
      "at": 1793667673.1335552,
      "count": 0
    },
    {
      "at": 1793667733.1335552,
      "count": 0
    },
    {
      "at": 1793667793.1335552,
      "count": 0
    },
    {
      "at": 1793667853.1335552,
      "count": 0
    },
    {
      "at": 1793667913.1335552,
      "count": 0
    },
    {
      "at": 1793667973.1335552,
      "count": 0
    },
    {
      "at": 1793668033.1335552,
      "count": 0
    },
    {
      "at": 1793668093.1335552,
      "count": 0
    },
    {
      "at": 1793668153.1335552,
      "count": 0
    },
    {
      "at": 1793668213.1335552,
      "count": 0
    },
    {
      "at": 1793668273.1335552,
      "count": 0
    },
    {
      "at": 1793668333.1335552,
      "count": 0
    },
    {
      "at": 1793668393.1335552,
      "count": 0
    },
    {
      "at": 1793668453.1335552,
      "count": 4
    }
  ],
  "risk_trend": [
    {
      "at": 1793666653.1335552,
      "score": 0.0
    },
    {
      "at": 1793666713.1335552,
      "score": 0.0
    },
    {
      "at": 1793666773.1335552,
      "score": 0.0
    },
    {
      "at": 1793666833.1335552,
      "score": 0.0
    },
    {
      "at": 1793666893.1335552,
      "score": 0.0
    },
    {
      "at": 1793666953.1335552,
      "score": 0.0
    },
    {
      "at": 1793667013.1335552,
      "score": 0.0
    },
    {
      "at": 1793667073.1335552,
      "score": 0.0
    },
    {
      "at": 1793667133.1335552,
      "score": 0.0
    },
    {
      "at": 1793667193.1335552,
      "score": 0.0
    },
    {
      "at": 1793667253.1335552,
      "score": 0.0
    },
    {
      "at": 1793667313.1335552,
      "score": 0.0
    },
    {
      "at": 1793667373.1335552,
      "score": 0.0
    },
    {
      "at": 1793667433.1335552,
      "score": 0.0
    },
    {
      "at": 1793667493.1335552,
      "score": 0.0
    },
    {
      "at": 1793667553.1335552,
      "score": 0.0
    },
    {
      "at": 1793667613.1335552,
      "score": 0.0
    },
    {
      "at": 1793667673.1335552,
      "score": 0.0
    },
    {
      "at": 1793667733.1335552,
      "score": 0.0
    },
    {
      "at": 1793667793.1335552,
      "score": 0.0
    },
    {
      "at": 1793667853.1335552,
      "score": 0.0
    },
    {
      "at": 1793667913.1335552,
      "score": 0.0
    },
    {
      "at": 1793667973.1335552,
      "score": 0.0
    },
    {
      "at": 1793668033.1335552,
      "score": 0.0
    },
    {
      "at": 1793668093.1335552,
      "score": 0.0
    },
    {
      "at": 1793668153.1335552,
      "score": 0.0
    },
    {
      "at": 1793668213.1335552,
      "score": 0.0
    },
    {
      "at": 1793668273.1335552,
      "score": 0.0
    },
    {
      "at": 1793668333.1335552,
      "score": 0.0
    },
    {
      "at": 1793668393.1335552,
      "score": 0.0
    },
    {
      "at": 1793668453.1335552,
      "score": 42.0
    }
  ],
  "recent": [
    {
      "id": "baa62956-abb2-41dc-a308-2fb0df8c6942",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793668453.12794,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 55,
      "decision": "DENY",
      "expires_at": 1793669353.12794,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "608c2bb0-84ed-437e-a56f-8980d568fe0f",
      "request_id": "baa62956-abb2-41dc-a308-2fb0df8c6942",
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
      "execution_id": "f11dd714-cb3e-4557-8e8a-59093cca5365",
      "receipt_id": null,
      "authorization": {
        "mode": "denied",
        "role": "report-submitter"
      }
    },
    {
      "id": "93842922-5922-4d0e-b42d-6a43bd3af9e9",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793668453.1210217,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 40,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793669353.1210217,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "15872599-4ce7-4fa7-9637-ad314a69d79e",
      "request_id": "93842922-5922-4d0e-b42d-6a43bd3af9e9",
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
      "execution_id": "ea03d87d-9d23-4e20-8dfb-32227a369864",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "1e9868de-f0ea-4231-b16d-a19293f6e8da",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793668453.0890963,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 70,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793669353.0890963,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "a90d406b-d035-41b6-80e0-41c30f189a96",
      "request_id": "1e9868de-f0ea-4231-b16d-a19293f6e8da",
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
      "execution_id": "37a84fc5-a7aa-4110-bf8d-2911d75eaf1c",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793668452.967009,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 15,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793669352.967009,
      "reviewer": "reviewer-demo",
      "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
      "decided_at": 1793668452.9980087,
      "result_count": 25,
      "trace_id": "832ce2f1-19e0-40f7-96f6-964509eb4d08",
      "request_id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
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
      "execution_id": "e6762e63-3900-407b-a852-de88e3c756bb",
      "receipt_id": "receipt-9bae6e87-17e6-4d59-b23d-4d7b1261987b",
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

## T25. 언제·어디서·누가·무엇·결과의 보고서

- 예상 결과: 메타데이터, 보안 분석, 검토 근거, 처리 이력 보존
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "http": 200,
  "report": {
    "id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793668452.967009,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 15,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793669352.967009,
    "reviewer": "reviewer-demo",
    "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
    "decided_at": 1793668452.9980087,
    "result_count": 25,
    "trace_id": "832ce2f1-19e0-40f7-96f6-964509eb4d08",
    "request_id": "804e7c48-0df8-499c-94d8-f9be5563cf41",
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
    "execution_id": "e6762e63-3900-407b-a852-de88e3c756bb",
    "receipt_id": "receipt-9bae6e87-17e6-4d59-b23d-4d7b1261987b",
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
        "at": 1793668452.969008,
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
        "at": 1793668452.9990075,
        "actor": "reviewer-demo",
        "event": "DB_APPROVED",
        "details": {
          "reason": "업무 범위와 열·조회량을 확인했습니다.",
          "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
        }
      },
      {
        "at": 1793668453.0285027,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_STARTED",
        "details": {
          "execution_id": "e6762e63-3900-407b-a852-de88e3c756bb",
          "authorization": {
            "mode": "human",
            "role": "report-submitter"
          }
        }
      },
      {
        "at": 1793668453.0437517,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_SUCCEEDED",
        "details": {
          "row_count": 25,
          "receipt_id": "receipt-9bae6e87-17e6-4d59-b23d-4d7b1261987b"
        }
      }
    ]
  }
}
```

## T26. 원클릭 실제 작동 점검

- 예상 결과: 연결·분석·DB·무결성 모든 점검 통과
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "checked_at": 1793668453.1845171,
  "passed": true,
  "checks": [
    {
      "name": "게이트웨이",
      "passed": true,
      "detail": "ready",
      "latency_ms": 0.74
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
      "latency_ms": 16.1
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

## T27. 동시 대시보드 조회 인증 안정성

- 예상 결과: 80개 요청 모두 200
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "total": 80,
  "successful": 80
}
```

## T28. 정상 종료 시 포트 반환

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

## T29. 독립 EXE 기동과 6개 시나리오

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
          "action_id": "acca27e4-c732-40d0-9149-cf1d4cf655f6",
          "decision": "ALLOW",
          "state": "SUCCEEDED",
          "reason_codes": [],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "a4f5d5e2-d348-4387-aeb0-6d9c65599e3d",
          "trace_id": "90418ae1-cd15-45a4-bb84-47b676432a7d",
          "policy_version": "demo-v2",
          "result": {
            "receipt_id": "receipt-735fb116-b2f0-4b74-a018-976f3e283132",
            "execution_id": "a4f5d5e2-d348-4387-aeb0-6d9c65599e3d",
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
          "action_id": "7601f340-68ad-4489-b3d1-b169fc3185f4",
          "decision": "DENY",
          "state": "DENIED",
          "reason_codes": [
            "RESOURCE_OUT_OF_SCOPE"
          ],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "b4d4fdf2-5e6d-4148-9639-e041935d16a0",
          "trace_id": "c7bbca30-9340-4377-9e3e-5c678ee343ca",
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
          "inspection_id": "bc7f088b-e864-486a-a26a-bd2f2abed8e9",
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
          "inspection_id": "42e58558-2999-4e44-a566-2cb32fbb3172",
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
          "action_id": "4ad272ce-f0fa-48c9-905e-861897d1ff27",
          "decision": "REQUIRE_APPROVAL",
          "state": "PENDING_APPROVAL",
          "reason_codes": [],
          "approval_id": "fe077465-ecfd-4daf-94bf-ec593515ccb8",
          "approval_state": "PENDING",
          "execution_id": "880bdb66-8811-465b-84fe-679e5afb5a76",
          "trace_id": "7925e33b-dbc9-478f-9f5e-2e994f9c41d2",
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
          "latest_chain_hash": "3646e3d12fcb0606e0c36fa2932f9a4c56c1faa8bf33832de66704e99175003c"
        },
        "mitre": "T1562 (Impair Defenses / Audit Tampering)",
        "severity": "INFO"
      }
    }
  },
  "binary": {
    "sha256": "1905d613f52af8949374137a75a698a8e3aaa246eba09bc50e0397f80c93ea24",
    "bytes": 15207031
  }
}
```

## T30. 독립 EXE의 DB 요청·분석·작동 진단

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
    "checked_at": 1793668462.3332078,
    "passed": true,
    "checks": [
      {
        "name": "게이트웨이",
        "passed": true,
        "detail": "ready",
        "latency_ms": 0.91
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
        "latency_ms": 15.09
      },
      {
        "name": "감사 DB",
        "passed": true,
        "detail": "감사 기록 저장소 연결됨",
        "latency_ms": 0.14
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

## T31. EXE 자동 종료

- 예상 결과: exit 0
- 실제 판정: **PASS**
- 관찰값 및 응답 원문:

```json
{
  "exit_code": 0
}
```

## 미실행 범위

- Docker 다중 네트워크 격리·사내 PostgreSQL 운영 연결(임시 PostgreSQL 기능 검증은 별도 보고서): NOT_RUN
- 코드 서명·다른 Windows PC 실행: NOT_RUN

## 재현과 증거

- 단계별 설명: [TEST_GUIDE.md](../../TEST_GUIDE.md)
- 구조화 결과: [results.json](results.json)
- 회귀 테스트 로그: [unittest.log](unittest.log)
- 감사 이벤트: [audit-events.json](audit-events.json)
- 실행파일 로그: [exe-smoke.log](exe-smoke.log)
- 테스트는 별도 임시 디렉터리를 사용하며 사용자 실행 데이터는 삭제하지 않습니다.
