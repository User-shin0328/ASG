import json
from pathlib import Path
import tempfile
import unittest

from testing.report_evidence import seal,verify,publish,report_lock


class ReportEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.folder=self.root/'runs'/'first'
        self.make_run(self.folder,'first')

    def tearDown(self):self.temp.cleanup()

    def make_run(self,folder,run_id):
        folder.mkdir(parents=True)
        report={'run_id':run_id,'source':{'commit':'abc','source_sha256':'fingerprint'},'executable':{},
                'result':'PASS','checks':[{'status':'PASS','actual':{'tests':2}}]}
        (folder/'results.json').write_text(json.dumps(report),encoding='utf-8')
        (folder/'REPORT.md').write_text('run '+run_id,encoding='utf-8')
        (folder/'unittest.log').write_text('ASG_RUN_ID='+run_id+'\nASG_COMMIT=abc\nASG_SOURCE_SHA256=fingerprint\nRan 2 tests in 0.1s\n\nOK\n',encoding='utf-8')

    def test_matching_reports_seal_and_verify(self):
        seal(self.folder)
        self.assertEqual(verify(self.folder)['status'],'VALID')

    def test_overwritten_log_is_detected(self):
        seal(self.folder)
        (self.folder/'unittest.log').write_text('Ran 3 tests\nFAILED (errors=1)\n',encoding='utf-8')
        with self.assertRaises(ValueError):verify(self.folder)

    def test_inconsistent_count_or_outcome_cannot_be_sealed(self):
        path=self.folder/'unittest.log'
        original=path.read_text(encoding='utf-8')
        for bad in (original.replace('Ran 2','Ran 3'),original.replace('OK','FAILED (errors=1)'),original.replace('ASG_RUN_ID=first','ASG_RUN_ID=other')):
            path.write_text(bad,encoding='utf-8')
            with self.assertRaises(ValueError):seal(self.folder)

    def test_publication_preserves_previous_latest_and_unique_runs(self):
        seal(self.folder);publish(self.folder,self.root)
        second=self.root/'runs'/'second';self.make_run(second,'second');seal(second);publish(second,self.root)
        self.assertEqual(verify(self.root/'latest')['run_id'],'second')
        self.assertTrue((self.folder/'manifest.json').exists())
        previous=list((self.root/'history').glob('previous-latest-*'))
        self.assertEqual(len(previous),1)
        self.assertEqual(verify(previous[0])['run_id'],'first')

    def test_two_report_writers_cannot_run_together(self):
        with report_lock(self.root):
            with self.assertRaises(RuntimeError):
                with report_lock(self.root):pass
