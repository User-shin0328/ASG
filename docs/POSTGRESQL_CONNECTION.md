# PostgreSQL 보호 DB 연결

사용자가 선택한 실제 사내 DB 종류는 PostgreSQL입니다. 이 문서는 연결 기능과 재현 절차를 설명하며, 운영 DB가 연결됐다는 뜻은 아닙니다.

## 1. 두 저장소를 구분합니다

| 저장소 | 용도 | 연결 정보를 받는 서비스 |
|---|---|---|
| 게이트웨이 PostgreSQL | 인증·정책·승인·감사 기록 | gateway / migrate |
| 보호 PostgreSQL | 승인 뒤 업무 데이터를 SELECT | tool-sandbox만 |

기존 `compose.yaml`의 PostgreSQL은 첫 번째 저장소입니다. `compose.postgresql-target.yaml`을 함께 사용하면 두 번째 DB를 별도로 연결합니다. 사내 에이전트와 브라우저에 DB 비밀번호를 전달하지 않습니다. 기본 `ASG.exe`는 계속 SQLite 가상 데이터 검증 환경으로 실행됩니다. 보호 PostgreSQL 연결은 아래 컨테이너 구성을 기준으로 설정합니다.

## 2. DBA가 읽기 대상을 준비합니다

프로그램은 운영 DB에 테이블·뷰·사용자·가상 데이터를 자동 생성하지 않습니다. 서버 카탈로그의 논리 대상 세 개를 `asg_access` 스키마의 읽기 테이블 또는 검토된 뷰로 제공해야 합니다.

| 관계 이름 | 필요한 열 |
|---|---|
| asg_operations | tenant, ticket_id, category, status, description |
| asg_directory | tenant, employee_id, name, department, work_email |
| asg_payroll | tenant, employee_id, department, salary, bank_account |

기존 사내 테이블 이름·구조가 다르면 DBA가 뷰로 위 이름과 열을 대응시키거나 서버 카탈로그를 검토해 변경합니다. 실제 업무 스키마가 주어지지 않았으므로 이 매핑은 아직 하지 않았습니다. `tenant`는 현재 데모 principal의 `north`/`south` 범위와 대응하며, 실제 조직·역할 매핑과 기업 IdP 연결도 별도 작업입니다.

전용 계정은 객체 소유자·관리자·BYPASSRLS 계정이 아니어야 합니다. 스키마 USAGE와 등록 관계 SELECT만 부여하고 DML·DDL·임의 함수 실행 권한을 주지 않습니다. 아래는 DBA가 대상을 확인한 뒤 적용할 권한 예시이며 프로그램이 자동 실행하지 않습니다.

```sql
-- asg_reader 계정 생성과 비밀번호 설정은 사내 비밀 관리 절차로 별도 수행합니다.
GRANT USAGE ON SCHEMA asg_access TO asg_reader;
GRANT SELECT ON asg_access.asg_operations,
                asg_access.asg_directory,
                asg_access.asg_payroll TO asg_reader;
```

현재 서버 쿼리는 테넌트 조건을 강제합니다. DB 계정 자체의 테넌트별 RLS 분리는 자동 구성하지 않으므로, 계정 탈취까지 고려한 DB 권한 설계는 DBA가 추가해야 합니다. 뷰의 내부 함수·조인·권한도 검토해야 하며 임의 뷰의 안전성을 프로그램이 증명하지 않습니다.

## 3. 비밀 파일과 대상 ID를 설정합니다

1. 로컬에서 `config/protected_db_dsn.example`을 참고해 `secrets/protected_db_dsn.txt`를 작성합니다. 값은 채팅·명령 인자·Git에 넣지 않습니다.
2. 사내 CA 인증서를 `secrets/protected_db_ca.crt`에 둡니다. `sslmode=verify-full`과 DB 인증서의 호스트 이름이 일치해야 합니다.
3. `.env`에 공개 설정 `PROTECTED_DB_TARGET_ID=corporate-reporting-v1`과 필요하면 `PROTECTED_DB_SCHEMA=asg_access`를 추가합니다. 비밀번호가 아닙니다.
4. 두 서비스가 같은 대상 ID를 사용해야 합니다. 호스트·DB·스키마·뷰 매핑을 바꿀 때 대상 ID 버전도 변경해 새 요청과 승인을 받습니다.

대상 ID는 승인 정책 해시에 포함되고 실행 계층에서도 대조합니다. **접속 파일을 바꾸면서 ID를 유지한 구성 변경까지 자동 탐지하지는 않습니다.** 기존 대기 요청은 새 대상으로 재사용하지 마세요. 이번 정책 바인딩 형식 변경 이전의 대기·승인 요청도 새로 제출해야 합니다.

