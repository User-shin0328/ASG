ALTER TABLE db_access_requests ADD COLUMN authorization_mode TEXT;
ALTER TABLE db_access_requests ADD COLUMN grant_id TEXT;
ALTER TABLE db_access_requests ADD COLUMN automatic_rule_id TEXT;
CREATE TABLE db_scope_grants(
 id TEXT PRIMARY KEY,source_request_id TEXT UNIQUE NOT NULL,principal TEXT NOT NULL,tenant TEXT NOT NULL,
 scope_key TEXT NOT NULL,arguments TEXT NOT NULL,policy_hash TEXT NOT NULL,issued_by TEXT NOT NULL,
 reason TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL,
 max_calls INTEGER NOT NULL,max_total_rows INTEGER NOT NULL,status TEXT NOT NULL,
 revoked_by TEXT,revoked_reason TEXT,revoked_at DOUBLE PRECISION);
CREATE INDEX db_grants_scope ON db_scope_grants(principal,scope_key,status);
CREATE TABLE db_query_usage(
 request_id TEXT PRIMARY KEY,principal TEXT NOT NULL,tenant TEXT NOT NULL,grant_id TEXT,
 reserved_at DOUBLE PRECISION NOT NULL,reserved_rows INTEGER NOT NULL,actual_rows INTEGER,state TEXT NOT NULL);
CREATE INDEX db_usage_principal_time ON db_query_usage(principal,reserved_at);
CREATE INDEX db_usage_grant ON db_query_usage(grant_id);
REVOKE ALL ON db_scope_grants,db_query_usage FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON db_scope_grants,db_query_usage TO gateway_app;
