"""Real PostgreSQL checks using two independent Gateway connections and a live tool service."""
from concurrent.futures import ThreadPoolExecutor
import time
import uuid

from gateway.app.core import Gateway,GatewayError


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
        chain=first.verify_audit_chain(r)
        record('다중 연결 처리 후 감사 해시 체인',chain['status']=='VALID',{'status':chain['status'],'records':chain['chained_records']})
    finally:second.db.close()
