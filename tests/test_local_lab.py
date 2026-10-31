import json
from pathlib import Path
import socket
import tempfile
import unittest
from contextlib import closing
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from scripts.testbed_launcher import LocalLab, configure_packaged_loopback_http
from scripts.traffic_generator import send_request


class LocalLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.lab = LocalLab(Path(cls.temp.name), 0, 0, 0).start()

    @classmethod
    def tearDownClass(cls):
        cls.lab.stop()
        cls.temp.cleanup()

    def fetch(self, path, method='GET', data=None, headers=None):
        body = json.dumps(data).encode() if data is not None else None
        req = Request(self.lab.url + path, method=method, data=body, headers=headers or {})
        try:
            with urlopen(req, timeout=8) as response:
                return response.status, response.read(), response.headers
        except HTTPError as error:
            return error.code, error.read(), error.headers

    def test_readiness_and_static_files(self):
        for path in ('/', '/app.css', '/app.js', '/soc_dashboard.html', '/health/ready'):
            status, body, headers = self.fetch(path)
            self.assertEqual(status, 200, path)
            self.assertGreater(len(body), 10)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])

    def test_no_directory_or_source_disclosure(self):
        for path in ('/server.py', '/../config/policy.yaml', '/.env', '/api/host-info'):
            self.assertEqual(self.fetch(path)[0], 404)

    def test_local_context_does_not_expose_tokens(self):
        _, body, headers = self.fetch('/api/context')
        self.assertEqual(json.loads(body)['mode'], 'local')
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        for token in self.lab.tokens.values():
            self.assertNotIn(token.encode(), body)

    def test_cross_origin_and_simple_post_are_rejected(self):
        self.assertEqual(self.fetch('/api/generate?mode=normal', 'POST', {})[0], 403)
        self.assertEqual(self.fetch('/api/generate?mode=normal', 'POST', {}, {'X-ASG-Request':'1','Origin':'https://untrusted.test'})[0], 403)

    def test_untrusted_host_is_rejected(self):
        self.assertEqual(self.fetch('/api/context', headers={'Host':'untrusted.test'})[0], 403)

    def test_custom_payload_and_unknown_mode_are_validated(self):
        headers = {'X-ASG-Request':'1'}
        self.assertEqual(self.fetch('/api/generate?mode=missing','POST',{},headers)[0],400)
        for text in ('', None, 42, 'a'*8001):
            self.assertEqual(self.fetch('/api/generate?mode=custom','POST',{'text':text},headers)[0],422)

    def test_same_origin_generator_hits_real_gateway(self):
        status, body, _ = self.fetch('/api/generate?mode=cross-tenant', 'POST', {}, {'X-ASG-Request':'1'})
        self.assertEqual(status,200)
        result = json.loads(body)
        self.assertEqual(result['status'],403)
        self.assertEqual(result['result']['decision'],'DENY')

    def test_report_creates_real_approval_and_no_outbox(self):
        result = self.lab.servers[2].RequestHandlerClass.generator.run_unapproved_report_submit()
        self.assertEqual(result['status'],202)
        self.assertEqual(result['result']['state'],'PENDING_APPROVAL')
        self.assertFalse(result.get('setup_failed'))
        import sqlite3
        with closing(sqlite3.connect(Path(self.temp.name)/'tools.sqlite3')) as conn:
            self.assertEqual(conn.execute('select count(*) from outbox').fetchone()[0],0)

    def test_occupied_port_fails_before_readiness(self):
        # Use a subprocess so handler globals in the active lab stay untouched.
        import subprocess, sys
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable,'-m','scripts.testbed_launcher','--no-browser','--smoke-seconds','0.1', '--data-dir',folder,'--tool-port',str(self.lab.servers[0].server_port)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
        self.assertEqual(result.returncode,1)
        self.assertNotIn('ASG READY',result.stdout)

    def test_duplicate_data_folder_is_rejected(self):
        duplicate=LocalLab(Path(self.temp.name),0,0,0)
        with self.assertRaisesRegex(RuntimeError,'already in use'):
            duplicate.start()
        duplicate.stop()

    def test_dashboard_proxy_preserves_auth_failures(self):
        self.assertEqual(self.fetch('/v1/audit/events',headers={'Authorization':'Bearer wrong'})[0],401)

    def test_sandbox_rejects_direct_unauthenticated_calls(self):
        status, _ = send_request(f'http://127.0.0.1:{self.lab.servers[0].server_port}/internal/artifacts/fake')
        self.assertEqual(status,401)

    def test_packaged_http_transport_rejects_remote_and_https(self):
        from unittest.mock import patch
        from urllib.error import URLError
        with patch('urllib.request._opener', None):
            configure_packaged_loopback_http()
            for url in ('http://untrusted.test/', 'https://127.0.0.1/'):
                with self.assertRaises(URLError):
                    urlopen(url,timeout=1)

    def test_packaged_http_transport_keeps_local_errors(self):
        from unittest.mock import patch
        with patch('urllib.request._opener', None):
            configure_packaged_loopback_http()
            self.assertEqual(self.fetch('/health/ready')[0],200)
            self.assertEqual(self.fetch('/v1/audit/events',headers={'Authorization':'Bearer wrong'})[0],401)
