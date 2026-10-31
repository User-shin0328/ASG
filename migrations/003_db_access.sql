-- Approval-gated structured DB requests and persistent report events.
CREATE TABLE db_access_requests(
 id TEXT PRIMARY KEY,principal TEXT NOT NULL,user_name TEXT NOT NULL,tenant TEXT NOT NULL,
 task_id TEXT NOT NULL,requested_at DOUBLE PRECISION NOT NULL,source_ip TEXT NOT NULL,client TEXT NOT NULL,
 arguments TEXT NOT NULL,analysis TEXT NOT NULL,sensitive INTEGER NOT NULL,bulk INTEGER NOT NULL,
 abnormal INTEGER NOT NULL,risk_score INTEGER NOT NULL,decision TEXT NOT NULL,state TEXT NOT NULL,
 policy_hash TEXT NOT NULL,request_hash TEXT NOT NULL,snapshot_hash TEXT NOT NULL,expires_at DOUBLE PRECISION NOT NULL,
 reviewer TEXT,review_reason TEXT,decided_at DOUBLE PRECISION,execution_id TEXT NOT NULL,
 receipt_id TEXT,result_count INTEGER,idem_key TEXT NOT NULL,trace_id TEXT NOT NULL,
 UNIQUE(principal,idem_key));
CREATE INDEX db_requests_tenant_time ON db_access_requests(tenant,requested_at);
CREATE INDEX db_requests_state_risk ON db_access_requests(tenant,state,risk_score);
CREATE TABLE db_access_events(id TEXT PRIMARY KEY,request_id TEXT NOT NULL,tenant TEXT NOT NULL,
 at DOUBLE PRECISION NOT NULL,actor TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL);
CREATE INDEX db_events_request_time ON db_access_events(request_id,at);
CREATE TRIGGER db_events_no_update_delete BEFORE UPDATE OR DELETE ON db_access_events
 FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER db_events_no_truncate BEFORE TRUNCATE ON db_access_events
 FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation();
REVOKE ALL ON db_access_requests,db_access_events FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON db_access_requests TO gateway_app;
GRANT SELECT,INSERT ON db_access_events TO gateway_app;
