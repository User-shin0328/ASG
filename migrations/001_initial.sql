CREATE TABLE actions (
    id TEXT PRIMARY KEY,
    principal TEXT NOT NULL,
    task TEXT NOT NULL,
    tool TEXT NOT NULL,
    arguments TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    idem_key TEXT NOT NULL,
    decision TEXT NOT NULL,
    state TEXT NOT NULL,
    reasons TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    execution_id TEXT,
    approval_id TEXT,
    created DOUBLE PRECISION NOT NULL,
    UNIQUE (principal, task, idem_key)
);

CREATE INDEX actions_principal_created_idx ON actions(principal, created DESC);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL UNIQUE REFERENCES actions(id),
    snapshot_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    reviewer TEXT,
    expires DOUBLE PRECISION NOT NULL,
    used DOUBLE PRECISION
);

CREATE INDEX approvals_state_expires_idx ON approvals(state, expires);

CREATE TABLE audit (
    id BIGSERIAL PRIMARY KEY,
    at DOUBLE PRECISION NOT NULL,
    trace_id TEXT NOT NULL,
    action_id TEXT,
    actor TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE INDEX audit_action_id_id_idx ON audit(action_id, id DESC);

CREATE FUNCTION reject_audit_mutation() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit is append only';
END;
$$;

CREATE TRIGGER audit_no_update_delete
BEFORE UPDATE OR DELETE ON audit
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();

CREATE TRIGGER audit_no_truncate
BEFORE TRUNCATE ON audit
FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation();

CREATE TABLE inspections (
    id TEXT PRIMARY KEY,
    principal TEXT NOT NULL,
    source TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reasons TEXT NOT NULL,
    scanner_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created DOUBLE PRECISION NOT NULL
);

REVOKE ALL ON actions, approvals, audit, inspections FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON actions, approvals, inspections TO gateway_app;
GRANT SELECT, INSERT ON audit TO gateway_app;
GRANT USAGE, SELECT ON SEQUENCE audit_id_seq TO gateway_app;
