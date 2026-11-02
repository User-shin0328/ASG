"""Disposable PostgreSQL functional checks. Never uses a corporate DB or existing volumes."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from contextlib import ExitStack
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import shutil
import tempfile
import time
import uuid
from unittest.mock import patch
from urllib.parse import urlparse

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from scripts.testbed_launcher import LocalLab
from scripts.traffic_generator import send_request
from tool_sandbox import protected_db

ROOT=Path(__file__).resolve().parents[1]


def embed_retained_report(report_text):
    guide=ROOT/'testing/VALIDATION_DB_GUIDE.md'
    if not guide.exists():return
    marker='<!-- ASG_VALIDATION_RESULT_BEGIN -->'
    prefix=guide.read_text(encoding='utf-8').split(marker)[0].rstrip()
    embedded=report_text.replace('(results.json)','(results/postgresql-validation/results.json)').replace('(../../VALIDATION_DB_GUIDE.md)','(VALIDATION_DB_GUIDE.md)')
    guide.write_text(prefix+'\n\n'+marker+'\n\n'+embedded+'\n<!-- ASG_VALIDATION_RESULT_END -->\n',encoding='utf-8')


def run_retained_checks(record,call,create,approve,execute):
    with protected_db.readonly_connection() as (c,_):
        samples={}
        for table in ('asg_operations','asg_directory','asg_payroll'):
            total=c.execute(sql.SQL('SELECT count(*) AS total FROM {}').format(sql.Identifier('asg_access',table))).fetchone()['total']
            rows=c.execute(sql.SQL('SELECT * FROM {} ORDER BY 1,2 LIMIT 2').format(sql.Identifier('asg_access',table))).fetchall()
            samples[table]={'rows':total,'fictional_samples':rows}
    out=ROOT/'testing/results/postgresql-validation'
    out.mkdir(parents=True,exist_ok=True)
    (out/'data-samples.json').write_text(json.dumps({'fictional':True,'tables':samples},ensure_ascii=False,indent=2),encoding='utf-8')
    counts={table:value['rows'] for table,value in samples.items()}
    record('세 종류 가상 데이터 2,700행 적재',counts=={'asg_operations':2400,'asg_directory':200,'asg_payroll':100},counts)
    _,directory=create(dataset_id='employee-directory',columns=['employee_id','work_email'],row_limit=10)
    approve(directory)
    code,result=execute(directory)
    rows=result['result']['result']['rows']
    record('민감 연락처의 승인 후 실제 조회',code==200 and directory['analysis']['sensitive'] and len(rows)==10 and all(row['work_email'].endswith('@example.test') for row in rows),{'row_count':len(rows),'sensitive':directory['analysis']['sensitive']})
    _,payroll=create(dataset_id='payroll',columns=['employee_id','salary','bank_account'],row_limit=10)
    approve(payroll)
    code,result=execute(payroll)
    rows=result['result']['result']['rows']
    record('고위험 급여·계좌 가상 데이터 조회',code==200 and payroll['risk_score']>=70 and len(rows)==10 and all(row['bank_account'].startswith('MOCK-ACCOUNT-') for row in rows),{'row_count':len(rows),'risk_score':payroll['risk_score']})
    _,bulk=create(row_limit=1000)
    before,_=execute(bulk)
    approve(bulk)
    code,result=execute(bulk)
    rows=result['result']['result']['rows']
    record('대량 요청의 승인 전 차단·승인 후 1,000행 조회',before==409 and code==200 and bulk['analysis']['bulk'] and len(rows)==1000,{'before_approval':before,'row_count':len(rows)})
    _,rejected=create()
    code,_=call('/v1/db/requests/'+rejected['id']+'/decision','POST',{'decision':'reject','reason':'검증용 거절: 업무 필요성이 부족합니다.'},'reviewer-demo')
    after,_=execute(rejected)
    record('사람이 거절한 요청은 조회 불가',code==200 and after==409,{'decision':code,'execute':after})
    bob_args={'dataset_id':'payroll','columns':['employee_id','salary'],'filters':{},'row_limit':10,'purpose':'다른 조직 급여 접근 차단 검증입니다.'}
    code,bob=call('/v1/db/requests','POST',bob_args,'agent-bob')
    record('다른 테넌트 급여 요청 자동 차단',code==403 and bob['state']=='DENIED',{'status':code,'state':bob['state']})
    code,_=call('/v1/db/requests/'+directory['id']+'/execute','POST',{},'reviewer-demo')
    record('검토자에게 DB 실행 권한을 주지 않음',code==403,{'status':code})
    args={'dataset_id':'operations','columns':['ticket_id'],'filters':{},'row_limit':25,'purpose':'남부 조직 범위만 조회하는 검증입니다.'}
    result=protected_db.execute_query(None,args,'south','report-writer',os.environ['PROTECTED_DB_TARGET_ID'])
    record('실행 계층의 south 행 범위',result['row_count']==25 and all(r['ticket_id'].startswith('south-') for r in result['rows']),{'row_count':result['row_count'],'tenant':'south'})
    today=datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    code,audit=call('/v1/db/requests?date='+today,who='reviewer-demo')
    record('날짜별 감사 DB에서 완료·거절 이력 조회',code==200 and any(r['state']=='SUCCEEDED' for r in audit['items']) and any(r['state']=='REJECTED' for r in audit['items']),{'date':today,'request_count':audit['total']})
    code,overview=call('/v1/db/overview',who='reviewer-demo')
    risk=overview['risk']
    record('민감·대량·비정상 요청이 30분 위험도에 반영',code==200 and 30<=risk['score']<=100 and risk['factors']['sensitive']>=2 and risk['factors']['bulk']>=1 and risk['factors']['abnormal']>=1,{'score':risk['score'],'factors':risk['factors'],'window_seconds':risk['window_seconds']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',action='store_true',help='Keep the fictional lab open until Enter is pressed')
    parser.add_argument('--keep-db',action='store_true',help='Retain a dedicated fictional DB and local connection files')
    parser.add_argument('--reuse',action='store_true',help='Retest the owned fictional DB without reseeding or deleting data')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'testing/.runtime/postgresql-validation')
    args=parser.parse_args()
    if args.reuse and not args.keep_db:parser.error('--reuse requires --keep-db')
    if args.keep_db and args.data_dir.exists() and not args.reuse:
        parser.error('The data directory exists. Use --reuse to preserve and retest it, or choose a new --data-dir.')
    live_session=args.data_dir/'lab/session.json'
    if args.keep_db and live_session.exists():
        active=json.loads(live_session.read_text(encoding='utf-8')).get('dashboard','')
        if urlparse(active).hostname=='127.0.0.1':
            code,health=send_request(active+'/health/ready',timeout=1)
            if code==200 and health.get('status')=='ready':
                parser.error('Close the existing validation dashboard before retesting. DB data and prior reports are preserved.')
    prior=None
    if args.reuse:
        from testing.validation_database import start_and_wait
        prior=start_and_wait(args.data_dir)
    name=('asg-validation-' if args.keep_db else 'asg-pg-check-')+uuid.uuid4().hex[:10]
    gateway_name='asg_validation_gateway' if args.keep_db else 'gateway'
    business_name='asg_validation_business' if args.keep_db else 'business'
    secret=secrets.token_urlsafe(40)
    role_secret=secrets.token_urlsafe(40)
    if prior:
        name=prior['container']
        secret=conninfo_to_dict((args.data_dir/'admin-dsn.txt').read_text(encoding='utf-8'))['password']
        role_secret=conninfo_to_dict((args.data_dir/'protected-dsn.txt').read_text(encoding='utf-8'))['password']
    checks=[]
    lab=None
    def record(label,passed,actual):
        nonlocal lab
        checks.append({'name':label,'status':'PASS' if passed else 'FAIL','actual':actual})
        print(f"{checks[-1]['status']}: {label}",flush=True)
        if not passed:
            if lab:lab.stop();lab=None
            raise AssertionError(label)
    def docker(*args,**kw):
        return subprocess.check_output(['docker',*args],stderr=subprocess.PIPE,**kw).decode().strip()
    started=datetime.now(timezone(timedelta(hours=9))).isoformat()
    created=False
    try:
        with ExitStack() as cleanup:
            if args.keep_db:
                folder=args.data_dir.resolve()
                folder.mkdir(parents=True,exist_ok=args.reuse)
            else:
                folder=cleanup.enter_context(tempfile.TemporaryDirectory(prefix='asg-pg-functional-'))
            temp=Path(folder)
            env=os.environ.copy()|{'POSTGRES_PASSWORD':secret}
            retention=[]
            if args.keep_db and not args.reuse:
                docker('volume','create','--label','asg.validation=fictional',name+'-data')
                retention=['--mount','type=volume,source='+name+'-data,target=/var/lib/postgresql/data']
            else:retention=['--rm']
            if not args.reuse:
                docker('run',*retention,'-d','--name',name,'--label','asg.validation=fictional','--publish','127.0.0.1::5432','--env','POSTGRES_PASSWORD','--env','POSTGRES_DB='+gateway_name,'postgres:17.11-alpine',env=env)
            created=True
            port=docker('port',name,'5432/tcp').rsplit(':',1)[1]
            admin=make_conninfo(host='127.0.0.1',port=port,dbname=gateway_name,user='postgres',password=secret,sslmode='disable',connect_timeout=2)
            if args.keep_db:
                (temp/'admin-dsn.txt').write_text(admin,encoding='utf-8')
                (temp/'session.json').write_text(json.dumps({'container':name,'volume':name+'-data','host':'127.0.0.1','port':int(port),'gateway_database':gateway_name,'protected_database':business_name,'target_id':name,'fictional':True},indent=2),encoding='utf-8')
            deadline=time.monotonic()+40
            while True:
                try:
                    with psycopg.connect(admin,autocommit=True) as c:
                        version=c.execute('SHOW server_version').fetchone()[0]
                    break
                except psycopg.OperationalError:
                    if time.monotonic()>deadline:raise RuntimeError('Disposable PostgreSQL did not become ready') from None
                    time.sleep(.3)
            with psycopg.connect(admin,autocommit=True) as c:
                if not args.reuse:
                    for role in ('gateway_app','asg_reader'):
                        c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(role),sql.Literal(role_secret)))
                    for migration in sorted((ROOT/'migrations').glob('[0-9][0-9][0-9]_*.sql')):
                        c.execute(migration.read_text(encoding='utf-8'))
                    c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(business_name)))
            business_admin=make_conninfo(admin,dbname=business_name)
            with psycopg.connect(business_admin,autocommit=True) as c:
                if args.keep_db and not args.reuse:
                    c.execute((ROOT/'testing/fixtures/postgresql_validation.sql').read_text(encoding='utf-8'))
                elif not args.reuse:
                    c.execute('CREATE SCHEMA asg_access')
                    c.execute('CREATE TABLE asg_access.asg_operations(tenant text,ticket_id text,category text,status text,description text)')
                    c.execute('CREATE TABLE asg_access.asg_directory(tenant text,employee_id text,name text,department text,work_email text)')
                    c.execute('CREATE TABLE asg_access.asg_payroll(tenant text,employee_id text,department text,salary integer,bank_account text)')
                    for tenant in ('north','south'):
                        for i in range(2):
                            c.execute('INSERT INTO asg_access.asg_operations VALUES(%s,%s,%s,%s,%s)',(tenant,f'{tenant}-{i}','support','open','Fictional PostgreSQL fixture'))
                c.execute('GRANT USAGE ON SCHEMA asg_access TO asg_reader')
                c.execute('GRANT SELECT ON ALL TABLES IN SCHEMA asg_access TO asg_reader')
            dsn=temp/'protected-dsn.txt'
            reader=make_conninfo(admin,dbname=business_name,user='asg_reader',password=role_secret)
            dsn.write_text(reader,encoding='utf-8')
            target_id=name if args.keep_db else 'pg-functional-v1'
            settings={'PROTECTED_DB_BACKEND':'postgresql','PROTECTED_DB_TARGET_ID':target_id,
                      'PROTECTED_DB_SCHEMA':'asg_access','PROTECTED_DB_DSN_FILE':str(dsn),'PROTECTED_DB_LOCAL_TEST':'1'}
            with patch.dict(os.environ,settings):
                gateway_dsn=make_conninfo(admin,user='gateway_app',password=role_secret)
                if args.keep_db:(temp/'gateway-dsn.txt').write_text(gateway_dsn,encoding='utf-8')
                lab=LocalLab(temp/'lab',dashboard_port=0,gateway_database=gateway_dsn).start()
                cleanup.callback(lab.stop)
                def call(path,method='GET',payload=None,who='agent-alice'):
                    return send_request(lab.gateway_url+path,method,{'Authorization':'Bearer '+lab.tokens[who],'Idempotency-Key':str(uuid.uuid4())},payload)
                def create(**overrides):
                    args={'dataset_id':'operations','columns':['ticket_id','status'],'filters':{},'row_limit':25,'purpose':'PostgreSQL 승인 조회 검증입니다.'}|overrides
                    return call('/v1/db/requests','POST',args)
                def execute(request):return call('/v1/db/requests/'+request['id']+'/execute','POST',{})
                def approve(request):return call('/v1/db/requests/'+request['id']+'/decision','POST',{'decision':'approve','reason':'가상 PostgreSQL 요청 범위를 확인했습니다.'},'reviewer-demo')
                code,health=call('/v1/db/status',who='reviewer-demo')
                record('게이트웨이 감사 DB와 보호 DB의 실제 PostgreSQL 연결',code==200 and health['all_healthy'] and lab.gateway.db.is_postgres,{'version':version,'target':health['target'],'items':health['items']})
                code,request=create()
                before,_=execute(request)
                record('승인 전 실행 차단',code==202 and before==409,{'request':code,'execute_before_approval':before})
                approved,_=approve(request)
                code,result=execute(request)
                rows=result['result']['result']['rows']
                expected_rows=25 if args.keep_db else 2
                record('사람 승인 후 실제 SELECT와 테넌트 범위',approved==200 and code==200 and len(rows)==expected_rows and all(r['ticket_id'].startswith('north-') for r in rows),{'approved':approved,'execute':code,'row_count':len(rows),'state':result['state']})
                code,replay=execute(request)
                record('재실행 영수증 재사용',code==200 and replay['replayed'] and replay['receipt_id']==result['receipt_id'],{'replayed':replay.get('replayed')})
                code,report=call('/v1/db/requests/'+request['id'],who='reviewer-demo')
                record('PostgreSQL 감사 상세 보고서',code==200 and report['result_count']==expected_rows and report['analysis']['db_target']['backend']=='postgresql' and len(report['timeline'])>=4,{'mode':report['mode'],'events':len(report['timeline'])})
                _,injected=create(filters={'status':"open' OR 1=1 --"})
                approve(injected)
                code,result=execute(injected)
                record('필터 SQL 삽입을 값으로 처리',code==200 and result['result']['result']['row_count']==0,{'row_count':result['result']['result']['row_count']})
                code,bad=create(columns=['*'])
                record('등록되지 않은 열은 승인 전에 차단',code==403 and bad['state']=='DENIED',{'status':code,'state':bad['state']})
                forbidden=False
                try:
                    with protected_db.readonly_connection() as (c,_):
                        c.execute("INSERT INTO asg_access.asg_operations VALUES('north','bad','bad','bad','bad')")
                except psycopg.errors.ReadOnlySqlTransaction:forbidden=True
                record('DB 트랜잭션 자체가 쓰기 차단',forbidden,{'read_only_transaction_enforced':forbidden})
                forbidden=False
                try:
                    with psycopg.connect(reader,autocommit=True) as c:
                        c.execute('DELETE FROM asg_access.asg_operations')
                except psycopg.errors.InsufficientPrivilege:forbidden=True
                record('읽기 계정의 DB 쓰기 권한 없음',forbidden,{'db_grant_denies_delete':forbidden})
                _,bound=create()
                approve(bound)
                lab.gateway.db_access.target={'backend':'postgresql','id':'different-target-v2'}
                code,denied=execute(bound)
                record('승인 이후 대상 변경 거부',code==403 and denied['error']=='DB_POLICY_CHANGED',{'status':code})
                lab.gateway.db_access.target={'backend':'postgresql','id':target_id}
                with patch.dict(os.environ,{'PROTECTED_DB_TARGET_ID':'other-tool-target'}):
                    try:
                        protected_db.execute_query(None,request['arguments'],'north','report-submitter',target_id)
                        mismatch=False
                    except ValueError:mismatch=True
                record('실행 계층도 대상 불일치 거부',mismatch,{'target_mismatch_denied':mismatch})
                dsn.write_text(make_conninfo(reader,port=1),encoding='utf-8')
                code,fault=call('/v1/db/status',who='reviewer-demo')
                record('연결 장애는 빨간 상태이며 인증정보 미노출',code==200 and not fault['all_healthy'] and next(x for x in fault['items'] if x['key']=='protected_db')['status']=='down' and secret not in json.dumps(fault) and role_secret not in json.dumps(fault),{'protected_db':'down'})
                dsn.write_text(reader,encoding='utf-8')
                code,diag=call('/v1/db/diagnostics','POST',{},'reviewer-demo')
                record('복구 후 원클릭 실제 진단과 감사 체인',code==200 and diag['passed'],{'checks':diag['checks']})
                # Finish the approved target-binding sample so repeated manual use starts cleanly.
                if args.keep_db:
                    execute(bound)
                    run_retained_checks(record,call,create,approve,execute)
                if args.preview:
                    print('PREVIEW '+lab.url,flush=True)
                    input('Press Enter after browser review to stop this disposable lab: ')
                lab.stop();lab=None
            with psycopg.connect(business_admin) as c:
                count=c.execute('SELECT count(*) FROM asg_access.asg_operations').fetchone()[0]
            if args.keep_db:
                docker('restart',name)
                from testing.validation_database import owned_state,refresh_connections
                refresh_connections(temp,owned_state(temp))
                admin=(temp/'admin-dsn.txt').read_text(encoding='utf-8')
                business_admin=make_conninfo(admin,dbname=business_name)
                deadline=time.monotonic()+30
                while True:
                    try:
                        with psycopg.connect(business_admin) as c:
                            after=c.execute('SELECT count(*) FROM asg_access.asg_operations').fetchone()[0]
                        with psycopg.connect(admin) as c:
                            audit_count=c.execute('SELECT count(*) FROM db_access_events').fetchone()[0]
                        break
                    except psycopg.OperationalError:
                        if time.monotonic()>deadline:raise RuntimeError('Retained DB restart failed') from None
                        time.sleep(.3)
                record('DB 재시작 후 가상 데이터·감사 기록 보존',after==2400 and audit_count>0,{'operations_rows':after,'audit_events':audit_count})
            record('보호 DB 행 보존',count==(2400 if args.keep_db else 4),{'rows_after_all_checks':count})
    except Exception as exc:
        # Never emit DSNs or database error detail containing SQL/credentials.
        record_error={'name':'실행 오류','status':'FAIL','actual':{'error_type':type(exc).__name__}}
        checks.append(record_error)
        print('FAIL: '+type(exc).__name__,flush=True)
    finally:
        if lab:lab.stop()
        if created and not args.keep_db:
            docker('rm','-f','-v',name)
    result='PASS' if checks and all(c['status']=='PASS' for c in checks) else 'FAIL'
    out=ROOT/'testing/results'/('postgresql-validation' if args.keep_db else 'postgresql')
    out.mkdir(parents=True,exist_ok=True)
    report={'result':result,'started':started,'checks':checks,'scope':'Disposable PostgreSQL 17.11; fictional fixtures. No corporate DB, TLS certificate deployment or Docker network isolation verified.'}
    if args.keep_db:
        report['scope']='Retained fictional PostgreSQL validation DB. No corporate DB or production network involved.'
        report['database']={'container':name,'gateway_database':gateway_name,'protected_database':business_name,'fictional':True}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# PostgreSQL 연결 실제 검증 결과','',f'- 판정: **{result}**',f'- 시작: {started}','- 임시 PostgreSQL 17.11, 가상 데이터, 게이트웨이 감사 DB와 보호 DB 분리. 운영 DB 미접속.','', '| 검증 | 결과 |','|---|---|']
    lines += [f"| {c['name']} | {c['status']} |" for c in checks]
    for index,check in enumerate(checks,1):
        lines += ['',f"## {index}. {check['name']}",'',f"- 실제 판정: **{check['status']}**",'- 실제 관찰값:','','```json',json.dumps(check['actual'],ensure_ascii=False,indent=2),'```']
    lines += ['', '관찰값: [results.json](results.json)', '', '운영 인증서 배포·사내 DB·기업 IdP·Docker 네트워크 격리는 이 결과의 검증 범위가 아닙니다.']
    if args.keep_db:
        lines += ['', '## 보존된 검증 환경', '', '- 보호 DB: `asg_validation_business`', '- 감사 DB: `asg_validation_gateway`', '- 가상 운영 이력 2,400행 / 임직원 연락처 200행 / 급여·정산 100행', '- DB와 전용 볼륨은 테스트 후에도 보존합니다. 접속 비밀 파일은 Git 제외 경로에만 있습니다.', '- 단계별 재현·예상 결과: [검증 DB 설명서](../../VALIDATION_DB_GUIDE.md)']
    report_text='\n'.join(lines)+'\n'
    (out/'REPORT.md').write_text(report_text,encoding='utf-8')
    if args.keep_db:embed_retained_report(report_text)
    snapshot=ROOT/'testing/results/history'/('retained-' if args.keep_db else 'minimal-')
    snapshot=snapshot/(datetime.fromisoformat(started).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    shutil.copytree(out,snapshot)
    return 0 if result=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
