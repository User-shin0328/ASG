from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse
from security_agent.catalog import initialize_demo_database
from tool_sandbox import protected_db
from security_agent.http_safety import SafeHTTPHandler, BoundedHTTPServer, HTTPBodyError, read_json_body

DATA = Path(__file__).resolve().parent.parent / "fixtures" / "documents"
DATABASE = os.environ.get("TOOL_DATABASE_PATH", "/data/tool.sqlite3")
TOKEN = os.environ.get("TOOL_SERVICE_TOKEN", "")
DOCS = {
    "report-alice-001": ("alice", "north", "alice.txt"),
    "report-bob-001": ("bob", "south", "bob.txt"),
    "report-alice-attack": ("alice", "north", "injection.txt"),
}
TASK_DOCS = {"task-alice-001": ("alice", "north", {"report-alice-001", "report-alice-attack"}), "task-bob-001": ("bob", "south", {"report-bob-001"})}
_SCHEMA_LOCK = threading.Lock()
_INITIALIZED = set()
_QUERY_GUARD=threading.Lock()
_QUERY_LOCKS={}


@contextmanager
def query_lock(execution_id):
    with _QUERY_GUARD:
        entry=_QUERY_LOCKS.setdefault(execution_id,[threading.Lock(),0])
        entry[1]+=1
    acquired=entry[0].acquire(timeout=10)
    try:
        if not acquired:raise TimeoutError('Execution is busy')
        yield
    finally:
        if acquired:entry[0].release()
        with _QUERY_GUARD:
            entry[1]-=1
            if not entry[1]:_QUERY_LOCKS.pop(execution_id,None)


