# 호환 실행 도구

- `run_asg_testbed.bat` / `.ps1`: 루트의 새 `ASG.exe` 실행. 실행파일이 없으면 구축한 `.venv`의 소스 실행기로 연결합니다.
- `run_attack_generator.bat` / `.ps1`: 현재 로컬 대시보드 `http://127.0.0.1:18511`에 연결하는 콘솔 시뮬레이터입니다. 먼저 ASG를 실행하세요.
- 콘솔만 다른 포트에 연결: `.\.venv\Scripts\python.exe -m testing.console --dashboard http://127.0.0.1:18512` (프로젝트 루트에서 실행).
- `temp/`: 기존 임시 작업 위치. 새 자동 테스트와 결과는 `testing/`에서 관리합니다.

환경 구축·순서·예상 결과·실제 보고서는 [상세 테스트 설명서](../testing/TEST_GUIDE.md)를 확인하세요. 기본 게이트웨이·샌드박스 포트는 자동 배정됩니다.
