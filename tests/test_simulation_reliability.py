import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from gateway.app.core import Gateway, GatewayError
from scripts.testbed_launcher import LocalLab
from scripts.traffic_generator import send_request
from tests import virtual_agent_simulation as sim


class SimulationContractTests(unittest.TestCase):
    def test_operational_risk_boundaries_and_console_use_server_label(self):
        gateway=Gateway(':memory:',{'agent-alice':'a'*40,'reviewer-demo':'r'*40})
        try:
            now=time.time()
            for count,label in ((0,'낮음'),(2,'주의'),(5,'높음')):
                rows=[{'requested_at':now,'sensitive':0,'bulk':0,'abnormal':1} for _ in range(count)]
                risk=gateway.db_access.risk_at(rows,now)
                self.assertEqual(risk['level'],label)
            output=io.StringIO()
            transport=lambda *a,**k:(200,{'metrics':{'today_total':5,'allowed':0,'pending':0,'blocked':5},'risk':risk})
            with contextlib.redirect_stdout(output):sim.print_overview('http://local','r'*40,transport)
            self.assertIn('100점 (높음)',output.getvalue())
            self.assertNotIn('(정상)',output.getvalue())
        finally:gateway.db.close()

    def test_missing_risk_level_is_unknown_not_normal(self):
        data={'metrics':dict(today_total=0,allowed=0,pending=0,blocked=0),'risk':{'score':100}}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            sim.print_overview('http://local','r'*40,lambda *a,**k:(200,data))
        self.assertIn('등급 확인 불가',output.getvalue())

    def test_transport_failure_does_not_claim_block_or_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result=sim.run_scenario(4,'http://local','a'*40,lambda *a,**k:(503,{'error':'GATEWAY_UNAVAILABLE'}))
        self.assertFalse(result.ok)
        self.assertIn('확인 실패',output.getvalue())
        self.assertNotIn('정책 차단',output.getvalue())

    def test_business_denial_is_printed_as_denied_not_pending(self):
        body={'id':'denied','state':'DENIED','analysis':{'reasons':['PENDING_DB_REQUEST_LIMIT']}}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result=sim.run_scenario(2,'http://local','a'*40,lambda *a,**k:(403,body))
        self.assertTrue(result.ok)
        self.assertFalse(result.baseline_matches)
        self.assertIn('정책 차단',output.getvalue())
        self.assertNotIn('사람 승인 대기',output.getvalue())

    def test_failed_execution_is_not_reported_as_completed(self):
        calls=iter([(200,{'id':'r','state':'APPROVED'}),(503,{'error':'TOOL_UNAVAILABLE'})])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result=sim.run_scenario(1,'http://local','a'*40,lambda *a,**k:next(calls))
        self.assertFalse(result.ok)
        self.assertFalse(result.baseline_matches)
        self.assertNotIn('조회 완료',output.getvalue())

    def test_monitor_keeps_failed_execution_then_reads_receipt(self):
        calls=[]
        responses=iter([(200,{'id':'r','state':'APPROVED'}),(503,{'error':'lost'}),
                        (200,{'id':'r','state':'UNKNOWN'}),
                        (200,{'id':'r','state':'SUCCEEDED','receipt_id':'receipt','result_count':10})])
        def transport(url,*args,**kwargs):calls.append(url);return next(responses)
        result=sim.ScenarioResult(2,202,'PENDING_APPROVAL',{'id':'r','state':'PENDING_APPROVAL'})
        monitor=sim.ReviewMonitor('http://local','a'*40,'r'*40,transport)
        monitor.register(result)
        with contextlib.redirect_stdout(io.StringIO()):
            monitor.poll_once(force=True)
            self.assertIn('r',monitor.jobs)
            self.assertFalse(result.ok)
            monitor.poll_once(force=True)
        self.assertNotIn('r',monitor.jobs)
        self.assertTrue(result.ok)
        self.assertEqual(result.confirmation,'stored_receipt')
        self.assertEqual(sum(u.endswith('/execute') for u in calls),1)
        self.assertEqual(sum(u.endswith('/reconcile') for u in calls),1)

    def test_monitor_failure_limit_and_explicit_retry(self):
        result=sim.ScenarioResult(2,202,'PENDING_APPROVAL',{'id':'r','state':'PENDING_APPROVAL'})
        calls=[]
        def unavailable(*a,**k):calls.append(1);return 503,{}
        monitor=sim.ReviewMonitor('http://local','a'*40,'r'*40,unavailable,max_failures=2)
        monitor.register(result)
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(5):monitor.poll_once(force=True)
            self.assertEqual(len(calls),2)
            self.assertTrue(monitor.jobs['r'].paused)
            monitor.retry_paused()
            monitor.poll_once(force=True)
        self.assertEqual(len(calls),3)
        self.assertFalse(result.ok)

    def test_monitor_terminal_states_and_thread_shutdown(self):
        for state in ('DENIED','REJECTED','EXPIRED'):
            result=sim.ScenarioResult(2,202,'PENDING_APPROVAL',{'id':'r','state':'PENDING_APPROVAL'})
            monitor=sim.ReviewMonitor('http://local','a'*40,'r'*40,lambda *a,**k:(200,{'id':'r','state':state}))
            monitor.register(result)
            with contextlib.redirect_stdout(io.StringIO()):monitor.poll_once()
            self.assertFalse(monitor.jobs)
            monitor.start();monitor.close()
            self.assertFalse(monitor.thread.is_alive())

    def test_auto_mode_returns_failure_and_evidence_when_all_requests_fail(self):
        class FakeLab:
            url=gateway_url='http://local'
            tokens={'agent-alice':'a'*40,'reviewer-demo':'r'*40}
            def start(self):return self
            def stop(self):pass
        with tempfile.TemporaryDirectory() as tmp,patch.object(sim,'LocalLab',return_value=FakeLab()),patch.object(sim,'send_request',return_value=(503,{'error':'offline'})),contextlib.redirect_stdout(io.StringIO()):
            path=Path(tmp)/'result.json'
            code=sim.main(['--auto','--no-browser','--report-file',str(path)])
            data=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(code,1)
        self.assertEqual(data['result'],'FAIL')
        self.assertEqual(len(data['scenarios']),5)
        self.assertTrue(all(not r['ok'] for r in data['scenarios']))


