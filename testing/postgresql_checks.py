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
import tempfile
import time
import uuid
from unittest.mock import patch

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg import sql

from scripts.testbed_launcher import LocalLab
from scripts.traffic_generator import send_request
from tool_sandbox import protected_db

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',action='store_true',help='Keep the fictional lab open until Enter is pressed')
    args=parser.parse_args()
    name='asg-pg-check-'+uuid.uuid4().hex[:10]
    secret=secrets.token_urlsafe(40)
    role_secret=secrets.token_urlsafe(40)
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
            folder=cleanup.enter_context(tempfile.TemporaryDirectory(prefix='asg-pg-functional-'))
            temp=Path(folder)
            env=os.environ.copy()|{'POSTGRES_PASSWORD':secret}
            docker('run','--rm','-d','--name',name,'--publish','127.0.0.1::5432','--env','POSTGRES_PASSWORD','--env','POSTGRES_DB=gateway','postgres:17.11-alpine',env=env)
            created=True
            port=docker('port',name,'5432/tcp').rsplit(':',1)[1]
            admin=make_conninfo(host='127.0.0.1',port=port,dbname='gateway',user='postgres',password=secret,sslmode='disable',connect_timeout=2)
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
                for role in ('gateway_app','asg_reader'):
                    c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(role),sql.Literal(role_secret)))
                for migration in sorted((ROOT/'migrations').glob('[0-9][0-9][0-9]_*.sql')):
                    c.execute(migration.read_text(encoding='utf-8'))
                c.execute('CREATE DATABASE business')
            business_admin=make_conninfo(admin,dbname='business')
            with psycopg.connect(business_admin,autocommit=True) as c:
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
            reader=make_conninfo(admin,dbname='business',user='asg_reader',password=role_secret)
            dsn.write_text(reader,encoding='utf-8')
            settings={'PROTECTED_DB_BACKEND':'postgresql','PROTECTED_DB_TARGET_ID':'pg-functional-v1',
                      'PROTECTED_DB_SCHEMA':'asg_access','PROTECTED_DB_DSN_FILE':str(dsn),'PROTECTED_DB_LOCAL_TEST':'1'}
            with patch.dict(os.environ,settings):
                gateway_dsn=make_conninfo(admin,user='gateway_app',password=role_secret)
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
                record('사람 승인 후 실제 SELECT와 테넌트 범위',approved==200 and code==200 and len(rows)==2 and all(r['ticket_id'].startswith('north-') for r in rows),{'approved':approved,'execute':code,'row_count':len(rows),'state':result['state']})
                code,replay=execute(request)
                record('재실행 영수증 재사용',code==200 and replay['replayed'] and replay['receipt_id']==result['receipt_id'],{'replayed':replay.get('replayed')})
                code,report=call('/v1/db/requests/'+request['id'],who='reviewer-demo')
                record('PostgreSQL 감사 상세 보고서',code==200 and report['result_count']==2 and report['analysis']['db_target']['backend']=='postgresql' and len(report['timeline'])>=4,{'mode':report['mode'],'events':len(report['timeline'])})
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
                lab.gateway.db_access.target={'backend':'postgresql','id':'pg-functional-v1'}
                with patch.dict(os.environ,{'PROTECTED_DB_TARGET_ID':'other-tool-target'}):
                    try:
                        protected_db.execute_query(None,request['arguments'],'north','report-submitter','pg-functional-v1')
                        mismatch=False
                    except ValueError:mismatch=True
                record('실행 계층도 대상 불일치 거부',mismatch,{'target_mismatch_denied':mismatch})
                dsn.write_text(make_conninfo(reader,port=1),encoding='utf-8')
                code,fault=call('/v1/db/status',who='reviewer-demo')
                record('연결 장애는 빨간 상태이며 인증정보 미노출',code==200 and not fault['all_healthy'] and next(x for x in fault['items'] if x['key']=='protected_db')['status']=='down' and secret not in json.dumps(fault) and role_secret not in json.dumps(fault),{'protected_db':'down'})
                dsn.write_text(reader,encoding='utf-8')
                code,diag=call('/v1/db/diagnostics','POST',{},'reviewer-demo')
                record('복구 후 원클릭 실제 진단과 감사 체인',code==200 and diag['passed'],{'checks':diag['checks']})
                if args.preview:
                    print('PREVIEW '+lab.url,flush=True)
                    input('Press Enter after browser review to stop this disposable lab: ')
                lab.stop();lab=None
            with psycopg.connect(business_admin) as c:
                count=c.execute('SELECT count(*) FROM asg_access.asg_operations').fetchone()[0]
            record('보호 DB 행 보존',count==4,{'rows_after_all_checks':count})
    except Exception as exc:
        # Never emit DSNs or database error detail containing SQL/credentials.
        record_error={'name':'실행 오류','status':'FAIL','actual':{'error_type':type(exc).__name__}}
        checks.append(record_error)
        print('FAIL: '+type(exc).__name__,flush=True)
    finally:
        if lab:lab.stop()
        if created:
            docker('rm','-f','-v',name)
    result='PASS' if checks and all(c['status']=='PASS' for c in checks) else 'FAIL'
    out=ROOT/'testing/results/postgresql'
    out.mkdir(parents=True,exist_ok=True)
    report={'result':result,'started':started,'checks':checks,'scope':'Disposable PostgreSQL 17.11; fictional fixtures. No corporate DB, TLS certificate deployment or Docker network isolation verified.'}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# PostgreSQL 연결 실제 검증 결과','',f'- 판정: **{result}**',f'- 시작: {started}','- 임시 PostgreSQL 17.11, 가상 데이터, 게이트웨이 감사 DB와 보호 DB 분리. 운영 DB 미접속.','', '| 검증 | 결과 |','|---|---|']
    lines += [f"| {c['name']} | {c['status']} |" for c in checks]
    lines += ['', '관찰값: [results.json](results.json)', '', '운영 인증서 배포·사내 DB·기업 IdP·Docker 네트워크 격리는 이 결과의 검증 범위가 아닙니다.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0 if result=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
