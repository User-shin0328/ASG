# 실행·검증 안내

1. `testing/setup.ps1`로 테스트 환경을 준비합니다.
2. `scripts/build_exe.ps1`로 현재 소스의 ASG.exe를 만듭니다.
3. `testing/run_tests.ps1`로 회귀·HTTP·실행파일 검증을 수행합니다.
4. `python -m testing.postgresql_checks --policy-controls`로 별도 PostgreSQL과 독립 Gateway 연결 두 개의 경쟁을 검증합니다.
5. 가상 데이터 보존 환경은 [VALIDATION_DB_GUIDE](../testing/VALIDATION_DB_GUIDE.md)를 따릅니다. 기존 DB에는 004 마이그레이션이 필요합니다.

기본 실행파일은 SQLite 로컬 검증용입니다. 정책 파일을 바꿔 재기동하면 이전 정책의 대기·승인·범위 승인은 재사용하지 않습니다. 요청당·누적 한도는 config/db_access.json에 명시합니다.

응답 유실로 결과 확인 필요가 된 요청은 보고서의 영수증 대조 기능으로 확인합니다. 대조는 새 SQL을 실행하지 않으며, 영수증이 없으면 예약을 임의 환급하지 않습니다. 별도 운영자의 안전한 조사 절차가 필요합니다.

기존 Ollama·의미 분류기·모델 실행 설정은 제거했습니다. 호스트에 설치된 다른 소프트웨어는 관리하지 않습니다.