class SimulationReceiptIntegrationTests(unittest.TestCase):
    def test_real_lost_response_recovery_keeps_one_query_and_one_charge(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            lab=LocalLab(Path(tmp),0,0,0).start()
            monitor=sim.ReviewMonitor(lab.gateway_url,lab.tokens['agent-alice'],lab.tokens['reviewer-demo'])
            try:
                result=sim.run_scenario(2,lab.gateway_url,lab.tokens['agent-alice'])
                endpoint=lab.gateway_url+'/v1/db/requests/'+result.request['id']
                code,_=send_request(endpoint+'/decision','POST',sim.make_headers(lab.tokens['reviewer-demo']),{'decision':'approve','reason':'실행 응답 유실 복구를 검증합니다.'})
                self.assertEqual(code,200)
                original=lab.gateway._tool_request
                queries=[]
                def lose(method,path,body=None):
                    value=original(method,path,body)
                    if method=='POST':
                        queries.append(body['execution_id'])
                        raise GatewayError(503,'TOOL_UNAVAILABLE','response lost')
                    return value
                monitor.register(result)
                lab.gateway._tool_request=lose
                monitor.poll_once(force=True)
                self.assertFalse(result.ok)
                self.assertIn(result.request['id'],monitor.jobs)
                lab.gateway._tool_request=original
                monitor.poll_once(force=True)
                self.assertTrue(result.ok)
                self.assertEqual(result.request['result_count'],10)
                self.assertEqual(result.confirmation,'stored_receipt')
                self.assertEqual(len(queries),1)
                actor=lab.gateway.authenticate(lab.tokens['agent-alice'])
                used=lab.gateway.db_access.policy.budget(actor)
                self.assertEqual((used['used_calls'],used['used_rows']),(1,10))
            finally:monitor.close();lab.stop()

    def test_full_auto_simulation_returns_success_and_leaves_no_monitor(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            path=Path(tmp)/'results.json'
            code=sim.main(['--auto','--no-browser','--report-file',str(path)])
            data=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(code,0)
        self.assertEqual(data['result'],'PASS')
        self.assertEqual(data['scenarios'][0]['rows'],20)
        self.assertFalse(any(t.name=='ASGSimulationReviewMonitor' and t.is_alive() for t in threading.enumerate()))
