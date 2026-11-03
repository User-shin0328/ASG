"""Explicit DB authorization policy, scoped grants, and atomic execution budgets."""
from __future__ import annotations
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import uuid

from gateway.app.core import GatewayError, digest
from security_agent.catalog import CATALOG

SCHEMA = '''
CREATE TABLE IF NOT EXISTS db_scope_grants(
 id TEXT PRIMARY KEY,source_request_id TEXT UNIQUE NOT NULL,principal TEXT NOT NULL,tenant TEXT NOT NULL,
 scope_key TEXT NOT NULL,arguments TEXT NOT NULL,policy_hash TEXT NOT NULL,issued_by TEXT NOT NULL,
 reason TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL,
 max_calls INTEGER NOT NULL,max_total_rows INTEGER NOT NULL,status TEXT NOT NULL,
 revoked_by TEXT,revoked_reason TEXT,revoked_at DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS db_grants_scope ON db_scope_grants(principal,scope_key,status);
CREATE TABLE IF NOT EXISTS db_query_usage(
 request_id TEXT PRIMARY KEY,principal TEXT NOT NULL,tenant TEXT NOT NULL,grant_id TEXT,
 reserved_at DOUBLE PRECISION NOT NULL,reserved_rows INTEGER NOT NULL,
 actual_rows INTEGER,state TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS db_usage_principal_time ON db_query_usage(principal,reserved_at);
CREATE INDEX IF NOT EXISTS db_usage_grant ON db_query_usage(grant_id);
'''


def load_config():
    path=Path(os.environ.get('DB_POLICY_FILE',Path(__file__).resolve().parents[2]/'config/db_access.json'))
    config=json.loads(path.read_text(encoding='utf-8'))
    if set(config)!={'version','automatic_rules','budget','request_rate','grant_limits'} or not isinstance(config['version'],str):
        raise RuntimeError('Invalid DB policy')
    for key,fields in [('budget',{'window_seconds','max_calls','max_rows'}),('request_rate',{'warning','block'}),('grant_limits',{'max_ttl_seconds','max_calls','max_total_rows'})]:
        if not isinstance(config[key],dict) or set(config[key])!=fields or any(type(v) is not int or v<=0 for v in config[key].values()):
            raise RuntimeError('Invalid DB policy limits')
    if config['request_rate']['warning']>=config['request_rate']['block']:raise RuntimeError('Invalid DB request-rate policy')
    if not isinstance(config['automatic_rules'],list):raise RuntimeError('Invalid automatic rules')
    ids=set()
    for rule in config['automatic_rules']:
        if not isinstance(rule,dict) or set(rule)!={'id','dataset_id','columns','roles','tasks','max_rows'}:
            raise RuntimeError('Invalid automatic rule')
        spec=CATALOG.get(rule['dataset_id'])
        if not spec or not isinstance(rule['id'],str) or rule['id'] in ids or type(rule['max_rows']) is not int or not 1<=rule['max_rows']<1000:
            raise RuntimeError('Invalid automatic rule scope')
        for field in ('columns','roles','tasks'):
            if not isinstance(rule[field],list) or not rule[field] or any(not isinstance(v,str) for v in rule[field]):raise RuntimeError('Invalid automatic rule values')
        if any(spec['columns'].get(c)!='internal' for c in rule['columns']) or any(r not in spec['roles'] for r in rule['roles']):raise RuntimeError('Automatic rules cannot grant sensitive columns')
        ids.add(rule['id'])
    return config


