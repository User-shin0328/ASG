from __future__ import annotations
import copy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
from gateway.app.core import Gateway,GatewayError,Principal
from gateway.app.db_access import day_bounds
from scripts.testbed_launcher import LocalLab
from scripts.traffic_generator import send_request


def query(**changes):
    return dict({'dataset_id':'operations','columns':['ticket_id','status','description'],'filters':{},'row_limit':25,
        'purpose':'운영 지원 현황을 확인하기 위한 검증 요청입니다.'},**changes)


class DBPolicyTests(unittest.TestCase):
    def setUp(self):
        self.g=Gateway(':memory:',{'agent-alice':'a'*40,'agent-bob':'b'*40,'reviewer-demo':'r'*40})
        self.service=self.g.db_access
        self.alice=self.g.authenticate('a'*40)
        self.bob=self.g.authenticate('b'*40)
        self.reviewer=self.g.authenticate('r'*40)

    def tearDown(self):self.g.db.close()

    def create(self,payload=None,principal=None,key=None):
        return self.service.create(principal or self.alice,payload or query(),key or str(uuid.uuid4()),'192.0.2.15','Unit test agent')

    def test_exception_reads_need_human_approval(self):
        r=self.create()
        self.assertEqual(r['state'],'PENDING_APPROVAL')
        self.assertEqual(r['analysis']['decision'],'REQUIRE_APPROVAL')
        with self.assertRaises(GatewayError) as error:self.service.execute(self.alice,r['id'])
        self.assertEqual(error.exception.code,'DB_APPROVAL_REQUIRED')

    def test_parallel_authentication_never_loses_registered_principal(self):
        from concurrent.futures import ThreadPoolExecutor
        def authenticate(_):
            try:return self.g.authenticate('r'*40).id
            except GatewayError:return 'UNAUTHENTICATED'
        with ThreadPoolExecutor(12) as pool:results=list(pool.map(authenticate,range(1500)))
        self.assertEqual(set(results),{'reviewer-demo'})

    def test_sensitive_and_bulk_increase_explainable_analysis(self):
        ordinary=self.create()
        sensitive=self.create(query(dataset_id='payroll',columns=['salary','bank_account']))
        bulk=self.create(query(row_limit=2000))
        self.assertGreater(sensitive['risk_score'],ordinary['risk_score'])
        self.assertGreater(bulk['risk_score'],ordinary['risk_score'])
        self.assertTrue(sensitive['analysis']['sensitive'])
        self.assertTrue(bulk['analysis']['bulk'])
        self.assertTrue(sensitive['analysis']['recommendation'])

    def test_raw_sql_and_unregistered_columns_are_blocked(self):
        for body in (query(sql='SELECT * FROM users'),query(columns=['*']),query(columns=['password']),query(row_limit=5001)):
            r=self.create(body)
            self.assertEqual(r['state'],'DENIED')
            with self.assertRaises(GatewayError):self.service.decide(self.reviewer,r['id'],'approve','검토 완료')

    def test_tenant_and_role_scope_are_enforced(self):
        r=self.create(query(dataset_id='payroll',columns=['salary']),self.bob)
        self.assertEqual(r['state'],'DENIED')
        with self.assertRaises(GatewayError):self.service.detail(self.reviewer,r['id'])

    def test_agent_cannot_approve_or_view_reviewer_lists(self):
        r=self.create()
        for operation in (lambda:self.service.decide(self.alice,r['id'],'approve','검토 완료'),lambda:self.service.listing(self.alice),lambda:self.service.overview(self.alice)):
            with self.assertRaises(GatewayError) as error:operation()
            self.assertEqual(error.exception.status,403)

    def test_expired_approval_and_double_decision_are_blocked(self):
        r=self.create()
        self.g.db.execute('UPDATE db_access_requests SET expires_at=? WHERE id=?',(time.time()-1,r['id']))
        with self.assertRaises(GatewayError):self.service.decide(self.reviewer,r['id'],'approve','확인 완료')
        r=self.create()
        self.service.decide(self.reviewer,r['id'],'reject','불필요한 요청입니다.')
        with self.assertRaises(GatewayError):self.service.decide(self.reviewer,r['id'],'approve','확인 완료')

    def test_request_policy_and_analysis_are_bound(self):
        r=self.create()
        self.g.db.execute('UPDATE db_access_requests SET arguments=? WHERE id=?',(json.dumps(query(row_limit=100)),r['id']))
        with self.assertRaises(GatewayError) as error:self.service.decide(self.reviewer,r['id'],'approve','확인 완료')
        self.assertEqual(error.exception.code,'DB_SNAPSHOT_CHANGED')

    def test_idempotency_has_one_request_and_detects_content_changes(self):
        a=self.create(key='repeat');b=self.create(key='repeat')
        self.assertEqual(a['id'],b['id'])
        with self.assertRaises(GatewayError):self.create(query(row_limit=50),key='repeat')

    def test_risk_decays_and_expires_exactly_at_30_minutes(self):
        rows=[{'requested_at':10000,'sensitive':1,'bulk':1,'abnormal':1}]
        self.assertEqual(self.service.risk_at(rows,10000)['score'],42)
        self.assertEqual(self.service.risk_at(rows,10900)['score'],21)
        self.assertEqual(self.service.risk_at(rows,11800)['score'],0)
        self.assertEqual(self.service.risk_at(rows,9999)['score'],0)

    def test_risk_is_bounded_and_counts_each_factor(self):
        rows=[{'requested_at':10000,'sensitive':1,'bulk':1,'abnormal':1}]*10
        risk=self.service.risk_at(rows,10000)
        self.assertEqual(risk['score'],100)
        self.assertEqual(risk['factors'],{'sensitive':10,'bulk':10,'abnormal':10})

    def test_date_range_uses_korea_midnight(self):
        start,end=day_bounds('2026-10-31')
        self.assertEqual(datetime.fromtimestamp(start,timezone.utc).isoformat(),'2026-10-30T15:00:00+00:00')
        self.assertEqual(end-start,86400)
        with self.assertRaises(GatewayError):day_bounds('2026-99-99')

    def test_audit_pagination_and_risk_sort(self):
        low=self.create();high=self.create(query(dataset_id='payroll',columns=['salary']))
        rows=self.service.listing(self.reviewer,pending=True,sort='risk')['items']
        self.assertEqual(rows[0]['id'],high['id'])
        self.assertEqual(self.service.listing(self.reviewer,date='2000-01-01')['total'],0)
        r=self.service.detail(self.reviewer,low['id'])
        self.assertEqual(r['source_ip'],'192.0.2.15')
        self.assertEqual(r['timeline'][0]['event'],'DB_REQUESTED')

    def test_report_events_cannot_be_updated_or_deleted(self):
        r=self.create()
        for sql in ('UPDATE db_access_events SET actor=actor','DELETE FROM db_access_events'):
            with self.assertRaises(Exception):self.g.db.execute(sql)
        self.assertEqual(self.service.detail(self.reviewer,r['id'])['timeline'][0]['actor'],'agent-alice')

    def test_security_agent_failure_blocks_and_records_reason(self):
        with patch.object(self.service.agent,'assess',side_effect=RuntimeError('unavailable')):
            result=self.create()
        self.assertEqual(result['state'],'DENIED')
        self.assertIn('SECURITY_AGENT_UNAVAILABLE',result['analysis']['reason_codes'])

    def test_bad_input_types_are_reported_without_executing(self):
        for args in (query(dataset_id=[]),query(columns=[{}]),query(row_limit=True),query(filters=[])):
            result=self.create(args)
            self.assertEqual(result['state'],'DENIED')

    def test_overview_counts_reconcile_and_history_survives(self):
        self.create();self.create(query(columns=['*']))
        data=self.service.overview(self.reviewer)
        self.assertEqual(data['metrics']['today_total'],sum(data['metrics'][key] for key in ('pending','allowed','blocked')))
        self.assertEqual(sum(point['count'] for point in data['activity']),2)
        self.assertEqual(len(data['risk_trend']),31)

    def test_audit_can_page_beyond_200_requests(self):
        for _ in range(205):self.create(query(columns=['*']))
        page=self.service.listing(self.reviewer,page=5)
        self.assertEqual(page['total'],205)
        self.assertEqual(len(page['items']),5)

    def test_historical_day_is_preserved_and_separate_from_today(self):
        at=day_bounds('2020-01-02')[0]+60
        with patch('gateway.app.db_access.time.time',return_value=at):r=self.create()
        self.assertEqual(self.service.listing(self.reviewer,date='2020-01-02')['total'],1)
        self.assertEqual(self.service.overview(self.reviewer)['metrics']['today_total'],0)
        self.assertEqual(self.service.detail(self.reviewer,r['id'])['state'],'EXPIRED')


class DBHTTPIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.lab=LocalLab(Path(self.temp.name),0,0,0).start()
        self.headers={'Authorization':'Bearer '+self.lab.tokens['agent-alice'],'Idempotency-Key':str(uuid.uuid4())}

    def tearDown(self):
        self.lab.stop();self.temp.cleanup()

    def test_real_request_approval_query_and_cached_receipt(self):
        status,r=send_request(self.lab.gateway_url+'/v1/db/requests','POST',self.headers,query())
        self.assertEqual(status,202)
        url=self.lab.gateway_url+'/v1/db/requests/'+r['id']
        status,_=send_request(url+'/execute','POST',self.headers,{})
        self.assertEqual(status,409)
        reviewer={'X-ASG-Request':'1'}
        status,approved=send_request(self.lab.url+'/v1/db/requests/'+r['id']+'/decision','POST',reviewer,{'decision':'approve','reason':'업무 범위를 확인했습니다.'})
        self.assertEqual(status,200)
        self.assertEqual(approved['state'],'APPROVED')
        status,result=send_request(url+'/execute','POST',self.headers,{})
        self.assertEqual(status,200)
        self.assertEqual(result['result_count'],25)
        self.assertEqual(set(result['result']['result']['rows'][0]),{'ticket_id','status','description'})
        _,again=send_request(url+'/execute','POST',self.headers,{})
        self.assertTrue(again['replayed'])
        self.assertEqual(result['receipt_id'],again['receipt_id'])

    def test_one_click_diagnostics_are_real_and_fail_on_missing_dependency(self):
        status,result=send_request(self.lab.url+'/v1/db/diagnostics','POST',{'X-ASG-Request':'1'},{})
        self.assertEqual(status,200)
        self.assertTrue(result['passed'])
        original=self.lab.gateway.tool_url
        self.lab.gateway.tool_url='http://127.0.0.1:1'
        try:
            status,data=send_request(self.lab.url+'/v1/db/status',timeout=15)
            self.assertEqual(status,200)
            states={item['key']:item['status'] for item in data['items']}
            self.assertEqual(states['protected_db'],'down')
            self.assertEqual(states['gateway'],'down')
            self.assertEqual(states['security_agent'],'up')
        finally:self.lab.gateway.tool_url=original

    def test_page_routes_load_and_mutations_reject_foreign_origins(self):
        from urllib.request import urlopen
        for path in ('/','/approvals','/audit','/tests'):
            with urlopen(self.lab.url+path) as res:self.assertEqual(res.status,200)
        code,_=send_request(self.lab.url+'/api/db-demo','POST',{'Origin':'http://untrusted.test','X-ASG-Request':'1'},{'scenario':'normal'})
        self.assertEqual(code,403)

    def test_post_approval_tampering_and_other_agent_execution_are_blocked(self):
        _,r=send_request(self.lab.gateway_url+'/v1/db/requests','POST',self.headers,query())
        reviewer=self.lab.gateway.authenticate(self.lab.tokens['reviewer-demo'])
        self.lab.gateway.db_access.decide(reviewer,r['id'],'approve','검토 완료했습니다.')
        self.lab.gateway.db.execute('UPDATE db_access_requests SET arguments=? WHERE id=?',(json.dumps(query(row_limit=100)),r['id']))
        status,_=send_request(self.lab.gateway_url+'/v1/db/requests/'+r['id']+'/execute','POST',self.headers,{})
        self.assertEqual(status,403)
        status,_=send_request(self.lab.gateway_url+'/v1/db/requests/'+r['id']+'/execute','POST',{'Authorization':'Bearer '+self.lab.tokens['agent-bob']},{})
        self.assertEqual(status,404)

    def test_db_request_reports_survive_gateway_restart(self):
        _,r=send_request(self.lab.gateway_url+'/v1/db/requests','POST',self.headers,query())
        self.lab.stop()
        self.lab=LocalLab(Path(self.temp.name),0,0,0).start()
        code,report=send_request(self.lab.url+'/v1/db/requests/'+r['id'])
        self.assertEqual(code,200)
        self.assertEqual(report['timeline'][0]['event'],'DB_REQUESTED')