def database_execution(c,req):
    """Claim once, query without a SQLite writer lock, then persist the receipt."""
    from security_agent.catalog import validate_query
    roles={'agent-alice':'report-submitter','agent-bob':'report-writer'}
    if (req['principal'],req['user']) not in {('agent-alice','alice'),('agent-bob','bob')}:
        return 403,{'error':'DB_PRINCIPAL_FORBIDDEN'}
    args=dict(req['arguments'])
    target=args.pop('_asg_target_id',None)
    role=roles[req['principal']]
    if validate_query(args,{'tenant':req['tenant'],'role':role}) or target!=protected_db.target_config()['id']:
        return 403,{'error':'DB_QUERY_FORBIDDEN'}
    binding=hashlib.sha256(json.dumps(req,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with query_lock(req['execution_id']):
        c.execute('BEGIN IMMEDIATE')
        try:
            old=c.execute('SELECT * FROM receipts WHERE execution_id=?',(req['execution_id'],)).fetchone()
            claim=c.execute('SELECT * FROM db_execution_claims WHERE execution_id=?',(req['execution_id'],)).fetchone()
            if claim and claim['binding']!=binding:
                c.execute('ROLLBACK')
                return 409,{'error':'EXECUTION_ID_CONFLICT'}
            if old:
                c.execute('COMMIT')
                return 200,{'receipt_id':old['receipt_id'],'execution_id':req['execution_id'],'result':json.loads(old['result'])}
            if claim:
                c.execute('COMMIT')
                return 503,{'error':'DB_EXECUTION_UNCERTAIN'}
            c.execute('INSERT INTO db_execution_claims VALUES(?,?,?)',(req['execution_id'],binding,time.time()))
            c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        # An interrupted claim without a receipt stays uncertain; never run its SQL twice.
        result=protected_db.execute_query(c,args,req['tenant'],role,target)
        receipt='receipt-'+str(uuid.uuid4())
        c.execute('BEGIN IMMEDIATE')
        try:
            c.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(req['execution_id'],req['action_id'],req['request_hash'],receipt,json.dumps(result,ensure_ascii=False),time.time()))
            c.execute('COMMIT')
        except Exception:
            c.execute('ROLLBACK')
            raise
        return 200,{'receipt_id':receipt,'execution_id':req['execution_id'],'result':result}


def connect():
    Path(DATABASE).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DATABASE, timeout=10, isolation_level=None)
    c.row_factory = sqlite3.Row
    if DATABASE not in _INITIALIZED:
        with _SCHEMA_LOCK:
            if DATABASE not in _INITIALIZED:
                c.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,owner TEXT NOT NULL,tenant TEXT NOT NULL,document_id TEXT NOT NULL,content TEXT NOT NULL,content_hash TEXT NOT NULL,created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,execution_id TEXT UNIQUE NOT NULL,artifact_id TEXT NOT NULL,destination_id TEXT NOT NULL,content_hash TEXT NOT NULL,created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS receipts(execution_id TEXT PRIMARY KEY,action_id TEXT NOT NULL,request_hash TEXT NOT NULL,receipt_id TEXT NOT NULL,result TEXT NOT NULL,created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS db_execution_claims(execution_id TEXT PRIMARY KEY,binding TEXT NOT NULL,created REAL NOT NULL);
    CREATE TRIGGER IF NOT EXISTS db_claims_no_update BEFORE UPDATE ON db_execution_claims BEGIN SELECT RAISE(ABORT,'execution claims are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS db_claims_no_delete BEFORE DELETE ON db_execution_claims BEGIN SELECT RAISE(ABORT,'execution claims are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS artifacts_no_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS artifacts_no_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT,'receipts are append only'); END;
    CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT,'receipts are append only'); END;
    CREATE TRIGGER IF NOT EXISTS outbox_no_update BEFORE UPDATE ON outbox BEGIN SELECT RAISE(ABORT,'outbox is append only'); END;
    CREATE TRIGGER IF NOT EXISTS outbox_no_delete BEFORE DELETE ON outbox BEGIN SELECT RAISE(ABORT,'outbox is append only'); END;
                """)
                if protected_db.target_config()['backend'] == 'sqlite':
                    initialize_demo_database(c)
                _INITIALIZED.add(DATABASE)
    return c


class Handler(SafeHTTPHandler):
    server_version = "ToolSandbox/0.1"

    def log_message(self, fmt, *args):
        return

    def send_json(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def authorized(self):
        if not TOKEN:
            return False
        return self.headers.get("Authorization") == "Bearer " + TOKEN

    def read_body(self):
        return read_json_body(self, 20000)

    def do_GET(self):
        if self.path == "/health/live":
            return self.send_json(200, {"status": "live"})
        if not self.authorized():
            return self.send_json(401, {"error": "UNAUTHENTICATED"})
        path = urlparse(self.path).path
        c = connect()
        try:
            if path == '/internal/db-health':
                try:
                    return self.send_json(200, protected_db.health(c))
                except Exception:
                    return self.send_json(503, {'error':'PROTECTED_DB_UNAVAILABLE'})
            if path.startswith("/internal/artifacts/"):
                aid = unquote(path.rsplit("/", 1)[1])
                r = c.execute("SELECT id,owner,tenant,document_id,content,content_hash,created FROM artifacts WHERE id=?", (aid,)).fetchone()
                return self.send_json(404, {"error": "NOT_FOUND"}) if not r else self.send_json(200, dict(r))
            if path.startswith("/internal/executions/"):
                eid = unquote(path.rsplit("/", 1)[1])
                r = c.execute("SELECT execution_id,action_id,receipt_id,result,created FROM receipts WHERE execution_id=?", (eid,)).fetchone()
                return self.send_json(404, {"error": "NOT_FOUND"}) if not r else self.send_json(200, dict(r) | {"result": json.loads(r["result"])} )
            return self.send_json(404, {"error": "NOT_FOUND"})
        finally:
            c.close()

    def do_POST(self):
        if not self.authorized():
            return self.send_json(401, {"error": "UNAUTHENTICATED"})
        if self.path != "/internal/execute":
            return self.send_json(404, {"error": "NOT_FOUND"})
        try:
            req = self.read_body()
            required = {"execution_id", "action_id", "principal", "user", "tenant", "task_id", "tool", "arguments", "request_hash"}
            if set(req) != required or not all(isinstance(req[k], str) for k in required - {"arguments"}) or not isinstance(req["arguments"], dict):
                return self.send_json(422, {"error": "INVALID_REQUEST"})
            c = connect()
            try:
                old = c.execute("SELECT * FROM receipts WHERE execution_id=?", (req["execution_id"],)).fetchone()
                if old:
                    if old["request_hash"] != req["request_hash"]:
                        return self.send_json(409, {"error": "EXECUTION_ID_CONFLICT"})
                    return self.send_json(200, {"receipt_id": old["receipt_id"], "result": json.loads(old["result"]), "execution_id": old["execution_id"]})
                task = TASK_DOCS.get(req["task_id"])
                if not task or (req["user"], req["tenant"]) != task[:2]:
                    return self.send_json(403, {"error": "TASK_FORBIDDEN"})
                args = req["arguments"]
                if req['tool']=='query_database':
                    code,result=database_execution(c,req)
                    return self.send_json(code,result)
                c.execute("BEGIN IMMEDIATE")
                if req["tool"] == "read_document" and set(args) == {"document_id"}:
                    doc_id = args["document_id"]
                    doc = DOCS.get(doc_id)
                    if not doc or doc_id not in task[2] or (doc[0], doc[1]) != task[:2]:
                        c.execute("ROLLBACK")
                        return self.send_json(403, {"error": "RESOURCE_FORBIDDEN"})
                    text = (DATA / doc[2]).read_text(encoding="utf-8")
                    result = {"document_id": doc_id, "content": text, "content_hash": hashlib.sha256(text.encode()).hexdigest()}
                elif req["tool"] == "save_summary" and set(args) == {"document_id", "content"}:
                    doc_id, content = args["document_id"], args["content"]
                    doc = DOCS.get(doc_id)
                    if not doc or doc_id not in task[2] or (doc[0], doc[1]) != task[:2] or len(content) > 8000:
                        c.execute("ROLLBACK")
                        return self.send_json(403, {"error": "RESOURCE_FORBIDDEN"})
                    aid, ch = "artifact-" + str(uuid.uuid4()), hashlib.sha256(content.encode()).hexdigest()
                    c.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)", (aid, req["user"], req["tenant"], doc_id, content, ch, time.time()))
                    result = {"artifact_id": aid, "content_hash": ch, "document_id": doc_id}
                elif req["tool"] == "send_report" and set(args) == {"artifact_id", "destination_id"}:
                    if args["destination_id"] != "internal-review-outbox":
                        c.execute("ROLLBACK")
                        return self.send_json(403, {"error": "DESTINATION_FORBIDDEN"})
                    artifact = c.execute("SELECT * FROM artifacts WHERE id=?", (args["artifact_id"],)).fetchone()
                    if not artifact or (artifact["owner"], artifact["tenant"]) != task[:2]:
                        c.execute("ROLLBACK")
                        return self.send_json(403, {"error": "ARTIFACT_FORBIDDEN"})
                    c.execute("INSERT INTO outbox VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), req["execution_id"], artifact["id"], args["destination_id"], artifact["content_hash"], time.time()))
                    result = {"status": "submitted_to_mock_outbox", "artifact_id": artifact["id"], "destination_id": args["destination_id"], "content_hash": artifact["content_hash"]}
                else:
                    c.execute("ROLLBACK")
                    return self.send_json(422, {"error": "TOOL_OR_ARGUMENTS_INVALID"})
                receipt_id = "receipt-" + str(uuid.uuid4())
                c.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (req["execution_id"], req["action_id"], req["request_hash"], receipt_id, json.dumps(result, ensure_ascii=False), time.time()))
                c.execute("COMMIT")
                return self.send_json(200, {"receipt_id": receipt_id, "execution_id": req["execution_id"], "result": result})
            except Exception:
                if c.in_transaction:
                    c.execute("ROLLBACK")
                raise
            finally:
                c.close()
        except HTTPBodyError as error:
            return self.body_error(error)
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "INVALID_JSON"})
        except Exception:
            return self.send_json(500, {"error": "TOOL_FAILURE"})


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOOL_SERVICE_TOKEN must be configured")
    connect().close()
    BoundedHTTPServer(("0.0.0.0", 8001), Handler).serve_forever()