class DBPolicy:
    def __init__(self,service):
        self.service=service
        self.db=service.db
        self.config=load_config()
        if not self.db.is_postgres:self.db.executescript(SCHEMA)

    def scope_key(self,p,args):
        scope={k:v for k,v in args.items() if k!='row_limit'}
        scope['columns']=sorted(scope['columns'])
        return digest({'principal':p.id,'user':p.user,'tenant':p.tenant,'task':p.task,'role':p.role,'target':self.service.target,'scope':scope})

    def grant_usage(self,grant_id):
        row=self.db.execute("SELECT COUNT(*) AS calls,COALESCE(SUM(CASE WHEN state='COMPLETED' THEN actual_rows ELSE reserved_rows END),0) AS rows FROM db_query_usage WHERE grant_id=?",(grant_id,)).fetchone()
        return dict(row)

    def choose(self,p,args,analysis):
        if analysis['decision']=='DENY':return {'mode':'denied','role':p.role}
        if not analysis['abnormal']:
            rows=self.db.execute("SELECT * FROM db_scope_grants WHERE principal=? AND scope_key=? AND status='ACTIVE' AND expires_at>? AND policy_hash=? ORDER BY created_at DESC",(p.id,self.scope_key(p,args),time.time(),self.service.policy_hash())).fetchall()
            for grant in rows:
                used=self.grant_usage(grant['id'])
                if args['row_limit']<=json.loads(grant['arguments'])['row_limit'] and used['calls']<grant['max_calls'] and used['rows']+args['row_limit']<=grant['max_total_rows']:
                    return {'mode':'scope_grant','grant_id':grant['id'],'role':p.role}
            if not analysis['sensitive'] and not analysis['bulk']:
                for rule in self.config['automatic_rules']:
                    if args['dataset_id']==rule['dataset_id'] and set(args['columns'])<=set(rule['columns']) and p.role in rule['roles'] and p.task in rule['tasks'] and args['row_limit']<=rule['max_rows']:
                        return {'mode':'automatic','rule_id':rule['id'],'role':p.role}
        return {'mode':'human','role':p.role}

    def issue(self,p,row,limits,reason):
        spec=self.config['grant_limits']
        if not isinstance(limits,dict) or set(limits)!={'ttl_seconds','max_calls','max_total_rows'} or any(type(v) is not int or v<=0 for v in limits.values()):
            raise GatewayError(422,'INVALID_SCOPE_GRANT','기간·횟수·누적 행 수가 필요합니다.')
        args=json.loads(row['arguments'])
        if not 60<=limits['ttl_seconds']<=spec['max_ttl_seconds'] or limits['max_calls']>spec['max_calls'] or not args['row_limit']<=limits['max_total_rows']<=spec['max_total_rows']:
            raise GatewayError(422,'INVALID_SCOPE_GRANT','범위 승인 한도를 벗어났습니다.')
        auth=json.loads(row['analysis'])['authorization']
        actor=SimpleNamespace(id=row['principal'],user=row['user_name'],tenant=row['tenant'],task=row['task_id'],role=auth['role'])
        now=time.time()
        grant={'id':str(uuid.uuid4()),'source_request_id':row['id'],'principal':row['principal'],'tenant':row['tenant'],
            'scope_key':self.scope_key(actor,args),'arguments':json.dumps(args,ensure_ascii=False),'policy_hash':self.service.policy_hash(),
            'issued_by':p.id,'reason':reason,'created_at':now,'expires_at':now+limits['ttl_seconds'],
            'max_calls':limits['max_calls'],'max_total_rows':limits['max_total_rows'],'status':'ACTIVE',
            'revoked_by':None,'revoked_reason':None,'revoked_at':None}
        self.db.execute('INSERT INTO db_scope_grants ('+','.join(grant)+') VALUES('+','.join('?' for _ in grant)+')',tuple(grant.values()))
        return grant

    def for_request(self,row):
        auth=json.loads(row['analysis']).get('authorization',{})
        grant_id=dict(row).get('grant_id') or auth.get('grant_id')
        if grant_id:
            return self.db.execute('SELECT * FROM db_scope_grants WHERE id=?',(grant_id,)).fetchone()
        return self.db.execute('SELECT * FROM db_scope_grants WHERE source_request_id=?',(row['id'],)).fetchone()

    def validate_grant(self,p,row,args,grant):
        if grant['status']!='ACTIVE' or grant['expires_at']<=time.time() or grant['policy_hash']!=self.service.policy_hash() or grant['scope_key']!=self.scope_key(p,args) or args['row_limit']>json.loads(grant['arguments'])['row_limit']:
            raise GatewayError(403,'SCOPE_GRANT_INVALID','반복 업무 승인이 만료·취소됐거나 요청 범위가 다릅니다.')

    def budget(self,p):
        limit=self.config['budget']
        row=self.db.execute("SELECT COUNT(*) AS calls,COALESCE(SUM(CASE WHEN state='COMPLETED' THEN actual_rows ELSE reserved_rows END),0) AS rows FROM db_query_usage WHERE principal=? AND (reserved_at>=? OR state='RESERVED')",(p.id,time.time()-limit['window_seconds'])).fetchone()
        return {'used_calls':row['calls'],'used_rows':row['rows'],**limit}

    def reserve(self,p,row,args,grant):
        old=self.db.execute('SELECT * FROM db_query_usage WHERE request_id=?',(row['id'],)).fetchone()
        if old:return
        used=self.budget(p)
        if used['used_calls']>=used['max_calls'] or used['used_rows']+args['row_limit']>used['max_rows']:
            raise GatewayError(429,'DB_BUDGET_EXCEEDED','최근 30분의 조회 횟수·누적 행 수 한도를 초과합니다.')
        if grant:
            usage=self.grant_usage(grant['id'])
            if usage['calls']>=grant['max_calls'] or usage['rows']+args['row_limit']>grant['max_total_rows']:
                raise GatewayError(429,'SCOPE_GRANT_EXHAUSTED','반복 업무 승인의 횟수·누적 행 수를 모두 사용했습니다.')
        self.db.execute("INSERT INTO db_query_usage VALUES(?,?,?,?,?,?,?,?)",(row['id'],p.id,p.tenant,grant['id'] if grant else None,time.time(),args['row_limit'],None,'RESERVED'))

    def settle(self,row,result):
        count=result['result'].get('row_count')
        usage=self.db.execute('SELECT * FROM db_query_usage WHERE request_id=?',(row['id'],)).fetchone()
        if type(count) is not int or count<0 or not usage or count>usage['reserved_rows']:
            raise GatewayError(503,'DB_RECEIPT_INVALID','반환량을 확인할 수 없어 예약을 유지합니다.')
        self.db.execute("UPDATE db_query_usage SET actual_rows=?,state='COMPLETED',reserved_at=? WHERE request_id=? AND state='RESERVED'",(count,time.time(),row['id']))

    def describe_grant(self,row):
        item=dict(row)
        item['arguments']=json.loads(item['arguments'])
        usage=self.grant_usage(item['id'])
        item['usage']=usage
        item['effective_status']='REVOKED' if item['status']=='REVOKED' else 'EXPIRED' if item['expires_at']<=time.time() else 'POLICY_CHANGED' if item['policy_hash']!=self.service.policy_hash() else 'EXHAUSTED' if usage['calls']>=item['max_calls'] or usage['rows']>=item['max_total_rows'] else 'ACTIVE'
        return item
