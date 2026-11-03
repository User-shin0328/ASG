# ASG · 정책 기반 DB 접근 게이트웨이

사내 프로그램·에이전트의 DB 읽기를 **명시적 자동 허용 / 예외 검토 / 자동 차단**으로 처리합니다. 게이트웨이 내부 LLM·Ollama·학습형 분류기 실행 경로는 제거했습니다.

## 바로 실행

[ASG.exe](ASG.exe)를 내려받아 실행하면 루프백 대시보드를 엽니다. 기본 실행파일은 가상 데이터 SQLite 검증 모드입니다. PostgreSQL 보호 DB는 별도 연결 설정을 사용합니다. 실제 사내 DB·기업 로그인이 연결된 제품이라고 표시하지 않습니다.

## 적용한 통제

| 통제 | 동작 |
|---|---|
| 자동 허용 | 등록 역할·작업, 운영 이력 기본 열, 요청당 100행 이하 등 명시적 정책 |
| 예외 승인 | 민감정보·대량 조회·자동 정책 밖의 유효 요청만 검토 |
| 자동 차단 | 미등록 데이터/열, 권한·형식 위반, 분석 오류, 초과 요청 빈도 |
| 반복 업무 승인 | 같은 신원·업무·대상·열·필터·목적에 기간·횟수·누적 행 수 제한 |
| 누적 예산 | 최근 30분 기본 1,000회·5,000행. 실행 전 최대량 예약 후 실제 반환량 정산 |
| 오류·재시도 | 미확정 예약 유지, 영수증 재사용, 만료 뒤 저장된 영수증만 대조 |
| 감사 | 자동 허용·발급·취소·차단·실행 이력과 해시 체인 |

점수만으로 자동 허용하지 않습니다. 승인만으로 SQL이 실행되지 않으며 원래 요청자의 별도 execute가 필요합니다. 정책·카탈로그·DB 대상·역할이 바뀌거나 승인이 만료·취소되면 재사용을 거부합니다. 기본값은 검증용 정책이며 운영 규모에 적합한 한도로 검증됐다는 뜻은 아닙니다.

## 대시보드

왼쪽 메뉴에 보안 현황, 승인 검토, 날짜별 감사 기록, 작동 테스트가 있습니다. 승인 검토에서 반복 업무 범위를 발급·조회·취소하고 신원별 누적 사용량을 확인합니다. 보고서는 실제 반환 행의 내용 대신 요청·판단·반환량·처리 이력을 보여줍니다.

## 문서와 테스트

- [설계계획서](docs/POLICY_GATEWAY_IMPLEMENTATION_PLAN.md)
- [적용 내용 상세 설명](docs/POLICY_GATEWAY_CHANGES.md)
- [테스트 절차·실제 결과](testing/TEST_GUIDE.md)
- [지금 테스트 시작하기](testing/START_HERE.md)
- [PostgreSQL 연결](docs/POSTGRESQL_CONNECTION.md)
- [2,700행 보존형 가상 DB](testing/VALIDATION_DB_GUIDE.md)
- [API](docs/api.md)
- [GitHub 푸시 준비와 검증 요약](docs/GITHUB_PUSH_READY.md)

```powershell
.\testing\setup.ps1
.\scripts\build_exe.ps1
.\testing\run_tests.ps1
.\.venv\Scripts\python.exe -m testing.postgresql_checks --policy-controls
```

정책 파일은 `config/db_access.json`, 기존 문서·산출물·모의 전송함 도구 정책은 `config/policy.yaml`입니다. 기존 데이터에는 `004_db_policy_grants.sql` 마이그레이션이 필요합니다. SQLite는 새 테이블을 자동 추가합니다.

과거 모델·외부 데이터셋 평가 기록은 역사적 자료이며 현재 기능의 성능 주장에 사용하지 않습니다. 실제 사내 스키마·기업 IdP·운영 인증서·네트워크 격리·생산 처리량 검증은 별도입니다. 라이선스: [MIT](LICENSE).
