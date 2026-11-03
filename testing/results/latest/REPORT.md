# ASG 실제 테스트 결과보고서

- 실행: 2026-11-03 14:34:57 ~ 14:35:44 (Asia/Seoul)
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
  "tests": 125
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
    "action_id": "a9feeb27-ef07-4eff-8a30-61cfe22a0955",
    "decision": "ALLOW",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": null,
    "approval_state": null,
    "execution_id": "cb25ca8b-8304-4bf3-958d-38a602b612e7",
    "trace_id": "21993df3-4c1a-4f55-8061-231ca580152a",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-36a47a1b-c052-463b-b679-bcffbf86a950",
      "execution_id": "cb25ca8b-8304-4bf3-958d-38a602b612e7",
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
      "action_id": "32616645-cbda-4079-8f83-04737d5bb116",
      "decision": "DENY",
      "state": "DENIED",
      "reason_codes": [
        "RESOURCE_OUT_OF_SCOPE"
      ],
      "approval_id": null,
      "approval_state": null,
      "execution_id": "938cb4c9-41df-4759-92c3-5f30df2197b9",
      "trace_id": "21009887-3a52-46f9-b9eb-12ac89907277",
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
    "inspection_id": "421af296-ccaa-42ef-8e87-0220bf4a6657",
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
    "inspection_id": "e38b89cd-7b12-4eb0-ab56-70d36c14ee51",
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
    "inspection_id": "a87cb286-bf39-46dc-bdf8-d6078ec06d56",
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
    "action_id": "eb717b86-f731-4611-850f-f2ee8d97e427",
    "decision": "REQUIRE_APPROVAL",
    "state": "PENDING_APPROVAL",
    "reason_codes": [],
    "approval_id": "67968787-a567-4aa0-8f1e-fee2baf8db52",
    "approval_state": "PENDING",
    "execution_id": "9a2197c4-a45b-4c8e-a695-e50cd2db502c",
    "trace_id": "26363934-83e0-4cfb-a4d7-b3ed558788ff",
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
    "approval_id": "67968787-a567-4aa0-8f1e-fee2baf8db52",
    "action_id": "eb717b86-f731-4611-850f-f2ee8d97e427",
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
    "action_id": "eb717b86-f731-4611-850f-f2ee8d97e427",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "67968787-a567-4aa0-8f1e-fee2baf8db52",
    "approval_state": "CONSUMED",
    "execution_id": "9a2197c4-a45b-4c8e-a695-e50cd2db502c",
    "trace_id": "26363934-83e0-4cfb-a4d7-b3ed558788ff",
    "policy_version": "demo-v2",
    "result": {
      "receipt_id": "receipt-acb3643c-665a-4d5c-bfa7-40e1741b0f82",
      "execution_id": "9a2197c4-a45b-4c8e-a695-e50cd2db502c",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-dda5354b-8c9a-41f6-9168-aa3000727294",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      }
    }
  },
  "repeat_status": 200,
  "repeat": {
    "action_id": "eb717b86-f731-4611-850f-f2ee8d97e427",
    "decision": "REQUIRE_APPROVAL",
    "state": "SUCCEEDED",
    "reason_codes": [],
    "approval_id": "67968787-a567-4aa0-8f1e-fee2baf8db52",
    "approval_state": "CONSUMED",
    "execution_id": "9a2197c4-a45b-4c8e-a695-e50cd2db502c",
    "trace_id": "26363934-83e0-4cfb-a4d7-b3ed558788ff",
    "policy_version": "demo-v2",
    "result": {
      "execution_id": "9a2197c4-a45b-4c8e-a695-e50cd2db502c",
      "action_id": "eb717b86-f731-4611-850f-f2ee8d97e427",
      "receipt_id": "receipt-acb3643c-665a-4d5c-bfa7-40e1741b0f82",
      "result": {
        "status": "submitted_to_mock_outbox",
        "artifact_id": "artifact-dda5354b-8c9a-41f6-9168-aa3000727294",
        "destination_id": "internal-review-outbox",
        "content_hash": "41e95c20ceb9b5cb597e25ca6aa7191c654bbedbc5afc265023a892f3e8b8d4e"
      },
      "created": 1793684120.026676
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
    "latest_chain_hash": "38bd2445f54963bff57e1a2cfd2cd50c7f17b2ad3a4b8696918441f91858f35a"
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
  "id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793684120.0553882,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793685020.0553882,
  "reviewer": null,
  "review_reason": null,
  "decided_at": null,
  "result_count": null,
  "trace_id": "687ef417-44b9-4d09-b2a7-932b6dc3d659",
  "request_id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
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
  "execution_id": "f0935b1d-82dc-4c3a-86dc-33e7afe2aa71",
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
      "at": 1793684120.0564306,
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
  "id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
  "principal": "agent-alice",
  "user_name": "alice",
  "tenant": "north",
  "task_id": "task-alice-001",
  "requested_at": 1793684120.0553882,
  "source_ip": "127.0.0.1",
  "client": "Python-urllib/3.12",
  "risk_score": 15,
  "decision": "REQUIRE_APPROVAL",
  "expires_at": 1793685020.0553882,
  "reviewer": "reviewer-demo",
  "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
  "decided_at": 1793684120.0649953,
  "result_count": null,
  "trace_id": "687ef417-44b9-4d09-b2a7-932b6dc3d659",
  "request_id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
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
  "execution_id": "f0935b1d-82dc-4c3a-86dc-33e7afe2aa71",
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
      "at": 1793684120.0564306,
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
      "at": 1793684120.0655227,
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
  "receipt_id": "receipt-fc92542c-7af4-4386-99a4-04f866fdd2ff",
  "repeat_receipt": "receipt-fc92542c-7af4-4386-99a4-04f866fdd2ff",
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
    "id": "3f368b50-a320-43b6-88d9-75cd7f7007db",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793684120.1074684,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 70,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793685020.1074684,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "ce6837a2-53a9-4247-b3c2-491a70b719fc",
    "request_id": "3f368b50-a320-43b6-88d9-75cd7f7007db",
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
    "execution_id": "3afc70cc-1117-4d31-bea7-187b18993a11",
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
        "at": 1793684120.108088,
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
    "id": "2e8fa742-ccc5-4443-8014-a51650847335",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793684120.1159124,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 40,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793685020.1159124,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "b7f97005-5d99-4906-9852-dae08b6a195a",
    "request_id": "2e8fa742-ccc5-4443-8014-a51650847335",
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
    "execution_id": "b71c13b9-81c6-41b8-bd0c-200f1836d39c",
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
        "at": 1793684120.1174753,
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
    "id": "567034f9-9bf0-431a-b4c8-4251937ac26c",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793684120.1237712,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 55,
    "decision": "DENY",
    "expires_at": 1793685020.1237712,
    "reviewer": null,
    "review_reason": null,
    "decided_at": null,
    "result_count": null,
    "trace_id": "bf9d9a3c-75b7-47a2-9ebe-3b417560b099",
    "request_id": "567034f9-9bf0-431a-b4c8-4251937ac26c",
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
    "execution_id": "7741d676-48af-467e-b0d7-ef50d8253344",
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
        "at": 1793684120.1248415,
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
  "as_of": 1793684120.1316178,
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
      "at": 1793682380.1316178,
      "count": 0
    },
    {
      "at": 1793682440.1316178,
      "count": 0
    },
    {
      "at": 1793682500.1316178,
      "count": 0
    },
    {
      "at": 1793682560.1316178,
      "count": 0
    },
    {
      "at": 1793682620.1316178,
      "count": 0
    },
    {
      "at": 1793682680.1316178,
      "count": 0
    },
    {
      "at": 1793682740.1316178,
      "count": 0
    },
    {
      "at": 1793682800.1316178,
      "count": 0
    },
    {
      "at": 1793682860.1316178,
      "count": 0
    },
    {
      "at": 1793682920.1316178,
      "count": 0
    },
    {
      "at": 1793682980.1316178,
      "count": 0
    },
    {
      "at": 1793683040.1316178,
      "count": 0
    },
    {
      "at": 1793683100.1316178,
      "count": 0
    },
    {
      "at": 1793683160.1316178,
      "count": 0
    },
    {
      "at": 1793683220.1316178,
      "count": 0
    },
    {
      "at": 1793683280.1316178,
      "count": 0
    },
    {
      "at": 1793683340.1316178,
      "count": 0
    },
    {
      "at": 1793683400.1316178,
      "count": 0
    },
    {
      "at": 1793683460.1316178,
      "count": 0
    },
    {
      "at": 1793683520.1316178,
      "count": 0
    },
    {
      "at": 1793683580.1316178,
      "count": 0
    },
    {
      "at": 1793683640.1316178,
      "count": 0
    },
    {
      "at": 1793683700.1316178,
      "count": 0
    },
    {
      "at": 1793683760.1316178,
      "count": 0
    },
    {
      "at": 1793683820.1316178,
      "count": 0
    },
    {
      "at": 1793683880.1316178,
      "count": 0
    },
    {
      "at": 1793683940.1316178,
      "count": 0
    },
    {
      "at": 1793684000.1316178,
      "count": 0
    },
    {
      "at": 1793684060.1316178,
      "count": 0
    },
    {
      "at": 1793684120.1316178,
      "count": 4
    }
  ],
  "risk_trend": [
    {
      "at": 1793682320.1316178,
      "score": 0.0
    },
    {
      "at": 1793682380.1316178,
      "score": 0.0
    },
    {
      "at": 1793682440.1316178,
      "score": 0.0
    },
    {
      "at": 1793682500.1316178,
      "score": 0.0
    },
    {
      "at": 1793682560.1316178,
      "score": 0.0
    },
    {
      "at": 1793682620.1316178,
      "score": 0.0
    },
    {
      "at": 1793682680.1316178,
      "score": 0.0
    },
    {
      "at": 1793682740.1316178,
      "score": 0.0
    },
    {
      "at": 1793682800.1316178,
      "score": 0.0
    },
    {
      "at": 1793682860.1316178,
      "score": 0.0
    },
    {
      "at": 1793682920.1316178,
      "score": 0.0
    },
    {
      "at": 1793682980.1316178,
      "score": 0.0
    },
    {
      "at": 1793683040.1316178,
      "score": 0.0
    },
    {
      "at": 1793683100.1316178,
      "score": 0.0
    },
    {
      "at": 1793683160.1316178,
      "score": 0.0
    },
    {
      "at": 1793683220.1316178,
      "score": 0.0
    },
    {
      "at": 1793683280.1316178,
      "score": 0.0
    },
    {
      "at": 1793683340.1316178,
      "score": 0.0
    },
    {
      "at": 1793683400.1316178,
      "score": 0.0
    },
    {
      "at": 1793683460.1316178,
      "score": 0.0
    },
    {
      "at": 1793683520.1316178,
      "score": 0.0
    },
    {
      "at": 1793683580.1316178,
      "score": 0.0
    },
    {
      "at": 1793683640.1316178,
      "score": 0.0
    },
    {
      "at": 1793683700.1316178,
      "score": 0.0
    },
    {
      "at": 1793683760.1316178,
      "score": 0.0
    },
    {
      "at": 1793683820.1316178,
      "score": 0.0
    },
    {
      "at": 1793683880.1316178,
      "score": 0.0
    },
    {
      "at": 1793683940.1316178,
      "score": 0.0
    },
    {
      "at": 1793684000.1316178,
      "score": 0.0
    },
    {
      "at": 1793684060.1316178,
      "score": 0.0
    },
    {
      "at": 1793684120.1316178,
      "score": 42.0
    }
  ],
  "recent": [
    {
      "id": "567034f9-9bf0-431a-b4c8-4251937ac26c",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793684120.1237712,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 55,
      "decision": "DENY",
      "expires_at": 1793685020.1237712,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "bf9d9a3c-75b7-47a2-9ebe-3b417560b099",
      "request_id": "567034f9-9bf0-431a-b4c8-4251937ac26c",
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
      "execution_id": "7741d676-48af-467e-b0d7-ef50d8253344",
      "receipt_id": null,
      "authorization": {
        "mode": "denied",
        "role": "report-submitter"
      }
    },
    {
      "id": "2e8fa742-ccc5-4443-8014-a51650847335",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793684120.1159124,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 40,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793685020.1159124,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "b7f97005-5d99-4906-9852-dae08b6a195a",
      "request_id": "2e8fa742-ccc5-4443-8014-a51650847335",
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
      "execution_id": "b71c13b9-81c6-41b8-bd0c-200f1836d39c",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "3f368b50-a320-43b6-88d9-75cd7f7007db",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793684120.1074684,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 70,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793685020.1074684,
      "reviewer": null,
      "review_reason": null,
      "decided_at": null,
      "result_count": null,
      "trace_id": "ce6837a2-53a9-4247-b3c2-491a70b719fc",
      "request_id": "3f368b50-a320-43b6-88d9-75cd7f7007db",
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
      "execution_id": "3afc70cc-1117-4d31-bea7-187b18993a11",
      "receipt_id": null,
      "authorization": {
        "mode": "human",
        "role": "report-submitter"
      }
    },
    {
      "id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
      "principal": "agent-alice",
      "user_name": "alice",
      "tenant": "north",
      "task_id": "task-alice-001",
      "requested_at": 1793684120.0553882,
      "source_ip": "127.0.0.1",
      "client": "Python-urllib/3.12",
      "risk_score": 15,
      "decision": "REQUIRE_APPROVAL",
      "expires_at": 1793685020.0553882,
      "reviewer": "reviewer-demo",
      "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
      "decided_at": 1793684120.0649953,
      "result_count": 25,
      "trace_id": "687ef417-44b9-4d09-b2a7-932b6dc3d659",
      "request_id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
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
      "execution_id": "f0935b1d-82dc-4c3a-86dc-33e7afe2aa71",
      "receipt_id": "receipt-fc92542c-7af4-4386-99a4-04f866fdd2ff",
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
    "id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
    "principal": "agent-alice",
    "user_name": "alice",
    "tenant": "north",
    "task_id": "task-alice-001",
    "requested_at": 1793684120.0553882,
    "source_ip": "127.0.0.1",
    "client": "Python-urllib/3.12",
    "risk_score": 15,
    "decision": "REQUIRE_APPROVAL",
    "expires_at": 1793685020.0553882,
    "reviewer": "reviewer-demo",
    "review_reason": "업무 범위와 열·조회량을 확인했습니다.",
    "decided_at": 1793684120.0649953,
    "result_count": 25,
    "trace_id": "687ef417-44b9-4d09-b2a7-932b6dc3d659",
    "request_id": "5277367f-2aca-4f72-a751-40c3b3d0257b",
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
    "execution_id": "f0935b1d-82dc-4c3a-86dc-33e7afe2aa71",
    "receipt_id": "receipt-fc92542c-7af4-4386-99a4-04f866fdd2ff",
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
        "at": 1793684120.0564306,
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
        "at": 1793684120.0655227,
        "actor": "reviewer-demo",
        "event": "DB_APPROVED",
        "details": {
          "reason": "업무 범위와 열·조회량을 확인했습니다.",
          "snapshot_hash": "8442085d0d6001055d1ec95da36cf24712a8714af9d4523e2c2266be023c0911"
        }
      },
      {
        "at": 1793684120.0717928,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_STARTED",
        "details": {
          "execution_id": "f0935b1d-82dc-4c3a-86dc-33e7afe2aa71",
          "authorization": {
            "mode": "human",
            "role": "report-submitter"
          }
        }
      },
      {
        "at": 1793684120.0917928,
        "actor": "agent-alice",
        "event": "DB_EXECUTION_SUCCEEDED",
        "details": {
          "row_count": 25,
          "receipt_id": "receipt-fc92542c-7af4-4386-99a4-04f866fdd2ff"
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
  "checked_at": 1793684120.1405816,
  "passed": true,
  "checks": [
    {
      "name": "게이트웨이",
      "passed": true,
      "detail": "ready",
      "latency_ms": 0.86
    },
    {
      "name": "보안 에이전트",
      "passed": true,
      "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
      "latency_ms": 0.17
    },
    {
      "name": "보호 DB",
      "passed": true,
      "detail": "검증용 SQLite DB 읽기 연결 정상",
      "latency_ms": 1.52
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
          "action_id": "57b956a0-7bc3-4c3a-bc4b-50b7d43e26de",
          "decision": "ALLOW",
          "state": "SUCCEEDED",
          "reason_codes": [],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "38f68a74-55c5-45b2-8f44-20b10fa15ecc",
          "trace_id": "016c1731-50f8-4b49-8731-5607e8cc3195",
          "policy_version": "demo-v2",
          "result": {
            "receipt_id": "receipt-97c60e66-424e-4d15-8f7a-2726be207d2d",
            "execution_id": "38f68a74-55c5-45b2-8f44-20b10fa15ecc",
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
          "action_id": "e92623cd-6ac2-452e-bd99-0b023772f3fa",
          "decision": "DENY",
          "state": "DENIED",
          "reason_codes": [
            "RESOURCE_OUT_OF_SCOPE"
          ],
          "approval_id": null,
          "approval_state": null,
          "execution_id": "d4228c87-7d3f-44ea-951a-8c3c5938bc0e",
          "trace_id": "13f57468-53da-46a0-8399-21168be13660",
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
          "inspection_id": "7e06476d-a543-4042-83eb-45f208b8b4ce",
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
          "inspection_id": "ebbd6fb3-c599-4f9b-9dfd-1afb8a77735b",
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
          "action_id": "35394aab-7029-4c80-87a0-705994e07a69",
          "decision": "REQUIRE_APPROVAL",
          "state": "PENDING_APPROVAL",
          "reason_codes": [],
          "approval_id": "934a4dcd-7d8a-4248-928c-ada725a91401",
          "approval_state": "PENDING",
          "execution_id": "a8d8d196-78e4-47e6-8e8d-5a85363a8acd",
          "trace_id": "b2b49896-8aa6-42db-ac3a-225dcfeddbe7",
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
          "latest_chain_hash": "37282abd5318d2abdda7a98d58d4b31a365c26967afdaa35fae27938104fb969"
        },
        "mitre": "T1562 (Impair Defenses / Audit Tampering)",
        "severity": "INFO"
      }
    }
  },
  "binary": {
    "sha256": "d497c1f5279e7135ca22193dff62e21d858cfd33bb7f1220947dd955c95dfe98",
    "bytes": 14174875
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
    "checked_at": 1793684129.1104734,
    "passed": true,
    "checks": [
      {
        "name": "게이트웨이",
        "passed": true,
        "detail": "ready",
        "latency_ms": 22.8
      },
      {
        "name": "보안 에이전트",
        "passed": true,
        "detail": "정상·정책 위반 입력 분석 자체 점검 통과",
        "latency_ms": 0.18
      },
      {
        "name": "보호 DB",
        "passed": true,
        "detail": "검증용 SQLite DB 읽기 연결 정상",
        "latency_ms": 16.77
      },
      {
        "name": "감사 DB",
        "passed": true,
        "detail": "감사 기록 저장소 연결됨",
        "latency_ms": 0.16
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
