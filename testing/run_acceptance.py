"""Run regressions, real local HTTP scenarios and a portable EXE check; retain evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import closing

from scripts.testbed_launcher import LocalLab
from scripts.traffic_generator import TrafficGenerator, send_request

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))


def update_combined_guide(report_text):
    """Keep procedures, expected outcomes and observed results together in one Markdown file."""
    guide_path=ROOT/'testing/TEST_GUIDE.md'
    if not guide_path.exists():
        return
    marker='<!-- ASG_RESULT_BEGIN -->'
    base=guide_path.read_text(encoding='utf-8').split(marker,1)[0].rstrip()
    embedded=report_text.replace('# ASG 실제 테스트 결과보고서','## 11. 실제 테스트 결과보고서',1)
    embedded=re.sub(r'^## (?!11\.)','### ',embedded,flags=re.MULTILINE)
    embedded=embedded.replace('(../../TEST_GUIDE.md)','(TEST_GUIDE.md)')
    for name in ('results.json','unittest.log','audit-events.json','exe-smoke.log'):
        embedded=embedded.replace(']('+name+')','](results/latest/'+name+')')
    guide_path.write_text(base+'\n\n'+marker+'\n\n'+embedded+'\n<!-- ASG_RESULT_END -->\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--skip-exe',action='store_true')
    args=parser.parse_args()
    output=ROOT/'testing/results/latest'
    output.mkdir(parents=True,exist_ok=True)
    checks=[]

    def record(name, expected, actual, passed):
        checks.append({'id':f'T{len(checks)+1:02}', 'name':name,'expected':expected,'actual':actual,'status':'PASS' if passed else 'FAIL'})
        print(f"{checks[-1]['id']} {checks[-1]['status']} {name}",flush=True)

    started=datetime.now(KST)
    regression=subprocess.run([sys.executable,'-m','unittest','discover','-v'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    log=regression.stdout+regression.stderr
    (output/'unittest.log').write_text(log,encoding='utf-8')
    match=re.search(r'Ran (\d+) tests',log)
    record('기존·추가 회귀 테스트','전체 테스트 성공',{'exit_code':regression.returncode,'tests':int(match.group(1)) if match else None},regression.returncode==0)
    with tempfile.TemporaryDirectory(prefix='asg-acceptance-') as temp:
        lab=LocalLab(Path(temp),0,0,0).start()
        gen=TrafficGenerator(lab.gateway_url,lab.tokens['agent-alice'],lab.tokens['agent-bob'],lab.tokens['reviewer-demo'])
        agent_headers=gen._headers(lab.tokens['agent-alice'])
        reviewer_headers=gen._headers(lab.tokens['reviewer-demo'])
        try:
            status,health=send_request(lab.url+'/health/ready')
            record('3개 서비스 준비 확인','200 ready',health,status==200 and health.get('status')=='ready')
            result=gen.run_normal_read()
            record('배정 문서 읽기','200 ALLOW SUCCEEDED',result,result['status']==200 and result['result'].get('state')=='SUCCEEDED')
            with closing(sqlite3.connect(Path(temp)/'tools.sqlite3')) as db:
                before=[db.execute('select count(*) from '+table).fetchone()[0] for table in ('artifacts','outbox','receipts')]
            result=gen.run_cross_tenant_violation()
            with closing(sqlite3.connect(Path(temp)/'tools.sqlite3')) as db:
                after=[db.execute('select count(*) from '+table).fetchone()[0] for table in ('artifacts','outbox','receipts')]
            record('테넌트 경계와 부작용','403 DENY, 산출물/전송함/영수증 증가 없음',{'response':result,'before':before,'after':after},result['status']==403 and result['result'].get('decision')=='DENY' and before==after)
            for name,run in [('프롬프트 인젝션',gen.run_prompt_injection_inspection),('유니코드 은닉',gen.run_unicode_obfuscation)]:
                result=run()
                record(name,'200 SUSPICIOUS',result,result['status']==200 and result['result'].get('verdict')=='SUSPICIOUS')
            result=gen.run_custom_prompt('Please summarize the assigned report.')
            record('정상 입력 검사','200 CLEAR',result,result['status']==200 and result['result'].get('verdict')=='CLEAR')
            result=gen.run_unapproved_report_submit()
            pending=result['result']
            record('실제 산출물 생성과 승인 대기','202 REQUIRE_APPROVAL PENDING_APPROVAL',result,result['status']==202 and pending.get('state')=='PENDING_APPROVAL')
            action_id=pending.get('action_id','missing')
            approval_id=pending.get('approval_id','missing')
            status,blocked=send_request(lab.gateway_url+f'/v1/actions/{action_id}/execute','POST',agent_headers,{})
            with closing(sqlite3.connect(Path(temp)/'tools.sqlite3')) as db:
                count=db.execute('select count(*) from outbox').fetchone()[0]
            record('승인 전 실행 차단','409 ACTION_NOT_EXECUTABLE, outbox 0건',{'status':status,'response':blocked,'outbox':count},status==409 and blocked.get('error')=='ACTION_NOT_EXECUTABLE' and count==0)
            status,decision=send_request(lab.gateway_url+f'/v1/approvals/{approval_id}/decision','POST',reviewer_headers,{'decision':'approve'})
            record('검토자 승인','200 APPROVED',{'status':status,'response':decision},status==200 and decision.get('state')=='APPROVED')
            status,done=send_request(lab.gateway_url+f'/v1/actions/{action_id}/execute','POST',agent_headers,{})
            status2,again=send_request(lab.gateway_url+f'/v1/actions/{action_id}/execute','POST',agent_headers,{})
            with closing(sqlite3.connect(Path(temp)/'tools.sqlite3')) as db:
                count=db.execute('select count(*) from outbox').fetchone()[0]
            record('승인 후 실행·재실행 중복 방지','200 SUCCEEDED, 재실행 후에도 outbox 1건',{'status':status,'response':done,'repeat_status':status2,'repeat':again,'outbox':count},status==200 and done.get('state')=='SUCCEEDED' and count==1)
            result=gen.run_audit_verify()
            record('감사 해시 연결','200 VALID, 검증 건수 > 0, 변조 0',result,result['status']==200 and result['result'].get('status')=='VALID' and result['result'].get('chained_records',0)>0 and not result['result'].get('tampered_record_ids'))
            status,bad=send_request(lab.url+'/api/generate?mode=normal','POST',{'Origin':'https://untrusted.test','X-ASG-Request':'1'},{})
            record('다른 사이트에서 테스트 실행 차단','403 SAME_ORIGIN_REQUIRED',{'status':status,'response':bad},status==403)
            status,direct=send_request(f'http://127.0.0.1:{lab.servers[0].server_port}/internal/artifacts/missing')
            record('도구 직접 접근 인증','401 UNAUTHENTICATED',{'status':status,'response':direct},status==401)
            status,audit=send_request(lab.url+'/v1/audit/events')
            (output/'audit-events.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
            record('대시보드 감사 연결','200, 실제 감사 이벤트 > 0',{'status':status,'count':len(audit.get('items',[]))},status==200 and len(audit.get('items',[]))>0)
            db_args={'dataset_id':'operations','columns':['ticket_id','status'],'filters':{},'row_limit':25,'purpose':'승인 기반 DB 조회 통합 검증입니다.'}
            db_headers=dict(agent_headers,**{'Idempotency-Key':str(uuid.uuid4())})
            status,requested=send_request(lab.gateway_url+'/v1/db/requests','POST',db_headers,db_args)
            record('DB 접근 요청·보안 에이전트 분석','202 PENDING_APPROVAL, 분석 근거와 추천 대응 제공',requested,status==202 and requested.get('state')=='PENDING_APPROVAL' and bool(requested.get('analysis',{}).get('recommendation')))
            db_id=requested.get('id','missing');db_url=lab.gateway_url+'/v1/db/requests/'+db_id
            status,blocked=send_request(db_url+'/execute','POST',agent_headers,{})
            record('사람 승인 전 DB 조회 차단','409 DB_APPROVAL_REQUIRED',{'http':status,'response':blocked},status==409 and blocked.get('error')=='DB_APPROVAL_REQUIRED')
            status,approved=send_request(db_url+'/decision','POST',reviewer_headers,{'decision':'approve','reason':'업무 범위와 열·조회량을 확인했습니다.'})
            record('판단 근거를 포함한 사람 승인','200 APPROVED',approved,status==200 and approved.get('state')=='APPROVED' and bool(approved.get('review_reason')))
            status,executed=send_request(db_url+'/execute','POST',agent_headers,{})
            _,repeated=send_request(db_url+'/execute','POST',agent_headers,{})
            record('승인 후 실제 SQL 조회·영수증 재사용','25행 조회, 동일 영수증으로 재실행 응답',{'http':status,'row_count':executed.get('result_count'),'receipt_id':executed.get('receipt_id'),'repeat_receipt':repeated.get('receipt_id'),'replayed':repeated.get('replayed')},status==200 and executed.get('result_count')==25 and repeated.get('replayed') and executed.get('receipt_id')==repeated.get('receipt_id'))
            for case in ('sensitive','bulk','abnormal'):
                http,result=send_request(lab.url+'/api/db-demo','POST',{'X-ASG-Request':'1'},{'scenario':case})
                expected='DENIED' if case=='abnormal' else 'PENDING_APPROVAL'
                record('DB 분석 시나리오 '+case,expected,result,http==200 and result.get('request',{}).get('state')==expected)
            service=lab.gateway.db_access
            rows=[{'requested_at':10000,'sensitive':1,'bulk':1,'abnormal':1}]
            scores=[service.risk_at(rows,at)['score'] for at in (10000,10900,11800)]
            record('30분 위험도 증가·감쇠·소멸','42 → 21 → 0',scores,scores==[42,21,0])
            http,overview=send_request(lab.url+'/v1/db/overview')
            metrics=overview.get('metrics',{})
            record('현재 위험도·일일 처리 집계','대기+허용+차단=오늘 요청 수, 실제 위험 요인 포함',overview,http==200 and metrics.get('today_total')==sum(metrics.get(k,0) for k in ('pending','allowed','blocked')) and overview.get('risk',{}).get('score',0)>0)
            http,report_data=send_request(lab.url+'/v1/db/requests/'+db_id)
            (output/'db-access-report.json').write_text(json.dumps(report_data,ensure_ascii=False,indent=2),encoding='utf-8')
            record('언제·어디서·누가·무엇·결과의 보고서','메타데이터, 보안 분석, 검토 근거, 처리 이력 보존',{'http':http,'report':report_data},http==200 and bool(report_data.get('source_ip')) and len(report_data.get('timeline',[]))>=4)
            http,diagnostic=send_request(lab.url+'/v1/db/diagnostics','POST',{'X-ASG-Request':'1'},{},timeout=15)
            record('원클릭 실제 작동 점검','연결·분석·DB·무결성 모든 점검 통과',diagnostic,http==200 and diagnostic.get('passed') is True)
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(8) as pool:
                concurrent=list(pool.map(lambda _:send_request(lab.url+'/v1/db/requests?pending=true')[0],range(80)))
            record('동시 대시보드 조회 인증 안정성','80개 요청 모두 200',{'total':len(concurrent),'successful':concurrent.count(200)},all(code==200 for code in concurrent))
            ports=[s.server_port for s in lab.servers]
        finally:
            lab.stop()
        closed=[]
        for port in ports:
            with socket.socket() as sock:
                closed.append(sock.connect_ex(('127.0.0.1',port))!=0)
        record('정상 종료 시 포트 반환','3개 포트 모두 연결 불가',closed,all(closed))

    exe=ROOT/'ASG.exe'
    exe_meta=None
    if not args.skip_exe and exe.exists():
        exe_meta={'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'bytes':exe.stat().st_size}
        with tempfile.TemporaryDirectory(prefix='ASG-portable-') as tmp:
            portable=Path(tmp)/'독립 실행 검증'
            portable.mkdir()
            shutil.copy2(exe,portable/'ASG.exe')
            runtime=portable/'data'
            process=subprocess.Popen([str(portable/'ASG.exe'),'--no-browser','--gateway-port','0','--tool-port','0','--dashboard-port','0','--data-dir',str(runtime),'--smoke-seconds','14'],cwd=portable,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            portable_result={}
            try:
                deadline=time.monotonic()+35
                while time.monotonic()<deadline and process.poll() is None:
                    session=runtime/'session.json'
                    if session.exists():
                        portable_result=json.loads(session.read_text(encoding='utf-8'))
                        break
                    time.sleep(.2)
                url=portable_result.get('dashboard','http://127.0.0.1:1')
                code,health=send_request(url+'/health/ready')
                scenarios={}
                for scenario in ('normal','cross-tenant','injection','obfuscation','unapproved','audit-verify'):
                    status,data=send_request(url+'/api/generate?mode='+scenario,'POST',{'X-ASG-Request':'1'},{})
                    scenarios[scenario]={'http':status,'data':data}
                body=scenarios['unapproved']['data']
                success=code==200 and all(r['http']==200 for r in scenarios.values()) and scenarios['normal']['data'].get('result',{}).get('state')=='SUCCEEDED' and body.get('status')==202
                record('독립 EXE 기동과 6개 시나리오','원본 폴더/Python 없이 실행, ready, 모든 시나리오 응답',{'health':health,'scenarios':scenarios,'binary':exe_meta},success)
                db_samples={}
                for scenario in ('normal','sensitive','bulk','abnormal'):
                    http,data=send_request(url+'/api/db-demo','POST',{'X-ASG-Request':'1'},{'scenario':scenario})
                    db_samples[scenario]={'http':http,'state':data.get('request',{}).get('state'),'risk':data.get('request',{}).get('risk_score')}
                http,check=send_request(url+'/v1/db/diagnostics','POST',{'X-ASG-Request':'1'},{},timeout=15)
                record('독립 EXE의 DB 요청·분석·작동 진단','정상·민감·대량은 승인 대기, 비정상은 차단, 진단 통과',{'scenarios':db_samples,'diagnostic':check},http==200 and check.get('passed') and all(v['http']==200 and v['state']==('DENIED' if k=='abnormal' else 'PENDING_APPROVAL') for k,v in db_samples.items()))
                stdout,_=process.communicate(timeout=35)
                (output/'exe-smoke.log').write_text(stdout,encoding='utf-8')
                record('EXE 자동 종료','exit 0',{'exit_code':process.returncode},process.returncode==0)
            except Exception as exc:
                record('독립 EXE 실행','성공',{'error':str(exc)},False)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
    else:
        checks.append({'id':'EXE','name':'독립 EXE','expected':'실행 확인','actual':'--skip-exe 선택 또는 ASG.exe 없음','status':'NOT_RUN'})

    completed=datetime.now(KST)
    result='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PARTIAL' if any(c['status']=='NOT_RUN' for c in checks) else 'PASS'
    report={'result':result,'started':started.isoformat(),'completed':completed.isoformat(),'python':sys.version,'platform':sys.platform,'executable':exe_meta,'checks':checks,'not_run':['Docker 다중 네트워크 격리·PostgreSQL 실동작','외부 LLM 및 외부 데이터셋 평가','코드 서명·다른 Windows PC 실행']}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# ASG 실제 테스트 결과보고서','',f'- 실행: {started:%Y-%m-%d %H:%M:%S} ~ {completed:%H:%M:%S} (Asia/Seoul)',f'- 전체 판정: **{result}**',f'- Python: {sys.version.split()[0]} / {sys.platform}','- 로컬 HTTP·SQLite·모의 전송함을 사용했습니다. 실제 외부 발송은 없습니다.','', '| ID | 테스트 | 결과 |','|---|---|---|']
    lines += [f"| {c['id']} | {c['name']} | {c['status']} |" for c in checks]
    for check in checks:
        lines += ['',f"## {check['id']}. {check['name']}",'',f"- 예상 결과: {check['expected']}",f"- 실제 판정: **{check['status']}**",'- 관찰값 및 응답 원문:','','```json',json.dumps(check['actual'],ensure_ascii=False,indent=2),'```']
    lines += ['','## 미실행 범위','']+['- '+item+': NOT_RUN' for item in report['not_run']]
    lines += ['','## 재현과 증거','','- 단계별 설명: [TEST_GUIDE.md](../../TEST_GUIDE.md)','- 구조화 결과: [results.json](results.json)','- 회귀 테스트 로그: [unittest.log](unittest.log)','- 감사 이벤트: [audit-events.json](audit-events.json)','- 실행파일 로그: [exe-smoke.log](exe-smoke.log)','- 테스트는 별도 임시 디렉터리를 사용하며 사용자 실행 데이터는 삭제하지 않습니다.']
    report_text='\n'.join(lines)+'\n'
    (output/'REPORT.md').write_text(report_text,encoding='utf-8')
    update_combined_guide(report_text)
    # A dated copy preserves the current acceptance evidence while latest can be regenerated.
    snapshot=ROOT/'testing/results'/started.strftime('%Y%m%d-%H%M%S')
    shutil.copytree(output,snapshot)
    print(f'{result}: {output / "REPORT.md"}',flush=True)
    return 1 if result=='FAIL' else 0


if __name__=='__main__':
    raise SystemExit(main())
