from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from security_agent.db_target import target_config
from tool_sandbox.protected_db import _pg_config, execute_query
from tests import test_db_access as db_access_tests


class ProtectedDBConfigTests(unittest.TestCase):
    def test_default_is_sqlite(self):
        self.assertEqual(target_config({}), {'backend':'sqlite','id':'sqlite-lab-v1'})

    def test_unknown_backend_and_missing_postgres_target_fail(self):
        for env in ({'PROTECTED_DB_BACKEND':'mysql'}, {'PROTECTED_DB_BACKEND':'postgresql'}):
            with self.assertRaises(ValueError): target_config(env)

    def test_invalid_schema_and_tls_fail_before_connect(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'dsn.txt'
            path.write_text('host=corporate.example dbname=business user=asg_reader sslmode=disable',encoding='utf-8')
            env={'PROTECTED_DB_DSN_FILE':str(path)}
            with patch.dict('os.environ',env,clear=True):
                with self.assertRaises(ValueError): _pg_config()
            with patch.dict('os.environ',env|{'PROTECTED_DB_LOCAL_TEST':'1'},clear=True):
                with self.assertRaises(ValueError): _pg_config()
            path.write_text('host=127.0.0.1 dbname=business user=asg_reader sslmode=disable',encoding='utf-8')
            with patch.dict('os.environ',env|{'PROTECTED_DB_LOCAL_TEST':'1','PROTECTED_DB_SCHEMA':'public; DROP SCHEMA public'},clear=True):
                with self.assertRaises(ValueError): _pg_config()

    def test_target_mismatch_fails_before_sql(self):
        with patch.dict('os.environ',{'PROTECTED_DB_BACKEND':'sqlite','PROTECTED_DB_TARGET_ID':'lab-v2'},clear=True):
            with self.assertRaises(ValueError): execute_query(None,{},'north','report-submitter','lab-v1')

    def test_keyword_dsn_is_never_used_as_a_sqlite_filename(self):
        from gateway.app.database import Database
        with patch.object(Database,'_connect_postgres',return_value=object()) as connect:
            database=Database('user=reader dbname=business host=127.0.0.1')
        self.assertTrue(database.is_postgres)
        connect.assert_called_once()


class TargetBindingTests(unittest.TestCase):
    setUp=db_access_tests.DBPolicyTests.setUp
    tearDown=db_access_tests.DBPolicyTests.tearDown
    create=db_access_tests.DBPolicyTests.create
    def test_switching_target_invalidates_human_approval(self):
        r=self.create()
        self.service.decide(self.reviewer,r['id'],'approve','조회 범위를 검토했습니다.')
        self.service.target={'backend':'postgresql','id':'another-db-v2'}
        from gateway.app.core import GatewayError
        with self.assertRaises(GatewayError) as caught:self.service.execute(self.alice,r['id'])
        self.assertEqual(caught.exception.code,'DB_POLICY_CHANGED')