인증서 검증 모드는 PostgreSQL [공식 TLS 문서](https://www.postgresql.org/docs/17/libpq-ssl.html)를 따릅니다. 복호화 가능한 환경 변수 DSN 대신 도구 서비스 전용 파일로 전달합니다. 파일과 호스트의 접근 권한은 운영자가 제한해야 합니다.

## 4. 컨테이너 설정을 확인하고 실행합니다

기존 로컬 데모의 토큰·감사 DB 비밀 파일을 먼저 준비한 상태에서 실행합니다.

```powershell
docker compose -f compose.yaml -f compose.postgresql-target.yaml config --quiet
docker compose -f compose.yaml -f compose.postgresql-target.yaml up --build -d
```

이 명령은 사내 연결 정보가 준비된 운영자가 실행할 절차이며, 이번 작업에서는 사내 DB를 대상으로 실행하지 않았습니다. 도구 서비스에만 외부 DB용 네트워크와 DSN·CA 비밀 파일을 붙입니다. 추가 bridge는 자체 목적지 방화벽이 아니므로 실제 배포에서는 승인한 DB 호스트·포트만 허용하는 네트워크 ACL이 필요합니다.

사내 에이전트 → 게이트웨이 요청 → 보안 분석 → 사람 승인 → 원래 요청자의 실행 흐름은 동일합니다. 원클릭 작동 점검에서 PostgreSQL 읽기 전용 연결과 세 관계의 열·SELECT 권한을 확인합니다. 확인되지 않으면 빨간 상태를 표시하며 SQLite로 대체하지 않습니다.

## 5. 실제 조회 시 강제하는 제한

- 임의 SQL·테이블 이름을 요청받지 않고 등록된 열과 필터 값만 받습니다.
- SQL 식별자는 psycopg의 Identifier, 값은 바인딩 매개변수로 전달합니다.
- 전용 연결마다 READ ONLY 트랜잭션, 연결 2초·쿼리 2초·잠금 0.5초 제한을 사용합니다.
- 슈퍼유저·BYPASSRLS 계정은 거부합니다. 트랜잭션 설정과 연결 종료는 [psycopg 공식 문서](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)의 방식을 사용합니다.
- 결과 행은 에이전트에만 반환하며 보고서에는 대상·판단·반환량·이력을 저장합니다. PostgreSQL Decimal은 정밀도를 잃지 않게 문자열로 반환합니다.
- 실행 영수증·모의 전송함·기존 문서 기능은 도구 서비스의 별도 SQLite 저장소를 계속 사용합니다. 보호 DB에 감사 기록을 쓰지 않습니다.

## 6. 사내 연결 없이 재현하는 순서

```powershell
.\testing\setup.ps1
.\.venv\Scripts\python.exe -m testing.postgresql_checks
```

Docker가 켜져 있고 로컬에 `postgres:17.11-alpine` 이미지가 필요합니다. 없으면 먼저 `docker pull postgres:17.11-alpine`로 받습니다. 테스트는 무작위 이름의 임시 컨테이너를 만들고 루프백 임시 포트만 열며 테스트 종료 시 자신이 만든 컨테이너와 볼륨만 정리합니다. 기존 컨테이너·데이터·운영 주소를 사용하지 않습니다. 테스트 계정·비밀번호는 무작위 생성하고 출력하지 않습니다.

| 순서 | 예상 결과 |
|---|---|
| 1 | 게이트웨이 감사 DB와 보호 DB 모두 PostgreSQL 연결 정상 |
| 2 | 승인 전 실행 409 |
| 3 | 사람 승인 후 실제 2행 조회, 요청자의 north 범위만 반환 |
| 4 | 같은 요청 재실행은 같은 영수증 반환 |
| 5 | 감사 보고서에 PostgreSQL 대상·반환량·처리 이력 저장 |
| 6 | SQL 삽입 모양의 필터는 단순 값으로 처리, 0행 |
| 7 | 미등록 열은 403 차단 |
| 8 | READ ONLY 트랜잭션에서 INSERT 거부 |
| 9 | 읽기 계정의 DB 권한으로 DELETE 거부 |
| 10 | 승인 후 대상 ID 변경 시 실행 403 |
| 11 | 도구 서비스의 대상 ID 불일치도 거부 |
| 12 | DB 연결 오류 시 빨간 상태, 비밀번호·DSN 미노출 |
| 13 | 연결 복구 후 원클릭 진단과 감사 체인 정상 |
| 14 | 보호 DB의 가상 데이터 4행이 그대로 보존 |

실제 결과와 관찰값은 [PostgreSQL 결과보고서](../testing/results/postgresql/REPORT.md)에 저장합니다. 브라우저에서 가상 PostgreSQL 화면을 직접 확인하려면 같은 명령에 `--preview`를 붙이고 출력된 루프백 주소를 엽니다. 확인을 마친 뒤 콘솔에서 Enter를 눌러 정리합니다.

이 검증은 기능·권한·오류 처리 검증입니다. 실제 사내 스키마 매핑, 운영 인증서 배포, 기업 IdP, 운영 네트워크 격리를 검증한 결과가 아닙니다.
