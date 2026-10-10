"""Durable local service layer for the ReguLens hackathon prototype.

Uses SQLite, a hash-chained audit log, run history, and a small key/value store.
This is production-style local persistence, NOT an enterprise production deployment.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "regulens.db"

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with _connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS app_state (
          state_key TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS assessment_runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          status TEXT NOT NULL, source_hash TEXT, metrics_json TEXT NOT NULL,
          result_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          actor TEXT NOT NULL, action TEXT NOT NULL, entity_type TEXT NOT NULL,
          entity_id TEXT NOT NULL, details_json TEXT NOT NULL,
          previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS service_outbox (
          message_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          channel TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED',
          attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT
        );
        ''')

def save_state(key: str, value: Any):
    init_db()
    payload = json.dumps(value, ensure_ascii=False, default=str)
    with _connect() as con:
        con.execute('''INSERT INTO app_state(state_key,state_json,updated_at) VALUES(?,?,?)
        ON CONFLICT(state_key) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at''',
        (key, payload, now_utc()))

def load_state(key: str, default=None):
    init_db()
    with _connect() as con:
        row = con.execute('SELECT state_json FROM app_state WHERE state_key=?', (key,)).fetchone()
    if not row: return default
    try: return json.loads(row['state_json'])
    except (TypeError, json.JSONDecodeError): return default

def save_run(result: dict, status: str | None = None) -> int:
    init_db()
    payload = json.dumps(result, ensure_ascii=False, default=str)
    metrics = json.dumps(result.get('metrics', {}), ensure_ascii=False, default=str)
    with _connect() as con:
        cur = con.execute('INSERT INTO assessment_runs(created_at,status,source_hash,metrics_json,result_json) VALUES(?,?,?,?,?)',
          (now_utc(), status or result.get('status','UNKNOWN'), result.get('source_hash',''), metrics, payload))
        run_id = int(cur.lastrowid)
    append_audit('system', 'ASSESSMENT_SAVED', 'assessment', str(run_id), {'status': status or result.get('status'), 'source_hash': result.get('source_hash','')})
    return run_id

def update_latest_run(result: dict):
    """Persist post-remediation state as a new versioned run record."""
    return save_run(result, result.get('status','UPDATED'))

def latest_run():
    init_db()
    with _connect() as con:
        row = con.execute('SELECT * FROM assessment_runs ORDER BY run_id DESC LIMIT 1').fetchone()
    if not row: return None
    try:
        obj = json.loads(row['result_json'])
        obj['_persistence'] = {'run_id': row['run_id'], 'created_at': row['created_at']}
        return obj
    except (TypeError, json.JSONDecodeError): return None

def list_runs(limit: int = 50):
    init_db()
    with _connect() as con:
        rows = con.execute('SELECT run_id,created_at,status,source_hash,metrics_json FROM assessment_runs ORDER BY run_id DESC LIMIT ?', (int(limit),)).fetchall()
    result=[]
    for r in rows:
        try: metrics=json.loads(r['metrics_json'])
        except Exception: metrics={}
        result.append({'run_id':r['run_id'],'created_at':r['created_at'],'status':r['status'],'source_hash':r['source_hash'],'metrics':metrics})
    return result

def append_audit(actor: str, action: str, entity_type: str, entity_id: str, details: dict | None = None):
    init_db()
    details_json = json.dumps(details or {}, sort_keys=True, ensure_ascii=False, default=str)
    with _connect() as con:
        last = con.execute('SELECT event_hash FROM audit_events ORDER BY event_id DESC LIMIT 1').fetchone()
        prev = last['event_hash'] if last else 'GENESIS'
        created = now_utc()
        body = '|'.join([created, actor, action, entity_type, str(entity_id), details_json, prev])
        digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
        con.execute('INSERT INTO audit_events(created_at,actor,action,entity_type,entity_id,details_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)',
                    (created, actor, action, entity_type, str(entity_id), details_json, prev, digest))
    return digest

def list_audit(limit: int = 300):
    init_db()
    with _connect() as con:
        rows=con.execute('SELECT * FROM (SELECT * FROM audit_events ORDER BY event_id DESC LIMIT ?) ORDER BY event_id ASC',(int(limit),)).fetchall()
    out=[]
    for r in rows:
        try: details=json.loads(r['details_json'])
        except Exception: details={}
        out.append({'event_id':r['event_id'],'created_at':r['created_at'],'actor':r['actor'],'action':r['action'],'entity_type':r['entity_type'],'entity_id':r['entity_id'],'details':details,'previous_hash':r['previous_hash'],'event_hash':r['event_hash']})
    return out

def verify_audit_chain():
    events=list_audit(100000)
    prev='GENESIS'
    for e in events:
        details_json=json.dumps(e['details'], sort_keys=True, ensure_ascii=False, default=str)
        body='|'.join([e['created_at'],e['actor'],e['action'],e['entity_type'],str(e['entity_id']),details_json,prev])
        digest=hashlib.sha256(body.encode('utf-8')).hexdigest()
        if e['previous_hash'] != prev or e['event_hash'] != digest:
            return {'valid':False,'checked':len(events),'failed_event_id':e['event_id']}
        prev=e['event_hash']
    return {'valid':True,'checked':len(events),'failed_event_id':None}

def enqueue_notification(channel: str, payload: dict):
    """Queue a notification locally; delivery needs a configured external connector."""
    init_db()
    with _connect() as con:
        cur=con.execute('INSERT INTO service_outbox(created_at,channel,payload_json,status) VALUES(?,?,? ,?)',
                        (now_utc(),channel,json.dumps(payload,ensure_ascii=False,default=str),'QUEUED'))
        mid=int(cur.lastrowid)
    append_audit('system','NOTIFICATION_QUEUED','notification',str(mid),{'channel':channel})
    return mid

def list_outbox(limit: int = 100):
    init_db()
    with _connect() as con:
        rows=con.execute('SELECT * FROM service_outbox ORDER BY message_id DESC LIMIT ?', (int(limit),)).fetchall()
    out=[]
    for r in rows:
        try: payload=json.loads(r['payload_json'])
        except Exception: payload={}
        out.append({'message_id':r['message_id'],'created_at':r['created_at'],'channel':r['channel'],'payload':payload,'status':r['status'],'attempts':r['attempts'],'last_error':r['last_error']})
    return out

def service_health():
    init_db()
    with _connect() as con:
        db=con.execute('PRAGMA integrity_check').fetchone()[0]
        tables=[r['name'] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        run_count=con.execute('SELECT COUNT(*) FROM assessment_runs').fetchone()[0]
        audit_count=con.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
        queued=con.execute("SELECT COUNT(*) FROM service_outbox WHERE status='QUEUED'").fetchone()[0]
    return {'database':'SQLite local persistent store','database_integrity':db,'tables':tables,'assessment_runs':run_count,'audit_events':audit_count,'queued_notifications':queued,'database_path':str(DB_PATH),'external_integrations':'NOT CONFIGURED — local demo only'}
