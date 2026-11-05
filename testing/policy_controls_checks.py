"""Real PostgreSQL checks using two independent Gateway connections and a live tool service."""
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import uuid
from unittest.mock import patch

from gateway.app.core import Gateway,GatewayError
from gateway.app import core
from tool_sandbox import protected_db


def run_policy_checks(lab,record):
    first=lab.gateway
    second=Gateway(first.database,{k:v for k,v in lab.tokens.items() if k!='tool'},first.tool_url,first.tool_token)
    a=first.authenticate(lab.tokens['agent-alice']);b=first.authenticate(lab.tokens['agent-bob']);r=first.authenticate(lab.tokens['reviewer-demo'])
    def args(**changes):return {'dataset_id':'operations','columns':['ticket_id','status'],'filters':{},'row_limit':2,'purpose':'자동 정책과 누적 예산 검증입니다.'}|changes
    def create(g,p,body=None):return g.db_access.create(p,body or args(),str(uuid.uuid4()),'127.0.0.1')
    def execute(pair):
        g,p,request=pair
        try:return 200,g.db_access.execute(p,request['id'])
        except GatewayError as error:return error.status,{'error':error.code}
    try:
        request=create(first,a)
        code,result=execute((first,a,request))
        record('명시적 자동 정책으로 실제 PostgreSQL 조회',request['decision']=='ALLOW' and code==200 and result['result_count']==2 and result['reviewer'] is None,{'state':result['state'],'authorization':request['authorization'],'rows':result['result_count']})
        # Preserve retained usage while leaving room for exactly one new two-row read.
        existing_rows=first.db_access.policy.budget(b)['used_rows']
        for g in (first,second):g.db_access.policy.config['budget']['max_rows']=existing_rows+3
        one=create(first,b);two=create(second,b)
        with ThreadPoolExecutor(2) as pool:outcomes=list(pool.map(execute,[(first,b,one),(second,b,two)]))
        record('독립 PostgreSQL 연결의 누적 예산 경쟁',sorted(c for c,_ in outcomes)==[200,429],{'statuses':[c for c,_ in outcomes],'used':first.db_access.policy.budget(b)})
        for g in (first,second):g.db_access.policy.config['budget']['max_rows']=5000
        body=args(columns=['description'],row_limit=1)
        source=create(first,a,body)
        approved=first.db_access.decide(r,source['id'],'approve','한 번만 가능한 반복 업무 승인 검증입니다.',{'ttl_seconds':600,'max_calls':1,'max_total_rows':1})
        follow=create(second,a,body)
        with ThreadPoolExecutor(2) as pool:outcomes=list(pool.map(execute,[(first,a,source),(second,a,follow)]))
        grant=approved['scope_grant']
        record('범위 승인 마지막 횟수의 PostgreSQL 경쟁',sorted(c for c,_ in outcomes)==[200,429] and first.db_access.policy.grant_usage(grant['id'])=={'calls':1,'rows':1},{'statuses':[c for c,_ in outcomes],'usage':first.db_access.policy.grant_usage(grant['id'])})
        winner=source if outcomes[0][0]==200 else follow
        first.db_access.revoke_grant(r,grant['id'],'검증 후 반복 업무 승인을 취소합니다.')
        code,result=execute((second,a,winner))
        record('다른 게이트웨이 연결에서도 취소가 즉시 적용',code==403 and result['error']=='SCOPE_GRANT_INVALID',{'status':code,'error':result['error']})
        lost=create(first,a)
        original=first._tool_request
        def response_lost(method,path,body=None):
            data=original(method,path,body)
            if method=='POST':raise GatewayError(503,'TOOL_UNAVAILABLE','simulated response loss')
            return data
        first._tool_request=response_lost
        try:code,_=execute((first,a,lost))
        finally:first._tool_request=original
        reserved=first.db.execute('SELECT * FROM db_query_usage WHERE request_id=?',(lost['id'],)).fetchone()
        first.db.execute('UPDATE db_access_requests SET expires_at=? WHERE id=?',(time.time()-1,lost['id']))
        reconciled=second.db_access.reconcile(r,lost['id'])
        record('응답 유실 예약과 만료 후 영수증 대조',code==503 and reserved['state']=='RESERVED' and reconciled['state']=='SUCCEEDED' and 'result' not in reconciled,{'initial_status':code,'reserved_rows':reserved['reserved_rows'],'reconciled_rows':reconciled['result_count']})
        start=time.perf_counter()
        pairs=[(first if i%2==0 else second,a,create(first if i%2==0 else second,a,args(row_limit=1))) for i in range(40)]
        with ThreadPoolExecutor(8) as pool:outcomes=list(pool.map(execute,pairs))
        elapsed=time.perf_counter()-start
        record('자동 허용 40건을 사람 검토 없이 실행',all(c==200 for c,_ in outcomes) and all(p[2]['authorization']['mode']=='automatic' for p in pairs),{'requests':40,'success':sum(c==200 for c,_ in outcomes),'elapsed_seconds':round(elapsed,3),'concurrency':8,'note':'기능 검증 부하이며 운영 처리량 보증이 아닙니다.'})
        old=create(first,a)
        scoped=create(first,a,args(columns=['description']))
        approved=first.db_access.decide(r,scoped['id'],'approve','규칙 변경 시 반복 승인 무효화를 검증합니다.',{'ttl_seconds':600,'max_calls':1,'max_total_rows':2})
        before=first.db_access.policy.budget(a)['used_calls']
        with patch.object(core,'INSPECTION_PATTERNS',core.INSPECTION_PATTERNS+(args()['purpose'],)):
            blocked=[execute((second,a,item)) for item in (old,scoped,request)]
            fresh=create(first,a)
            grant_state=first.db_access.policy.describe_grant(first.db_access.policy.for_request(first.db_access._row(a,scoped['id'])))['effective_status']
            after=first.db_access.policy.budget(a)['used_calls']
            record('탐지 규칙 변경 시 다른 연결의 허용·반복 승인·결과 재조회 차단',
                all(code==403 and result.get('error')=='DB_POLICY_CHANGED' for code,result in blocked)
                and fresh['state']=='DENIED' and grant_state=='POLICY_CHANGED' and before==after,
                {'statuses':[code for code,_ in blocked],'errors':[result.get('error') for _,result in blocked],
                 'new_request_state':fresh['state'],'grant_status':grant_state,'additional_charges':after-before})
        parallel_args=args(purpose='Independent business query concurrency probe')
        slow_request=create(first,a,parallel_args)
        independent=create(second,b,parallel_args)
        entered=threading.Event();release=threading.Event()
        original_query=protected_db.execute_query
        def slow_query(c,arguments,tenant,role,target):
            if tenant=='north' and arguments['purpose']==parallel_args['purpose']:
                entered.set();release.wait(5)
            return original_query(c,arguments,tenant,role,target)
        independent_status=0;ready=False;early=False
        with patch.object(protected_db,'execute_query',side_effect=slow_query),ThreadPoolExecutor(3) as pool:
            slow=pool.submit(execute,(first,a,slow_request))
            try:
                if entered.wait(2):
                    separate=pool.submit(execute,(second,b,independent))
                    health=pool.submit(first.ready)
                    independent_status=separate.result(1)[0]
                    ready=health.result(1)['status']=='ready'
                    early=not release.is_set()
            except TimeoutError:
                pass
            finally:release.set()
            slow_status=slow.result(5)[0]
        record('느린 PostgreSQL 조회 중 다른 주체와 상태 점검 독립 처리',
            independent_status==200 and slow_status==200 and ready and early,
            {'slow_status':slow_status,'other_principal_status':independent_status,'ready_before_release':ready and early,
             'scope':'통제된 지연 주입에 대한 기능 검사, 운영 처리량 측정 아님'})
        chain=first.verify_audit_chain(r)
        record('다중 연결 처리 후 감사 해시 체인',chain['status']=='VALID',{'status':chain['status'],'records':chain['chained_records']})
    finally:second.db.close()
