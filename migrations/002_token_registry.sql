CREATE TABLE token_registry (
    token_hash TEXT PRIMARY KEY,
    principal TEXT NOT NULL,
    issued DOUBLE PRECISION NOT NULL,
    revoked DOUBLE PRECISION
);

CREATE INDEX token_registry_principal_idx ON token_registry(principal);
REVOKE ALL ON token_registry FROM PUBLIC;
GRANT SELECT, INSERT ON token_registry TO gateway_app;
