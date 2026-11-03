from concurrent.futures import ThreadPoolExecutor
import json
import time
import unittest
import uuid

from gateway.app.core import Gateway,GatewayError


def query(**changes):
    return {'dataset_id':'operations','columns':['ticket_id','status'],'filters':{},'row_limit':100,'purpose':'정해진 운영 현황 조회입니다.'}|changes


class PolicyControlTests(unittest.TestCase):
    def setUp(self):
        self.g=Gateway(':memory:',{'agent-alice':'a'*40,'agent-bob':'b'*40,'reviewer-demo':'r'*40})
        self.s=self.g.db_access
        self.a=self.g.authenticate('a'*40);self.b=self.g.authenticate('b'*40);self.r=self.g.authenticate('r'*40)
        self.queries=[];self.receipts={};self.actual=None
        self.g._tool_request=self.tool

    def tearDown(self):self.g.db.close()

    def tool(self,method,path,body=None):
        if method=='GET':return self.receipts[path.rsplit('/',1)[1]]
        self.queries.append(body)
        count=body['arguments']['row_limit'] if self.actual is None else self.actual
        result={'execution_id':body['execution_id'],'action_id':body['action_id'],'receipt_id':'r-'+body['execution_id'],'result':{'row_count':count}}
        self.receipts[body['execution_id']]=result
        return result

    def create(self,args=None,actor=None):
        return self.s.create(actor or self.a,args or query(),str(uuid.uuid4()),'127.0.0.1')

    def grant(self,args=None,calls=2,rows=400):
        request=self.create(args or query(columns=['description'],row_limit=200))
        self.assertEqual(request['state'],'PENDING_APPROVAL')
        approved=self.s.decide(self.r,request['id'],'approve','반복 업무 범위를 확인했습니다.',{'ttl_seconds':600,'max_calls':calls,'max_total_rows':rows})
        return approved,approved['scope_grant']

    def test_explicit_low_risk_rule_authorizes_without_human(self):
        r=self.create()
        self.assertEqual((r['decision'],r['state'],r['authorization']['mode']),('ALLOW','APPROVED','automatic'))
        result=self.s.execute(self.a,r['id'])
        self.assertEqual(result['result_count'],100)
        self.assertIsNone(result['reviewer'])

    def test_low_score_alone_does_not_authorize_description(self):
        r=self.create(query(columns=['description']))
        self.assertEqual(r['risk_score'],15)
        self.assertEqual(r['state'],'PENDING_APPROVAL')
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])

    def test_missing_rule_is_review_not_implicit_allow(self):
        self.s.policy.config['automatic_rules']=[]
        self.assertEqual(self.create()['state'],'PENDING_APPROVAL')

    def test_full_human_queue_does_not_block_explicit_automatic_policy(self):
        for _ in range(self.g.policy['limits']['pending_approvals_per_principal']):self.create(query(columns=['description']))
        self.assertEqual(self.create(query(columns=['description']))['state'],'DENIED')
        automatic=self.create()
        self.assertEqual(automatic['authorization']['mode'],'automatic')
        self.assertEqual(self.s.execute(self.a,automatic['id'])['state'],'SUCCEEDED')

    def test_role_change_invalidates_authorized_request_and_cached_result(self):
        from dataclasses import replace
        request=self.create()
        self.s.execute(self.a,request['id'])
        changed=replace(self.a,role='report-writer')
        with self.assertRaises(GatewayError):self.s.execute(changed,request['id'])
        self.assertEqual(len(self.queries),1)

    def test_automatic_requests_do_not_consume_human_review_queue(self):
        for _ in range(10):self.create()
        self.assertEqual(self.create(query(columns=['description']))['state'],'PENDING_APPROVAL')

    def test_policy_violation_cannot_be_approved(self):
        r=self.create(query(columns=['*']))
        self.assertEqual(r['state'],'DENIED')
        with self.assertRaises(GatewayError):self.s.decide(self.r,r['id'],'approve','승인 시도입니다.')
        self.assertEqual(len(self.queries),0)

    def test_new_abnormal_signal_requires_review_even_for_basic_query(self):
        self.s.policy.config['request_rate']={'warning':1,'block':10}
        self.create()
        self.assertEqual(self.create()['state'],'PENDING_APPROVAL')

    def test_expired_and_modified_automatic_authorization_are_rejected(self):
        r=self.create()
        self.g.db.execute('UPDATE db_access_requests SET expires_at=? WHERE id=?',(time.time()-1,r['id']))
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])
        r=self.create()
        self.g.db.execute('UPDATE db_access_requests SET arguments=? WHERE id=?',(json.dumps(query(row_limit=200)),r['id']))
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])

    def test_grant_includes_original_execution_and_reuses_only_same_scope(self):
        original,grant=self.grant()
        self.s.execute(self.a,original['id'])
        follow=self.create(query(columns=['description'],row_limit=100))
        self.assertEqual(follow['authorization']['mode'],'scope_grant')
        self.s.execute(self.a,follow['id'])
        used=self.s.policy.grant_usage(grant['id'])
        self.assertEqual(used,{'calls':2,'rows':300})
        self.assertEqual(self.create(query(columns=['description']))['state'],'PENDING_APPROVAL')

    def test_grant_never_expands_purpose_columns_filters_or_row_limit(self):
        _,grant=self.grant(calls=10,rows=2000)
        for change in ({'purpose':'다른 목적을 가진 요청입니다.'},{'columns':['description','ticket_id']},{'filters':{'status':'open'}},{'row_limit':201}):
            result=self.create(query(columns=['description'],row_limit=200,**change)) if 'columns' not in change and 'row_limit' not in change else self.create(query(**({'columns':['description'],'row_limit':200}|change)))
            self.assertNotEqual(result['authorization'].get('grant_id'),grant['id'])

    def test_grant_revoke_blocks_original_and_cached_result(self):
        r,grant=self.grant()
        self.s.execute(self.a,r['id'])
        self.s.revoke_grant(self.r,grant['id'],'업무가 종료되어 취소합니다.')
        with self.assertRaises(GatewayError) as error:self.s.execute(self.a,r['id'])
        self.assertEqual(error.exception.code,'SCOPE_GRANT_INVALID')

    def test_grant_expiry_and_policy_change_are_enforced(self):
        r,grant=self.grant()
        self.g.db.execute('UPDATE db_scope_grants SET expires_at=? WHERE id=?',(time.time()-1,grant['id']))
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])
        r=self.create()
        self.s.policy.config['version']='changed'
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])

    def test_agents_cannot_issue_revoke_or_list_other_peoples_grants(self):
        r,grant=self.grant()
        for fn in (lambda:self.s.grants(self.a),lambda:self.s.revoke_grant(self.b,grant['id'],'취소 시도입니다.')):
            with self.assertRaises(GatewayError):fn()

    def test_oversized_or_invalid_grant_rolls_back_the_decision(self):
        r=self.create(query(columns=['description']))
        with self.assertRaises(GatewayError):self.s.decide(self.r,r['id'],'approve','검토했습니다.',{'ttl_seconds':600,'max_calls':True,'max_total_rows':1000})
        self.assertEqual(self.s.detail(self.r,r['id'])['state'],'PENDING_APPROVAL')

    def test_cumulative_small_reads_are_blocked(self):
        self.s.policy.config['budget']['max_rows']=150
        first=self.create();second=self.create()
        self.s.execute(self.a,first['id'])
        with self.assertRaises(GatewayError) as error:self.s.execute(self.a,second['id'])
        self.assertEqual(error.exception.code,'DB_BUDGET_EXCEEDED')
        self.assertEqual(self.s.detail(self.r,second['id'])['state'],'DENIED')
        self.assertEqual(len(self.queries),1)

    def test_actual_rows_settle_and_replay_does_not_double_charge(self):
        self.actual=20
        r=self.create();self.s.execute(self.a,r['id']);self.s.execute(self.a,r['id'])
        used=self.s.policy.budget(self.a)
        self.assertEqual((used['used_calls'],used['used_rows']),(1,20))

    def test_lost_response_keeps_reservation_and_retry_does_not_charge_again(self):
        self.s.policy.config['budget']['max_rows']=100
        r=self.create()
        def fail(*args):raise GatewayError(503,'TOOL_UNAVAILABLE','response lost')
        self.g._tool_request=fail
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])
        self.g.db.execute('UPDATE db_query_usage SET reserved_at=?',(time.time()-2000,))
        self.assertEqual(self.s.policy.budget(self.a)['used_rows'],100)
        new=self.create()
        with self.assertRaises(GatewayError):self.s.execute(self.a,new['id'])
        self.g._tool_request=self.tool
        self.s.execute(self.a,r['id'])
        self.assertEqual(self.s.policy.budget(self.a)['used_calls'],1)

    def test_completed_window_expires_but_unresolved_reservation_does_not(self):
        r=self.create();self.s.execute(self.a,r['id'])
        self.g.db.execute('UPDATE db_query_usage SET reserved_at=?',(time.time()-1801,))
        self.assertEqual(self.s.policy.budget(self.a)['used_rows'],0)

    def test_parallel_execution_cannot_overspend_budget(self):
        self.s.policy.config['budget']['max_rows']=300
        requests=[self.create() for _ in range(10)]
        def run(r):
            try:self.s.execute(self.a,r['id']);return 200
            except GatewayError as e:return e.status
        with ThreadPoolExecutor(10) as pool:codes=list(pool.map(run,requests))
        self.assertEqual(codes.count(200),3)
        self.assertEqual(codes.count(429),7)

    def test_grant_concurrent_last_slot_is_consumed_once(self):
        original,grant=self.grant(calls=1,rows=200)
        other=self.create(query(columns=['description'],row_limit=200))
        self.s.execute(self.a,original['id'])
        with self.assertRaises(GatewayError) as error:self.s.execute(self.a,other['id'])
        self.assertEqual(error.exception.code,'SCOPE_GRANT_EXHAUSTED')

    def test_reconcile_after_expiry_only_reads_receipt_and_settles_without_returning_rows(self):
        r=self.create()
        def lost(method,path,body=None):
            self.tool(method,path,body)
            raise GatewayError(503,'TOOL_UNAVAILABLE','lost response')
        self.g._tool_request=lost
        with self.assertRaises(GatewayError):self.s.execute(self.a,r['id'])
        self.g.db.execute('UPDATE db_access_requests SET expires_at=?',(time.time()-1,))
        self.g._tool_request=self.tool
        report=self.s.reconcile(self.r,r['id'])
        self.assertEqual(report['state'],'SUCCEEDED')
        self.assertNotIn('result',report)
        self.assertEqual(len(self.queries),1)
        self.assertEqual(self.s.policy.budget(self.a)['used_rows'],100)
