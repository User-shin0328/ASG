# ASG Test Tools & Temporary Workspace (`test_tools/`)

이 디렉터리는 **ASG (AI Agent Secure Gateway)**의 로컬 통합 테스트 실행기, 대화형 공격 시뮬레이터, 그리고 개발/검증 중 잠깐 사용할 임시 파일들을 모아 관리하는 전용 폴더입니다.

---

## 📁 디렉터리 구성

| 파일 / 폴더 | 용도 | 실행 방법 |
| :--- | :--- | :--- |
| **`run_asg_testbed.bat`** | 로컬 게이트웨이(8000) + 샌드박스(8001) + SOC 대시보드(8501) 통합 실행기 | 탐색기에서 **더블클릭** |
| **`run_asg_testbed.ps1`** | PowerShell 터미널 전용 테스트베드 실행 스크립트 | `.\run_asg_testbed.ps1` |
| **`run_attack_generator.bat`** | 대화식 공격 시뮬레이터 (8대 공격/검증 시나리오 및 커스텀 프롬프트) | 탐색기에서 **더블클릭** |
| **`run_attack_generator.ps1`** | PowerShell 터미널 전용 공격 시뮬레이터 스크립트 | `.\run_attack_generator.ps1` |
| **`temp/`** | **임시 테스트 파일 및 단발성 디버그 스크립트 전용 보관소** | 자유롭게 파일 생성 및 테스트 |

---

## 🛡️ 임시 파일 보관 (`temp/`) 정책

- 개발 또는 테스트 시 잠깐 생성하는 스크립트(`*.py`), 임시 JSON 데이터, 디버그 로그 파일 등은 **`test_tools/temp/`** 폴더에 넣고 작업하시면 됩니다.
- `.gitignore` 규칙에 의해 `test_tools/temp/` 내의 파일들은 `.gitkeep`을 제외하고 Git 커밋/푸시 대상에서 **자동 제외**되므로 저장소가 오염되지 않고 깔끔하게 유지됩니다.
