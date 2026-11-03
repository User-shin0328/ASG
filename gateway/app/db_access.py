"""Approval-gated structured DB reads, durable reports and 30-minute risk analytics."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import math
import time
import uuid
from gateway.app.core import GatewayError, digest, scan_untrusted_text
from security_agent.assessment import SecurityAgent, AGENT_VERSION
from security_agent.catalog import CATALOG, validate_query
from security_agent.db_target import target_config
from gateway.app.db_policy import DBPolicy

KST=timezone(timedelta(hours=9))
WINDOW=1800
RISK_WEIGHTS={'sensitive':12,'bulk':10,'abnormal':20}

SCHEMA='''
CREATE TABLE IF NOT EXISTS db_access_requests(
 id TEXT PRIMARY KEY, principal TEXT NOT NULL, user_name TEXT NOT NULL, tenant TEXT NOT NULL,
 task_id TEXT NOT NULL, requested_at DOUBLE PRECISION NOT NULL, source_ip TEXT NOT NULL, client TEXT NOT NULL,
 arguments TEXT NOT NULL, analysis TEXT NOT NULL, sensitive INTEGER NOT NULL, bulk INTEGER NOT NULL,
 abnormal INTEGER NOT NULL, risk_score INTEGER NOT NULL, decision TEXT NOT NULL, state TEXT NOT NULL,
 policy_hash TEXT NOT NULL, request_hash TEXT NOT NULL, snapshot_hash TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL,
 reviewer TEXT, review_reason TEXT, decided_at DOUBLE PRECISION, execution_id TEXT NOT NULL,
 receipt_id TEXT, result_count INTEGER, idem_key TEXT NOT NULL, trace_id TEXT NOT NULL,
 UNIQUE(principal,idem_key));
CREATE INDEX IF NOT EXISTS db_requests_tenant_time ON db_access_requests(tenant,requested_at);
CREATE INDEX IF NOT EXISTS db_requests_state_risk ON db_access_requests(tenant,state,risk_score);
CREATE TABLE IF NOT EXISTS db_access_events(
 id TEXT PRIMARY KEY,request_id TEXT NOT NULL,tenant TEXT NOT NULL,at DOUBLE PRECISION NOT NULL,
 actor TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS db_events_request_time ON db_access_events(request_id,at);
'''


def day_bounds(value=None):
    try:
        day=datetime.strptime(value,'%Y-%m-%d').replace(tzinfo=KST) if value else datetime.now(KST).replace(hour=0,minute=0,second=0,microsecond=0)
    except (ValueError,TypeError):
        raise GatewayError(422,'INVALID_DATE','날짜는 YYYY-MM-DD 형식이어야 합니다.')
    return day.timestamp(),(day+timedelta(days=1)).timestamp()


def effective_state(row,now):
    return 'EXPIRED' if row['state'] in {'PENDING_APPROVAL','APPROVED'} and row['expires_at']<=now else row['state']


class DBAccessService:
    def __init__(self,gateway):
        self.gateway=gateway
        self.db=gateway.db
        self.lock=gateway.lock
        self.agent=SecurityAgent(scan_untrusted_text)
        self.target=target_config()
        self.policy=DBPolicy(self)
        if not self.db.is_postgres:
            self.db.executescript(SCHEMA+'''
            CREATE TRIGGER IF NOT EXISTS db_events_no_update BEFORE UPDATE ON db_access_events BEGIN SELECT RAISE(ABORT,'db events are append only'); END;
            CREATE TRIGGER IF NOT EXISTS db_events_no_delete BEFORE DELETE ON db_access_events BEGIN SELECT RAISE(ABORT,'db events are append only'); END;
            ''')
            columns={row['name'] for row in self.db.execute('PRAGMA table_info(db_access_requests)').fetchall()}
            for name in ('authorization_mode','grant_id','automatic_rule_id'):
                if name not in columns:self.db.execute('ALTER TABLE db_access_requests ADD COLUMN '+name+' TEXT')

    def request_state(self,row,grant=None):
        state=effective_state(row,time.time())
        if state=='APPROVED':
            if row['policy_hash']!=self.policy_hash():return 'DENIED'
            if grant:
                if grant['status']=='REVOKED' or grant['policy_hash']!=self.policy_hash():return 'DENIED'
                if grant['expires_at']<=time.time():return 'EXPIRED'
        return state

    def policy_hash(self):
        return digest({'policy':self.gateway.policy,'catalog':CATALOG,'engine':AGENT_VERSION,'db_policy':self.policy.config,'target':self.target})

    def reviewer(self,p):
        if p.kind!='reviewer':raise GatewayError(403,'REVIEWER_REQUIRED','검토자 권한이 필요합니다.')

    def _row(self,p,request_id):
        row=self.db.execute('SELECT * FROM db_access_requests WHERE id=? AND tenant=?',(request_id,p.tenant)).fetchone()
        if not row or (p.kind=='agent' and row['principal']!=p.id):
            raise GatewayError(404,'DB_REQUEST_NOT_FOUND','해당 요청을 찾을 수 없습니다.')
        if p.kind not in {'agent','reviewer'}:raise GatewayError(403,'FORBIDDEN','조회 권한이 없습니다.')
        return row

    def serialize(self,row,full=False):
        obj=dict(row)
        args=json.loads(obj['arguments'])
        analysis=json.loads(obj['analysis'])
        grant=self.policy.for_request(row)
        state=self.request_state(row,grant)
        result={k:obj[k] for k in ('id','principal','user_name','tenant','task_id','requested_at','source_ip','client','risk_score','decision','expires_at','reviewer','review_reason','decided_at','result_count','trace_id')}
        dataset=CATALOG.get(args.get('dataset_id'),{}) if isinstance(args.get('dataset_id'),str) else {}
        result.update({'request_id':obj['id'],'state':state,'arguments':args,'analysis':analysis,
            'dataset_name':dataset.get('name','등록되지 않은 데이터'),
            'database_name':'보호 PostgreSQL DB' if analysis.get('db_target',{}).get('backend')=='postgresql' else '사내 검증 DB',
            'mode':analysis.get('db_target',{}).get('backend','sqlite'),
            'execution_id':obj['execution_id'],'receipt_id':obj['receipt_id']})
        result['authorization']=analysis.get('authorization',{'mode':'legacy'})
        if grant:result['scope_grant']=self.policy.describe_grant(grant)
        if full:
            result['approval_binding']={'request_hash':obj['request_hash'],'snapshot_hash':obj['snapshot_hash'],'policy_hash':obj['policy_hash']}
            events=self.db.execute('SELECT at,actor,event,details FROM db_access_events WHERE request_id=? AND tenant=? ORDER BY at',(obj['id'],obj['tenant'])).fetchall()
            result['timeline']=[dict(e)|{'details':json.loads(e['details'])} for e in events]
        return result

    def _event(self,row,actor,event,details):
        self.db.execute('INSERT INTO db_access_events VALUES(?,?,?,?,?,?,?)',
            (str(uuid.uuid4()),row['id'],row['tenant'],time.time(),actor,event,json.dumps(details,ensure_ascii=False)))
        self.gateway._audit(row['trace_id'],None,actor,event,{'request_id':row['id'],**details})

    def create(self,p,body,idem,source_ip,client=''):
        if p.kind!='agent' or not p.task:raise GatewayError(403,'AGENT_REQUIRED','사내 에이전트의 인증된 요청이 필요합니다.')
        if not idem or len(idem)>128:raise GatewayError(422,'INVALID_IDEMPOTENCY_KEY','Idempotency-Key가 필요합니다.')
        if not isinstance(body,dict):raise GatewayError(422,'INVALID_REQUEST','요청은 JSON 객체여야 합니다.')
        request_hash=digest(body)
        with self.lock,self.db.advisory_lock('db-request:'+p.id):
            prior=self.db.execute('SELECT * FROM db_access_requests WHERE principal=? AND idem_key=?',(p.id,idem)).fetchone()
            if prior:
                if prior['request_hash']!=request_hash:raise GatewayError(409,'IDEMPOTENCY_CONFLICT','같은 키의 요청 내용이 다릅니다.')
                return self.serialize(prior,True)
            now=time.time()
            recent=self.db.execute('SELECT COUNT(*) AS count FROM db_access_requests WHERE principal=? AND requested_at>=?',(p.id,now-60)).fetchone()['count']
            # Unknown field contents are not retained. They still make validation fail closed.
            args={k:body.get(k) for k in ('dataset_id','columns','filters','row_limit','purpose')}
            analysis_input=dict(body)
            try:
                analysis=self.agent.assess(analysis_input,{'tenant':p.tenant,'role':p.role},recent,**self.policy.config['request_rate'])
            except Exception:
                analysis={'engine':AGENT_VERSION,'method':'policy_and_behavior_rules','risk_score':100,'risk_level':'critical',
                    'sensitive':False,'bulk':False,'abnormal':True,'reason_codes':['SECURITY_AGENT_UNAVAILABLE'],
                    'reasons':['보안 분석에 실패하여 요청을 차단했습니다.'],'recommendation':'분석 서비스를 복구한 뒤 새로 요청하세요.','decision':'DENY'}
            decision=analysis['decision']
            analysis['db_target']=dict(self.target)
            authorization=self.policy.choose(p,args,analysis)
            analysis['authorization']=authorization
            if authorization['mode'] in {'automatic','scope_grant'}:
                decision=analysis['decision']='ALLOW'
                analysis['reasons'].append('명시적 자동 허용 정책에 부합합니다.' if authorization['mode']=='automatic' else '검토자가 발급한 반복 업무 승인 범위에 부합합니다.')
            pending=self.db.execute("SELECT COUNT(*) AS count FROM db_access_requests WHERE principal=? AND (authorization_mode='human' OR authorization_mode IS NULL) AND state IN ('PENDING_APPROVAL','APPROVED') AND expires_at>?",(p.id,now)).fetchone()['count']
            if decision=='REQUIRE_APPROVAL' and pending>=self.gateway.policy['limits']['pending_approvals_per_principal']:
                analysis.update({'decision':'DENY','abnormal':True,'risk_score':max(80,analysis['risk_score']),'risk_level':'critical',
                    'reason_codes':analysis['reason_codes']+['PENDING_DB_REQUEST_LIMIT'],
                    'reasons':analysis['reasons']+['미처리 승인 요청 한도를 초과했습니다.'],'recommendation':'기존 요청을 검토·정리한 뒤 새로 요청하세요.'})
                decision='DENY'
            state='DENIED' if decision=='DENY' else 'APPROVED' if decision=='ALLOW' else 'PENDING_APPROVAL'
            policy=self.policy_hash()
            binding=digest({'principal':p.id,'tenant':p.tenant,'task':p.task,'arguments':args,'analysis':analysis,'policy':policy})
            values={'id':str(uuid.uuid4()),'principal':p.id,'user_name':p.user,'tenant':p.tenant,'task_id':p.task,
                'requested_at':now,'source_ip':str(source_ip)[:80],'client':str(client)[:160],
                'arguments':json.dumps(args,ensure_ascii=False),'analysis':json.dumps(analysis,ensure_ascii=False),
                'sensitive':int(analysis['sensitive']),'bulk':int(analysis['bulk']),'abnormal':int(analysis['abnormal']),
                'risk_score':analysis['risk_score'],'decision':decision,'state':state,'policy_hash':policy,
                'request_hash':request_hash,'snapshot_hash':binding,'expires_at':now+self.gateway.policy['limits']['approval_seconds'],
                'reviewer':None,'review_reason':None,'decided_at':None,'execution_id':str(uuid.uuid4()),
                'receipt_id':None,'result_count':None,'idem_key':idem,'trace_id':str(uuid.uuid4()),
                'authorization_mode':authorization['mode'],'grant_id':authorization.get('grant_id'),'automatic_rule_id':authorization.get('rule_id')}
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('INSERT INTO db_access_requests ('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
                self._event(values,p.id,'DB_REQUESTED',{'dataset_id':args['dataset_id'],'decision':decision,'risk_score':analysis['risk_score'],'source_ip':values['source_ip'],'request_hash':request_hash,'snapshot_hash':binding})
                if decision=='ALLOW':self._event(values,'policy-engine','DB_AUTO_AUTHORIZED',authorization)
                self.db.execute('COMMIT')
            except Exception:
                self.db.execute('ROLLBACK')
                raise
            return self.serialize(self._row(p,values['id']),True)

    def detail(self,p,request_id):
        with self.lock:return self.serialize(self._row(p,request_id),True)

    def decide(self,p,request_id,decision,reason,scope_grant=None):
        self.reviewer(p)
        if decision not in {'approve','reject'} or not isinstance(reason,str) or not 3<=len(reason.strip())<=1000:
            raise GatewayError(422,'REVIEW_REASON_REQUIRED','승인·거절과 3~1,000자의 판단 근거를 입력하세요.')
        with self.lock,self.db.advisory_lock('db-decision:'+request_id):
            row=self._row(p,request_id)
            if effective_state(row,time.time())!='PENDING_APPROVAL':raise GatewayError(409,'NOT_PENDING','결정되었거나 만료된 요청입니다.')
            if row['policy_hash']!=self.policy_hash():raise GatewayError(409,'POLICY_CHANGED','정책이 바뀌었습니다. 새 요청을 검토하세요.')
            binding=digest({'principal':row['principal'],'tenant':row['tenant'],'task':row['task_id'],'arguments':json.loads(row['arguments']),'analysis':json.loads(row['analysis']),'policy':self.policy_hash()})
            if binding!=row['snapshot_hash']:raise GatewayError(409,'DB_SNAPSHOT_CHANGED','검토할 요청 정보가 접수 이후 바뀌었습니다.')
            state='APPROVED' if decision=='approve' else 'REJECTED'
            if scope_grant is not None and decision!='approve':raise GatewayError(422,'INVALID_SCOPE_GRANT','범위 승인은 승인할 때만 발급할 수 있습니다.')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                changed=self.db.execute("UPDATE db_access_requests SET state=?,reviewer=?,review_reason=?,decided_at=? WHERE id=? AND state='PENDING_APPROVAL'",(state,p.id,reason.strip(),time.time(),request_id)).rowcount
                if changed!=1:raise GatewayError(409,'NOT_PENDING','이미 다른 검토자가 결정했습니다.')
                if scope_grant is not None:
                    grant=self.policy.issue(p,row,scope_grant,reason.strip())
                    self.db.execute('UPDATE db_access_requests SET grant_id=? WHERE id=?',(grant['id'],request_id))
                    self._event(row,p.id,'DB_SCOPE_GRANTED',{'grant_id':grant['id'],**scope_grant})
                self._event(row,p.id,'DB_'+state,{'reason':reason.strip(),'snapshot_hash':row['snapshot_hash']})
                self.db.execute('COMMIT')
            except Exception:
                self.db.execute('ROLLBACK')
                raise
            return self.serialize(self._row(p,request_id),True)

    def execute(self,p,request_id):
        if p.kind!='agent':raise GatewayError(403,'AGENT_REQUIRED','실행은 원래 요청한 에이전트만 할 수 있습니다.')
        with self.lock,self.db.advisory_lock('db-budget:'+p.id),self.db.advisory_lock('db-execute:'+request_id):
            row=self._row(p,request_id)
            args=json.loads(row['arguments'])
            if row['expires_at']<=time.time() or effective_state(row,time.time()) not in {'APPROVED','UNKNOWN','EXECUTING','SUCCEEDED'}:
                raise GatewayError(409,'DB_APPROVAL_REQUIRED','유효한 정책 허용 또는 승인 없이는 DB를 조회할 수 없습니다.')
            if row['policy_hash']!=self.policy_hash() or validate_query(args,{'tenant':p.tenant,'role':p.role}):
                raise GatewayError(403,'DB_POLICY_CHANGED','현재 정책이 요청을 허용하지 않습니다.')
            binding=digest({'principal':p.id,'tenant':p.tenant,'task':p.task,'arguments':args,'analysis':json.loads(row['analysis']),'policy':self.policy_hash()})
            auth=json.loads(row['analysis']).get('authorization',{})
            if binding!=row['snapshot_hash'] or auth.get('role')!=p.role or (auth.get('mode')=='human' and not row['reviewer']) or auth.get('mode') not in {'automatic','human','scope_grant'}:
                raise GatewayError(403,'DB_SNAPSHOT_CHANGED','승인 이후 요청이나 분석 정보가 바뀌었습니다.')
            grant=self.policy.for_request(row)
            if auth.get('mode')=='scope_grant' and not grant:raise GatewayError(403,'SCOPE_GRANT_INVALID','범위 승인을 찾을 수 없습니다.')
            if grant:self.policy.validate_grant(p,row,args,grant)
            if row['state']=='SUCCEEDED':
                receipt=self.gateway._tool_request('GET','/internal/executions/'+row['execution_id'])
                return self.serialize(row,True)|{'result':receipt,'replayed':True}
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.policy.reserve(p,row,args,grant)
                self.db.execute("UPDATE db_access_requests SET state='EXECUTING' WHERE id=?",(request_id,))
                self._event(row,p.id,'DB_EXECUTION_STARTED',{'execution_id':row['execution_id'],'authorization':auth})
                self.db.execute('COMMIT')
            except Exception as error:
                self.db.execute('ROLLBACK')
                if isinstance(error,GatewayError) and error.code in {'DB_BUDGET_EXCEEDED','SCOPE_GRANT_EXHAUSTED'}:
                    self.db.execute("UPDATE db_access_requests SET state='DENIED',decision='DENY',abnormal=1 WHERE id=?",(request_id,))
                    self._event(row,'policy-engine','DB_BUDGET_BLOCKED',{'reason':error.code})
                raise
            try:
                result=self.gateway._tool_request('POST','/internal/execute',{'execution_id':row['execution_id'],'action_id':request_id,
                    'principal':p.id,'user':p.user,'tenant':p.tenant,'task_id':p.task,'tool':'query_database',
                    'arguments':args|{'_asg_target_id':self.target['id']},'request_hash':row['request_hash']})
                self.policy.settle(row,result)
            except GatewayError:
                self.db.execute("UPDATE db_access_requests SET state='UNKNOWN' WHERE id=?",(request_id,))
                self._event(row,p.id,'DB_EXECUTION_UNKNOWN',{'execution_id':row['execution_id']})
                raise
            count=result['result']['row_count']
            self.db.execute("UPDATE db_access_requests SET state='SUCCEEDED',receipt_id=?,result_count=? WHERE id=?",(result['receipt_id'],count,request_id))
            self._event(row,p.id,'DB_EXECUTION_SUCCEEDED',{'row_count':count,'receipt_id':result['receipt_id']})
            return self.serialize(self._row(p,request_id),True)|{'result':result,'replayed':False}

    def grants(self,p):
        self.reviewer(p)
        with self.lock:
            rows=self.db.execute('SELECT * FROM db_scope_grants WHERE tenant=? ORDER BY created_at DESC LIMIT 100',(p.tenant,)).fetchall()
            return {'items':[self.policy.describe_grant(r) for r in rows]}

    def reconcile(self,p,request_id):
        self.reviewer(p)
        with self.lock:
            row=self._row(p,request_id)
            with self.db.advisory_lock('db-budget:'+row['principal']),self.db.advisory_lock('db-execute:'+request_id):
                row=self._row(p,request_id)
                if row['state'] not in {'UNKNOWN','EXECUTING'}:raise GatewayError(409,'NOT_UNCERTAIN','결과 확인이 필요한 실행만 대조할 수 있습니다.')
                receipt=self.gateway._tool_request('GET','/internal/executions/'+row['execution_id'])
                if receipt.get('execution_id')!=row['execution_id'] or receipt.get('action_id')!=row['id']:
                    raise GatewayError(503,'DB_RECEIPT_INVALID','일치하는 실행 영수증이 없습니다.')
                self.db.execute('BEGIN IMMEDIATE')
                try:
                    self.policy.settle(row,receipt)
                    self.db.execute("UPDATE db_access_requests SET state='SUCCEEDED',receipt_id=?,result_count=? WHERE id=?",(receipt['receipt_id'],receipt['result']['row_count'],request_id))
                    self._event(row,p.id,'DB_EXECUTION_RECONCILED',{'receipt_id':receipt['receipt_id'],'row_count':receipt['result']['row_count']})
                    self.db.execute('COMMIT')
                except Exception:
                    self.db.execute('ROLLBACK');raise
                return self.serialize(self._row(p,request_id),True)

    def budgets(self,p):
        self.reviewer(p)
        with self.lock:
            rows=self.db.execute('SELECT DISTINCT principal FROM db_query_usage WHERE tenant=?',(p.tenant,)).fetchall()
            from types import SimpleNamespace
            return {'items':[{'principal':r['principal'],**self.policy.budget(SimpleNamespace(id=r['principal']))} for r in rows],'window_seconds':self.policy.config['budget']['window_seconds']}

    def revoke_grant(self,p,grant_id,reason):
        self.reviewer(p)
        if not isinstance(reason,str) or not 3<=len(reason.strip())<=1000:raise GatewayError(422,'REVIEW_REASON_REQUIRED','취소 이유를 입력하세요.')
        with self.lock:
            grant=self.db.execute('SELECT * FROM db_scope_grants WHERE id=? AND tenant=?',(grant_id,p.tenant)).fetchone()
            if not grant:raise GatewayError(404,'NOT_FOUND','범위 승인을 찾을 수 없습니다.')
            with self.db.advisory_lock('db-budget:'+grant['principal']):
                self.db.execute('BEGIN IMMEDIATE')
                try:
                    self.db.execute("UPDATE db_scope_grants SET status='REVOKED',revoked_by=?,revoked_reason=?,revoked_at=? WHERE id=?",(p.id,reason.strip(),time.time(),grant_id))
                    self._event(self._row(p,grant['source_request_id']),p.id,'DB_SCOPE_REVOKED',{'grant_id':grant_id,'reason':reason.strip()})
                    self.db.execute('COMMIT')
                except Exception:
                    self.db.execute('ROLLBACK');raise
            return self.policy.describe_grant(self.db.execute('SELECT * FROM db_scope_grants WHERE id=?',(grant_id,)).fetchone())

    def listing(self,p,date=None,pending=False,sort='newest',page=1):
        self.reviewer(p)
        if sort not in {'newest','oldest','risk'}:raise GatewayError(422,'INVALID_SORT','정렬 조건이 올바르지 않습니다.')
        if type(page) is not int or not 1<=page<=100000:raise GatewayError(422,'INVALID_PAGE','페이지가 올바르지 않습니다.')
        clauses=['tenant=?'];params=[p.tenant]
        if pending:
            clauses+= ["state='PENDING_APPROVAL'",'expires_at>?'];params.append(time.time())
        else:
            start,end=day_bounds(date);clauses+=['requested_at>=?','requested_at<?'];params.extend((start,end))
        where=' AND '.join(clauses)
        order={'newest':'requested_at DESC,id','oldest':'requested_at ASC,id','risk':'risk_score DESC,requested_at ASC,id'}[sort]
        with self.lock:
            total=self.db.execute('SELECT COUNT(*) AS count FROM db_access_requests WHERE '+where,params).fetchone()['count']
            rows=self.db.execute('SELECT * FROM db_access_requests WHERE '+where+' ORDER BY '+order+' LIMIT ? OFFSET ?',params+[50,(page-1)*50]).fetchall()
        return {'items':[self.serialize(r) for r in rows],'total':total,'page':page,'page_size':50,'timezone':'Asia/Seoul'}

    def risk_at(self,rows,at):
        factors={key:0 for key in RISK_WEIGHTS};components={key:0.0 for key in RISK_WEIGHTS}
        for row in rows:
            age=at-row['requested_at']
            if not 0<=age<WINDOW:continue
            for key,weight in RISK_WEIGHTS.items():
                if row[key]:factors[key]+=1;components[key]+=weight*(1-age/WINDOW)
        raw=sum(components.values())
        return {'score':min(100,round(raw,1)),'raw_score':round(raw,2),'factors':factors,
            'components':{k:round(v,2) for k,v in components.items()},'weights':RISK_WEIGHTS,
            'window_seconds':WINDOW,'formula':'min(100, Σ[(민감×12 + 대량×10 + 비정상×20) × (1-경과초/1800)])',
            'meaning':'운영 위험 지표이며 침해 확률이나 모델의 신뢰도가 아닙니다.'}

    def overview(self,p):
        self.reviewer(p)
        now=time.time();start,end=day_bounds()
        with self.lock:
            today=self.db.execute('SELECT r.state,r.expires_at,r.policy_hash,g.status AS grant_status,g.expires_at AS grant_expires,g.policy_hash AS grant_policy FROM db_access_requests r LEFT JOIN db_scope_grants g ON r.grant_id=g.id WHERE r.tenant=? AND r.requested_at>=? AND r.requested_at<?',(p.tenant,start,end)).fetchall()
            # A full hour supports exact 30-minute windows at each historical chart point.
            risk_rows=self.db.execute('SELECT requested_at,sensitive,bulk,abnormal FROM db_access_requests WHERE tenant=? AND requested_at>=? AND requested_at<=?',(p.tenant,now-3600,now)).fetchall()
            recent=self.db.execute('SELECT * FROM db_access_requests WHERE tenant=? ORDER BY requested_at DESC LIMIT 6',(p.tenant,)).fetchall()
        states=[self.request_state(r,{'status':r['grant_status'],'expires_at':r['grant_expires'],'policy_hash':r['grant_policy']} if r['grant_status'] else None) for r in today]
        metrics={'pending':states.count('PENDING_APPROVAL'),'allowed':sum(s in {'APPROVED','EXECUTING','SUCCEEDED','UNKNOWN'} for s in states),
            'blocked':sum(s in {'DENIED','REJECTED','EXPIRED'} for s in states),'today_total':len(today)}
        activity=[];trend=[]
        for index in range(30):
            a=now-WINDOW+index*60;b=a+60
            group=[r for r in risk_rows if a<=r['requested_at']<b or (index==29 and r['requested_at']==b)]
            activity.append({'at':b,'count':len(group)})
        trend=[{'at':now-WINDOW+index*60,'score':self.risk_at(risk_rows,now-WINDOW+index*60)['score']} for index in range(31)]
        return {'as_of':now,'timezone':'Asia/Seoul','day_start':start,'metrics':metrics,'risk':self.risk_at(risk_rows,now),
            'activity':activity,'risk_trend':trend,'recent':[self.serialize(r) for r in recent],
            'catalog':[{'id':key,'name':value['name'],'columns':value['columns']} for key,value in CATALOG.items() if p.tenant in value['tenants']]}

    def status(self,p):
        self.reviewer(p)
        items=[]
        def probe(key,name,fn):
            started=time.perf_counter()
            try:
                detail=fn();state='up'
            except Exception:
                detail='실제 연결 점검 실패';state='down'
            items.append({'key':key,'name':name,'status':state,'detail':detail,'checked_at':time.time(),'latency_ms':round((time.perf_counter()-started)*1000,2)})
        probe('gateway','게이트웨이',lambda:self.gateway.ready()['status'])
        agent=self.agent.health()
        items.append({'key':'security_agent','name':'보안 에이전트',**agent})
        probe('protected_db','보호 DB',lambda:self.gateway._tool_request('GET','/internal/db-health')['detail'])
        probe('audit_db','감사 DB',lambda:'감사 기록 저장소 연결됨' if self.db.execute('SELECT COUNT(*) AS count FROM db_access_events').fetchone() else '')
        return {'checked_at':time.time(),'items':items,'all_healthy':all(item['status']=='up' for item in items),
            'deployment':'PostgreSQL 연결 모드' if self.target['backend']=='postgresql' else '로컬 검증 DB · 가상 데이터 · 실제 사내 DB 미연결', 'target':self.target}

    def diagnostics(self,p):
        with self.lock:
            status=self.status(p)
            integrity=self.gateway.verify_audit_chain(p)
        checks=[{'name':item['name'],'passed':item['status']=='up','detail':item['detail'],'latency_ms':item.get('latency_ms')} for item in status['items']]
        checks.append({'name':'감사 로그 무결성','passed':integrity['status']=='VALID','detail':f"{integrity['chained_records']}개 해시 연결 검증, 변조 의심 {len(integrity['tampered_record_ids'])}건"})
        return {'checked_at':time.time(),'passed':all(c['passed'] for c in checks),'checks':checks,
            'scope':'실제 연결과 분석 자체 점검입니다. 전체 네트워크 격리 검증은 포함하지 않습니다.'}
