"""SISAJ v0.5 — local-first demonstration for synthetic/pilot data only.
No cloud sync, no external AI, no production security certification.
"""
from __future__ import annotations
import csv, hashlib, hmac, io, json, os, secrets, shutil, sqlite3, time, uuid, re, zipfile
from decimal import Decimal, InvalidOperation
import psycopg
from .storage import Connection as PostgresConnection
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
from fastapi import FastAPI, Depends, File, Header, HTTPException, UploadFile, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv('SISA_DB_PATH', str(ROOT/'data'/'sisa.db')))
BACKUP_DIR = Path(os.getenv('SISA_BACKUP_DIR', str(ROOT/'backups')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', '')
CLOUD = os.getenv('SISA_DEPLOYMENT', 'local') == 'render'
if CLOUD and not DATABASE_URL:
    raise RuntimeError('DATABASE_URL requise sur Render : aucun repli SQLite autorisé.')
if CLOUD and os.getenv('SISA_DATA_MODE', 'synthetic') != 'synthetic':
    raise RuntimeError('Cette version cloud est réservée aux données synthétiques.')
SECURE_COOKIE = os.getenv('SISA_SECURE_COOKIE', '1' if CLOUD else '0') == '1'
SESSION_TTL = 8 * 60 * 60
app = FastAPI(title='SISA — Système intelligent de suivi et d’analyse judiciaire', version='0.5.1', description='MVP local-first. Données synthétiques uniquement jusqu’à validation institutionnelle.')

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','collector','supervisor')), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY, rp_number TEXT NOT NULL, rp_year INTEGER NOT NULL, date_rp TEXT NOT NULL, ri_number TEXT, provenance TEXT NOT NULL, transnational INTEGER NOT NULL CHECK(transnational IN (0,1)), category TEXT NOT NULL, person_physical_count INTEGER, person_legal_count INTEGER, status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted','returned','validated')), return_reason TEXT, version INTEGER NOT NULL DEFAULT 1, source_batch TEXT, created_by INTEGER NOT NULL REFERENCES users(id), updated_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, validated_by INTEGER REFERENCES users(id), validated_at TEXT, UNIQUE(rp_number,rp_year));
CREATE INDEX IF NOT EXISTS idx_cases_date ON cases(date_rp);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE TABLE IF NOT EXISTS case_events(id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL REFERENCES cases(id), event_type TEXT NOT NULL, event_date TEXT, decision_number TEXT, decision_on_merits INTEGER, outcome_conviction INTEGER, outcome_acquittal INTEGER, fine_amount TEXT, seizure_amount TEXT, confiscation_amount TEXT, notes TEXT, created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS import_batches(id TEXT PRIMARY KEY, filename TEXT NOT NULL, row_count INTEGER NOT NULL, imported_count INTEGER NOT NULL, imported_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, source_sheet TEXT);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT, detail_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS import_previews(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), payload TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS login_attempts(id INTEGER PRIMARY KEY, identity_hash TEXT NOT NULL, attempted_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(identity_hash,attempted_at);
CREATE TABLE IF NOT EXISTS indicator_definitions(code TEXT PRIMARY KEY, label TEXT NOT NULL, unit TEXT NOT NULL, date_basis TEXT NOT NULL, method_version TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0);
'''

def utcnow(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
@contextmanager
def db(write=False):
    if DATABASE_URL:
        con = PostgresConnection(DATABASE_URL)
        if not write: con.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
    else:
        con=sqlite3.connect(DB_PATH, timeout=10); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON'); con.execute('PRAGMA journal_mode=WAL')
        con.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
with db() as c:
    c.executescript(SCHEMA)
    c.execute("INSERT OR IGNORE INTO indicator_definitions VALUES ('received_cases','Dossiers reçus','dossier distinct','date RP','draft-v0.2',0)")

def locked_case(c, case_id, expected_version=None):
    row = c.execute('SELECT * FROM cases WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (case_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Dossier introuvable.')
    if expected_version is not None and row['version'] != expected_version:
        raise HTTPException(409, 'Le dossier a été modifié. Rechargez sa version actuelle.')
    return row

def pw_hash(pw: str, salt: Optional[bytes]=None) -> str:
    salt=salt or secrets.token_bytes(16); dk=hashlib.pbkdf2_hmac('sha256',pw.encode(),salt,310000)
    return salt.hex()+':'+dk.hex()
def pw_verify(pw, stored):
    try:
        salt_hex,hash_hex=stored.split(':'); got=hashlib.pbkdf2_hmac('sha256',pw.encode(),bytes.fromhex(salt_hex),310000).hex(); return hmac.compare_digest(got,hash_hex)
    except Exception: return False

def audit(c,user_id,action,entity_type,entity_id=None,detail=None):
    c.execute('INSERT INTO audit_log(user_id,action,entity_type,entity_id,detail_json,created_at) VALUES(?,?,?,?,?,?)',(user_id,action,entity_type,str(entity_id) if entity_id is not None else None,json.dumps(detail or {},ensure_ascii=False,default=str),utcnow()))

def user_from_token(request: Request, authorization: Optional[str]=Header(default=None)):
    if not authorization and request.cookies.get("sisa_session"):
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("X-SISA-CSRF") != "1":
            raise HTTPException(403,"Protection CSRF requise.")
        authorization = "Bearer " + request.cookies["sisa_session"]
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentification requise.')
    token=authorization[7:].strip(); th=hashlib.sha256(token.encode()).hexdigest()
    with db() as c:
        row=c.execute('SELECT u.id,u.username,u.role,u.active,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?',(th,)).fetchone()
    if not row or not row['active'] or row['expires_at']<int(time.time()): raise HTTPException(401,'Session invalide ou expirée.')
    return dict(row)
def require_roles(*roles):
    def dep(u=Depends(user_from_token)):
        if u['role'] not in roles: raise HTTPException(403,'Droits insuffisants.')
        return u
    return dep

class BootstrapIn(BaseModel): username: str=Field(min_length=3,max_length=80); password: str=Field(min_length=14,max_length=200)
class LoginIn(BaseModel): username: str=Field(min_length=1,max_length=80); password: str=Field(min_length=1,max_length=200)
class CaseIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    rp_number: str=Field(min_length=1,max_length=100); rp_year: int=Field(ge=1900,le=2200); date_rp: date; provenance: str=Field(min_length=1,max_length=250); transnational: bool | None; category: str=Field(min_length=1,max_length=250); ri_number: Optional[str]=None; person_physical_count: Optional[int]=Field(default=None,ge=0,le=2147483647); person_legal_count: Optional[int]=Field(default=None,ge=0,le=2147483647)
class ReturnIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str=Field(min_length=5,max_length=1000)
class UserIn(BaseModel): username: str=Field(min_length=3,max_length=80); password: str=Field(min_length=14,max_length=200); role: str

@app.get('/health')
def health(): return {'status':'ok','app':'SISA','version':'0.5.1','mode':'render-synthetic' if CLOUD else 'local-first','cloud_sync':'disabled','external_ai':'disabled'}
@app.post('/auth/bootstrap')
def bootstrap(x: BootstrapIn, x_sisa_bootstrap_key: Optional[str]=Header(default=None)):
    key = os.getenv('SISA_BOOTSTRAP_KEY', '')
    if (CLOUD and not key) or (key and not hmac.compare_digest(x_sisa_bootstrap_key or '', key)):
        raise HTTPException(403,'Clé d’initialisation requise.')
    with db(write=True) as c:
        if DATABASE_URL:
            c.execute('SELECT pg_advisory_xact_lock(731025)')
        if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']:
            raise HTTPException(409,'Initialisation déjà effectuée.')
        c.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',(x.username,pw_hash(x.password),'admin',utcnow()))
        uid=c.execute('SELECT id FROM users WHERE username=?',(x.username,)).fetchone()['id']; audit(c,uid,'bootstrap','user',uid,{'role':'admin'})
    return {'status':'created','username':x.username,'role':'admin','next':'Créer les comptes métier via POST /users.'}
@app.post('/auth/login')
def login(x: LoginIn, request: Request, response: Response):
    identity = hashlib.sha256((x.username.casefold() + '|' + (request.client.host if request.client else 'unknown')).encode()).hexdigest()
    now = int(time.time())
    with db(write=True) as c:
        c.execute('DELETE FROM login_attempts WHERE attempted_at<?', (now-900,))
        attempts = c.execute('SELECT COUNT(*) n FROM login_attempts WHERE identity_hash=?', (identity,)).fetchone()['n']
        if attempts >= 5:
            raise HTTPException(429,'Trop de tentatives. Réessayer dans quinze minutes.')
        c.execute('INSERT INTO login_attempts(identity_hash,attempted_at) VALUES(?,?)', (identity,now))
    with db(write=True) as c:
        u=c.execute('SELECT * FROM users WHERE username=?',(x.username,)).fetchone()
        if not u or not u['active'] or not pw_verify(x.password,u['password_hash']): raise HTTPException(401,'Identifiants incorrects.')
        c.execute('DELETE FROM login_attempts WHERE identity_hash=?', (identity,))
        token=secrets.token_urlsafe(40); expires=int(time.time())+SESSION_TTL
        c.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],expires)); audit(c,u['id'],'login','session',None,{})
    response.set_cookie('sisa_session', token, httponly=True, secure=SECURE_COOKIE, samesite='strict', max_age=SESSION_TTL, path='/')
    return {'access_token':token,'token_type':'bearer','expires_in':SESSION_TTL,'role':u['role']}
@app.get('/auth/me')
def me(u=Depends(user_from_token)): return {'id':u['id'],'username':u['username'],'role':u['role']}
@app.post('/auth/logout')
def logout(request: Request, response: Response, u=Depends(user_from_token), authorization: Optional[str]=Header(default=None)):
    token = authorization[7:].strip() if authorization else request.cookies.get('sisa_session', '')
    th=hashlib.sha256(token.encode()).hexdigest()
    with db(write=True) as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(th,)); audit(c,u['id'],'logout','session',None,{})
    response.delete_cookie('sisa_session', path='/')
    return {'status':'logged_out'}
@app.post('/users')
def create_user(x: UserIn,u=Depends(require_roles('admin'))):
    if x.role not in ('collector','supervisor'): raise HTTPException(422,'Rôle autorisé : collector ou supervisor. Le rôle admin est créé séparément.')
    try:
        with db(write=True) as c:
            cur=c.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',(x.username,pw_hash(x.password),x.role,utcnow())); audit(c,u['id'],'create','user',cur.lastrowid,{'username':x.username,'role':x.role})
    except (sqlite3.IntegrityError, psycopg.IntegrityError) as e: raise HTTPException(409,'Nom d’utilisateur déjà utilisé.') from e
    return {'status':'created','username':x.username,'role':x.role}
@app.get('/users')
def list_users(u=Depends(require_roles('admin','supervisor'))):
    with db() as c: rows=c.execute('SELECT id,username,role,active,created_at FROM users ORDER BY id').fetchall()
    return {'items':[dict(r) for r in rows]}

def normalize_case(x: CaseIn):
    if x.date_rp.year!=x.rp_year: raise HTTPException(422,'L’année de la date RP doit correspondre à rp_year.')
    return (x.rp_number.strip(),x.rp_year,x.date_rp.isoformat(),x.ri_number,x.provenance.strip(),int(bool(x.transnational)),x.category.strip(),x.person_physical_count,x.person_legal_count)
@app.post('/cases')
def create_case(x: CaseIn,u=Depends(require_roles('admin','collector','supervisor'))):
    values=normalize_case(x); now=utcnow()
    try:
        with db(write=True) as c:
            if DATABASE_URL:c.execute('SELECT pg_advisory_xact_lock(731026)')
            if c.execute('SELECT id FROM cases WHERE LOWER(rp_number)=? AND rp_year=?',(x.rp_number.lower(),x.rp_year)).fetchone():raise HTTPException(409,'Dossier déjà présent pour ce RP et cette année.')
            cur=c.execute('''INSERT INTO cases(rp_number,rp_year,date_rp,ri_number,provenance,transnational,category,person_physical_count,person_legal_count,created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(*values,u['id'],u['id'],now,now)); cid=cur.lastrowid
            if x.transnational is None:
                from .registry_models import Register
                c.execute('INSERT INTO registry_records VALUES (?,?,?)',(cid,Register(transnational_state='undetermined',ri_state='assigned' if x.ri_number else 'not_recorded').model_dump_json(),now))
            audit(c,u['id'],'create','case',cid,{'rp_number':x.rp_number,'rp_year':x.rp_year})
    except (sqlite3.IntegrityError, psycopg.IntegrityError) as e: raise HTTPException(409,'Dossier déjà existant pour ce numéro RP et cette année.') from e
    return {'id':cid,'status':'draft','version':1}
@app.get('/cases')
def list_cases(q: str|None=None, year: int|None=None, start: date|None=None, end: date|None=None, category: str|None=None, status: str|None=None, limit: int=100, offset: int=0,u=Depends(user_from_token)):
    if limit<1 or limit>500 or offset<0: raise HTTPException(422,'Pagination invalide.')
    if start and end and start>end: raise HTTPException(422,'Période invalide.')
    where=[]; args=[]
    if start: where.append('date_rp>=?'); args.append(start.isoformat())
    if end: where.append('date_rp<=?'); args.append(end.isoformat())
    if category: where.append('category=?'); args.append(category)
    if q: where.append('(rp_number LIKE ? OR ri_number LIKE ? OR provenance LIKE ? OR category LIKE ?)'); args += [f'%{q}%']*4
    if year is not None: where.append('rp_year=?'); args.append(year)
    if status:
        if status not in ('draft','submitted','returned','validated'): raise HTTPException(422,'Statut invalide.')
        where.append('status=?'); args.append(status)
    sql='SELECT id,rp_number,rp_year,date_rp,ri_number,provenance,transnational,category,person_physical_count,person_legal_count,status,version,created_at,updated_at FROM cases'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY date_rp DESC,id DESC LIMIT ? OFFSET ?'; args += [limit,offset]
    with db() as c: rows=c.execute(sql,args).fetchall(); total=c.execute('SELECT COUNT(*) n FROM cases'+(' WHERE '+' AND '.join(where) if where else ''),args[:-2]).fetchone()['n']
    return {'total':total,'limit':limit,'offset':offset,'items':[dict(r) for r in rows]}
@app.get('/cases/{case_id}')
def get_case(case_id:int,u=Depends(user_from_token)):
    with db() as c:
        row=c.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone()
        if not row: raise HTTPException(404,'Dossier introuvable.')
        events=c.execute('SELECT * FROM case_events WHERE case_id=? ORDER BY event_date,id',(case_id,)).fetchall()
        reg=c.execute('SELECT payload FROM registry_records WHERE case_id=?',(case_id,)).fetchone()
    d=dict(row)
    if reg:
        state=json.loads(reg['payload'])['transnational_state'];d['transnational_state']=state;d['transnational']=True if state=='yes' else False if state=='no' else None;d['register_complete']=True
    d.pop('created_by',None); d.pop('updated_by',None); d['events']=[dict(e) for e in events]; return d
@app.patch('/cases/{case_id}')
def update_case(case_id:int,x:CaseIn,reason:str,expected_version:int|None=None,u=Depends(require_roles('admin','collector','supervisor'))):
    if len(reason.strip())<5: raise HTTPException(422,'Motif de correction obligatoire (5 caractères minimum).')
    vals=normalize_case(x); now=utcnow()
    with db(write=True) as c:
        old=c.execute('SELECT * FROM cases WHERE id=?'+(' FOR UPDATE' if DATABASE_URL else ''),(case_id,)).fetchone()
        if not old: raise HTTPException(404,'Dossier introuvable.')
        if expected_version is not None and old['version'] != expected_version: raise HTTPException(409,'Le dossier a été modifié. Rechargez sa version actuelle.')
        from .registry_models import Register,validate_dates
        extra=c.execute('SELECT payload FROM registry_records WHERE case_id=?',(case_id,)).fetchone()
        if extra:
            vals=list(vals);vals[6]=int(Register.model_validate_json(extra['payload']).transnational_state=='yes')
            try: validate_dates(Register.model_validate_json(extra['payload']),x.date_rp)
            except ValueError as e: raise HTTPException(422,str(e))
        if old['status']=='validated' and u['role']!='supervisor' and u['role']!='admin': raise HTTPException(403,'Seul le superviseur peut corriger un dossier validé.')
        for table,column in (('case_decisions','decision_date'),('case_measures','measure_date')):
            if c.execute('SELECT 1 FROM '+table+' WHERE case_id=? AND '+column+'<?',(case_id,x.date_rp.isoformat())).fetchone():
                raise HTTPException(422,'La nouvelle date RP serait postérieure à une décision ou mesure existante.')
        if not extra and x.transnational is None:
            from .registry import read_record
            initial=read_record(c,dict(old));initial.transnational_state='undetermined'
            c.execute('INSERT INTO registry_records VALUES (?,?,?)',(case_id,initial.model_dump_json(),now))
        c.execute('UPDATE cases SET rp_number=?,rp_year=?,date_rp=?,ri_number=?,provenance=?,transnational=?,category=?,person_physical_count=?,person_legal_count=?,status=?,return_reason=NULL,version=version+1,updated_by=?,updated_at=?,validated_by=NULL,validated_at=NULL WHERE id=?',(*vals,'draft',u['id'],now,case_id))
        audit(c,u['id'],'correct','case',case_id,{'reason':reason,'before':dict(old),'after':dict(c.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone())})
    return {'id':case_id,'status':'draft','version':old['version']+1,'message':'Correction historisée; dossier remis en brouillon.'}
@app.post('/cases/{case_id}/submit')
def submit_case(case_id:int,expected_version:int|None=None,u=Depends(require_roles('admin','collector','supervisor'))):
    with db(write=True) as c:
        row=locked_case(c,case_id,expected_version)
        if not row: raise HTTPException(404,'Dossier introuvable.')
        if row['status'] not in ('draft','returned'): raise HTTPException(409,'Seuls les brouillons ou dossiers retournés peuvent être soumis.')
        from .registry import ready_for_submission
        ready_for_submission(c,case_id)
        c.execute("UPDATE cases SET status='submitted',return_reason=NULL,version=version+1,updated_by=?,updated_at=? WHERE id=?",(u['id'],utcnow(),case_id)); audit(c,u['id'],'submit','case',case_id,{})
    return {'id':case_id,'status':'submitted','version':row['version']+1}
@app.post('/cases/{case_id}/validate')
def validate_case(case_id:int,expected_version:int|None=None,u=Depends(require_roles('admin','supervisor'))):
    with db(write=True) as c:
        row=locked_case(c,case_id,expected_version)
        if not row: raise HTTPException(404,'Dossier introuvable.')
        if row['status']!='submitted': raise HTTPException(409,'Le dossier doit être soumis avant validation.')
        from .registry import ready_for_submission
        ready_for_submission(c,case_id)
        c.execute("UPDATE cases SET status='validated',version=version+1,validated_by=?,validated_at=?,updated_by=?,updated_at=? WHERE id=?",(u['id'],utcnow(),u['id'],utcnow(),case_id)); audit(c,u['id'],'validate','case',case_id,{})
    return {'id':case_id,'status':'validated','version':row['version']+1}
@app.post('/cases/{case_id}/return')
def return_case(case_id:int,x:ReturnIn,expected_version:int|None=None,u=Depends(require_roles('admin','supervisor'))):
    with db(write=True) as c:
        row=locked_case(c,case_id,expected_version)
        if not row: raise HTTPException(404,'Dossier introuvable.')
        if row['status']!='submitted': raise HTTPException(409,'Seul un dossier soumis peut être retourné.')
        c.execute("UPDATE cases SET status='returned',return_reason=?,version=version+1,updated_by=?,updated_at=? WHERE id=?",(x.reason,u['id'],utcnow(),case_id)); audit(c,u['id'],'return','case',case_id,{'reason':x.reason})
    return {'id':case_id,'status':'returned','reason':x.reason,'version':row['version']+1}

@app.post('/cases/{case_id}/events')
def add_event(case_id:int, event_type:str, event_date:date|None=None, decision_number:str|None=None, decision_on_merits:bool|None=None, outcome_conviction:bool|None=None, outcome_acquittal:bool|None=None, fine_amount:str|None=None, seizure_amount:str|None=None, confiscation_amount:str|None=None, notes:str|None=None,expected_version:int|None=None,u=Depends(require_roles('admin','collector','supervisor'))):
    for val in (fine_amount,seizure_amount,confiscation_amount):
        if val is not None:
            try:
                amount = Decimal(val)
                if not amount.is_finite() or amount < 0: raise ValueError
            except (ValueError, InvalidOperation): raise HTTPException(422,'Les montants doivent être numériques et positifs ou nuls.')
    with db(write=True) as c:
        case=locked_case(c,case_id,expected_version)
        if not case: raise HTTPException(404,'Dossier introuvable.')
        if case['status']=='validated': raise HTTPException(409,'Corriger le dossier avec un motif pour le remettre en brouillon avant d’ajouter un événement.')
        cur=c.execute('INSERT INTO case_events(case_id,event_type,event_date,decision_number,decision_on_merits,outcome_conviction,outcome_acquittal,fine_amount,seizure_amount,confiscation_amount,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(case_id,event_type,event_date.isoformat() if event_date else None,decision_number,None if decision_on_merits is None else int(decision_on_merits),None if outcome_conviction is None else int(outcome_conviction),None if outcome_acquittal is None else int(outcome_acquittal),fine_amount,seizure_amount,confiscation_amount,notes,u['id'],utcnow())); audit(c,u['id'],'create','case_event',cur.lastrowid,{'case_id':case_id,'event_type':event_type})
        c.execute('UPDATE cases SET version=version+1,updated_by=?,updated_at=? WHERE id=?',(u['id'],utcnow(),case_id))
    return {'event_id':cur.lastrowid,'case_id':case_id,'version':case['version']+1}

@app.get('/stats')
def stats(start:date|None=None,end:date|None=None,jurisdiction:str|None=None,u=Depends(user_from_token)):
    if start and end and start>end: raise HTTPException(422,'La date de début doit précéder la date de fin.')
    clauses=["status='validated'"]; args=[]
    if start: clauses.append('date_rp>=?'); args.append(start.isoformat())
    if end: clauses.append('date_rp<=?'); args.append(end.isoformat())
    if jurisdiction: clauses.append('EXISTS (SELECT 1 FROM case_profiles p WHERE p.case_id=cases.id AND p.jurisdiction_code=?)'); args.append(jurisdiction)
    wh=' WHERE '+' AND '.join(clauses)
    with db() as c:
        total=c.execute('SELECT COUNT(*) n FROM cases'+wh,args).fetchone()['n']; trans=c.execute('SELECT COUNT(*) n FROM cases'+wh+' AND transnational=1',args).fetchone()['n']
        bycat=c.execute('SELECT category,COUNT(*) n FROM cases'+wh+' GROUP BY category ORDER BY category',args).fetchall()
        byyear=c.execute('SELECT rp_year,COUNT(*) n FROM cases'+wh+' GROUP BY rp_year ORDER BY rp_year',args).fetchall()
    return {'period':{'start':start.isoformat() if start else None,'end':end.isoformat() if end else None},'unit':'dossier distinct','population':'dossiers validés seulement','method_version':'draft-v0.2-not-approved','received_cases':total,'transnational_cases':trans,'by_category':[dict(r) for r in bycat],'by_year':[{'year':r['rp_year'],'count':r['n']} for r in byyear],'warning':'Indicateurs provisoires. Règles officielles PPEF à faire approuver; ne pas transmettre comme statistiques officielles.'}
@app.get('/intelligence/anomalies')
def anomalies(u=Depends(require_roles('admin','supervisor'))):
    """Explainable local rules, not an ML model. Only approved records are considered."""
    issues=[]
    with db() as c: rows=c.execute("SELECT id,rp_number,rp_year,date_rp,person_physical_count,person_legal_count,status FROM cases WHERE status IN ('submitted','validated') ORDER BY id").fetchall()
    for r in rows:
        if int(r['date_rp'][:4])!=r['rp_year']: issues.append({'case_id':r['id'],'code':'YEAR_DATE_MISMATCH','severity':'high','explanation':'L’année de la date RP diffère de l’année enregistrée.'})
        if r['person_physical_count'] is not None and r['person_physical_count']<0: issues.append({'case_id':r['id'],'code':'NEGATIVE_PHYSICAL_COUNT','severity':'high','explanation':'Effectif physique négatif.'})
        if r['person_legal_count'] is not None and r['person_legal_count']<0: issues.append({'case_id':r['id'],'code':'NEGATIVE_LEGAL_COUNT','severity':'high','explanation':'Effectif personne morale négatif.'})
    return {'engine':'local-explainable-rules-v0.2','is_machine_learning':False,'count':len(issues),'items':issues}

# Import standard template OR source PPEF workbook (sheet AUDIENCES PENALES, row 3 headers).
CORE_HEADERS={'rp_number':'N° RP','date_rp':'Date RP','provenance':'Unité (OPJ) de Provenance','transnational':'Dossier à caractère transnational (oui/non)','category':'Infraction retenue par le Parquet','ri_number':'N° RI','person_physical_count':'Nombre prévenus (PP)','person_legal_count':'Nombre prévenus (PM)'}
def parse_bool(v):
    if isinstance(v,bool): return int(v)
    s=str(v or '').strip().casefold()
    if s in ('oui','o','yes','y','1','true','vrai'): return 1
    if s in ('non','n','no','0','false','faux'): return 0
    return None
def parse_date(v):
    if isinstance(v,datetime): return v.date().isoformat()
    if isinstance(v,date): return v.isoformat()
    if v is None or not str(v).strip(): return None
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%Y/%m/%d'):
        try: return datetime.strptime(str(v).strip(),fmt).date().isoformat()
        except ValueError: pass
    return None
def read_rows(filename, content):
    if Path(filename).suffix.lower()=='.csv':
        try: return list(csv.DictReader(io.StringIO(content.decode('utf-8-sig')))), None
        except Exception as e: raise HTTPException(400,'CSV illisible; UTF-8 attendu.') from e
    if Path(filename).suffix.lower()!='.xlsx': raise HTTPException(415,'Formats acceptés : CSV et XLSX.')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 60*1024*1024:
                raise HTTPException(413,'XLSX décompressé trop volumineux.')
    except zipfile.BadZipFile as e:
        raise HTTPException(400,'XLSX illisible.') from e
    try: wb=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    except Exception as e: raise HTTPException(400,'XLSX illisible.') from e
    # canonical template: first row headers; original PPEF: row 3 headers on AUDIENCES PENALES
    if 'AUDIENCES PENALES' in wb.sheetnames:
        ws=wb['AUDIENCES PENALES']; header_row=3; source='AUDIENCES PENALES'
    else: ws=wb.active; header_row=1; source=ws.title
    if (ws.max_column or 0)>256 or (ws.max_row or 0)>10003:
        wb.close()
        raise HTTPException(413,'XLSX limité à 256 colonnes et 10 000 lignes de données.')
    headers=[str(v).strip() if v is not None else '' for v in next(ws.iter_rows(min_row=header_row,max_row=header_row,values_only=True))]
    rows=[]
    for vals in ws.iter_rows(min_row=header_row+1,values_only=True):
        if not any(v is not None and str(v).strip() for v in vals): continue
        if len(rows) >= 10000:
            wb.close()
            raise HTTPException(413,'Maximum 10 000 lignes par import.')
        rows.append({headers[i]: vals[i] if i<len(vals) and headers[i] else None for i in range(len(headers)) if headers[i]})
    wb.close(); return rows, source
def parse_integer(value):
    number = Decimal(str(value).strip())
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError('Entier requis')
    return int(number)

def map_import(raw):
    # canonical headers take precedence, otherwise map source PPEF headings
    if 'rp_number' in raw: d={k:raw.get(k) for k in ('rp_number','rp_year','date_rp','provenance','transnational','category','ri_number','person_physical_count','person_legal_count')}; d['rp_year']=d.get('rp_year') or (parse_date(d.get('date_rp')) or '')[:4]
    else:
        d={k:raw.get(v) for k,v in CORE_HEADERS.items()}; d['rp_year']=(parse_date(d.get('date_rp')) or '')[:4]
    d['rp_number']=str(d.get('rp_number') or '').strip(); d['provenance']=str(d.get('provenance') or '').strip(); d['category']=str(d.get('category') or '').strip(); d['ri_number']=str(d.get('ri_number') or '').strip() or None
    d['date_rp']=parse_date(d.get('date_rp')); d['transnational']=parse_bool(d.get('transnational'))
    try: d['rp_year']=parse_integer(d.get('rp_year'))
    except Exception: d['rp_year']=None
    for key in ('person_physical_count','person_legal_count'):
        try: d[key]=None if d.get(key) in (None,'') else parse_integer(d[key])
        except Exception: d[key]='INVALID'
    return d
def validate_import(rows):
    if not rows: raise HTTPException(400,'Aucune ligne exploitable.')
    allowed=set(CORE_HEADERS.values())|{'rp_number','rp_year','date_rp','provenance','transnational','category','ri_number','person_physical_count','person_legal_count'}
    if any(str(v).strip() for row in rows for k,v in row.items() if k not in allowed and v is not None):
        raise HTTPException(422,'Colonnes métier supplémentaires : utiliser la reprise PPEF complète pour éviter toute perte de données.')
    good=[]; errors=[]; seen=set()
    for idx,raw in enumerate(rows, start=1):
        d=map_import(raw); e=[]
        for k in ('rp_number','date_rp','provenance','category'):
            if not d.get(k): e.append(f'{k} obligatoire ou invalide')
        if d['rp_year'] is None or not 1900<=d['rp_year']<=2200: e.append('rp_year invalide')
        if d['date_rp'] and d['rp_year'] and int(d['date_rp'][:4])!=d['rp_year']: e.append('année de date_rp différente de rp_year')
        if d['transnational'] is None: e.append('transnational doit être Oui/Non')
        for k in ('person_physical_count','person_legal_count'):
            if d[k]=='INVALID' or (d[k] is not None and d[k]<0): e.append(f'{k} doit être un entier positif ou inconnu')
        key=(d['rp_number'].casefold(),d['rp_year']) if d['rp_number'] and d['rp_year'] else None
        if key and key in seen: e.append('doublon dans le fichier (RP + année)')
        if key: seen.add(key)
        try:
            CaseIn(**{**d, 'transnational': bool(d['transnational'])})
        except Exception:
            e.append('format ou longueur de champ invalide')
        if e: errors.append({'row':idx,'rp_number':d['rp_number'],'errors':e})
        else: good.append(d)
    with db() as c:
        for d in good:
            exists=c.execute('SELECT id FROM cases WHERE rp_number=? AND rp_year=?',(d['rp_number'],d['rp_year'])).fetchone()
            if exists: errors.append({'row':None,'rp_number':d['rp_number'],'errors':['dossier déjà présent en base']})
    return good,errors
@app.post('/imports/preview')
async def import_preview(file: UploadFile=File(...),u=Depends(require_roles('admin','collector','supervisor'))):
    content=await file.read(15*1024*1024+1)
    if len(content)>15*1024*1024: raise HTTPException(413,'Limite prototype : 15 Mo.')
    rows,source=read_rows(file.filename or 'upload.csv',content); good,errors=validate_import(rows)
    # preview stored on server as expiring JSON file, not in public cloud
    pid=secrets.token_urlsafe(18); payload={'user_id':u['id'],'filename':file.filename,'source':source,'created':time.time(),'rows':good if not errors else []}
    if DATABASE_URL:
        with db() as c:
            c.execute('DELETE FROM import_previews WHERE created_at<?', (int(time.time())-1800,))
            c.execute('INSERT INTO import_previews VALUES(?,?,?,?)', (pid,u['id'],json.dumps(payload,ensure_ascii=False,default=str),int(time.time())))
    else:
        (DB_PATH.parent/f'preview_{pid}.json').write_text(json.dumps(payload,ensure_ascii=False,default=str),encoding='utf-8')
    return {'preview_id':pid,'source_sheet':source,'total_rows':len(rows),'valid_rows':len(good),'error_count':len(errors),'errors':errors[:200],'can_confirm':bool(good) and not errors,'sample':good[:5],'message':'Aucune écriture avant confirmation.'}
@app.post('/imports/{preview_id}/confirm')
def import_confirm(preview_id:str,u=Depends(require_roles('admin','collector','supervisor'))):
    if not re.fullmatch(r'[A-Za-z0-9_-]{24}', preview_id):
        raise HTTPException(404,'Aperçu introuvable.')
    if DATABASE_URL:
        return confirm_postgres_preview(preview_id, u)
    p=DB_PATH.parent/f'preview_{preview_id}.json'
    if not p.exists(): raise HTTPException(404,'Aperçu absent, expiré ou déjà utilisé.')
    payload=json.loads(p.read_text(encoding='utf-8'))
    # Authorization must precede cleanup: a denied caller cannot delete an owner's work.
    if payload['user_id']!=u['id']:
        raise HTTPException(403,'Aperçu expiré ou créé par un autre utilisateur.')
    if time.time()-payload['created']>1800:
        p.unlink(missing_ok=True)
        raise HTTPException(403,'Aperçu expiré ou créé par un autre utilisateur.')
    rows=payload['rows']
    if not rows: raise HTTPException(422,'Import bloqué : erreurs à corriger.')
    bid=str(uuid.uuid4()); now=utcnow()
    try:
        with db(write=True) as c:
            for d in rows:
                c.execute("INSERT INTO cases(rp_number,rp_year,date_rp,ri_number,provenance,transnational,category,person_physical_count,person_legal_count,source_batch,created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(d['rp_number'],d['rp_year'],d['date_rp'],d['ri_number'],d['provenance'],d['transnational'],d['category'],None if d['person_physical_count']=='INVALID' else d['person_physical_count'],None if d['person_legal_count']=='INVALID' else d['person_legal_count'],bid,u['id'],u['id'],now,now))
            c.execute('INSERT INTO import_batches VALUES(?,?,?,?,?,?,?)',(bid,payload['filename'],len(rows),len(rows),u['id'],now,payload['source'])); audit(c,u['id'],'import','batch',bid,{'rows':len(rows),'source':payload['source']})
    except (sqlite3.IntegrityError, psycopg.IntegrityError) as e: raise HTTPException(409,'Conflit d’unicité : aucune ligne du lot ne doit être considérée comme importée.') from e
    p.unlink(missing_ok=True)
    return {'status':'imported','batch_id':bid,'imported_rows':len(rows),'note':'Dossiers créés en brouillon; soumission et validation restent requises.'}
@app.get('/exports/cases.csv')
def export_cases(u=Depends(require_roles('admin','supervisor'))):
    with db() as c: rows=c.execute('SELECT rp_number,rp_year,date_rp,ri_number,provenance,transnational,category,person_physical_count,person_legal_count,status,version,created_at,updated_at FROM cases ORDER BY rp_year,rp_number').fetchall(); audit(c,u['id'],'export','cases',None,{'format':'csv','rows':len(rows)})
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(rows[0].keys() if rows else ['rp_number','rp_year','date_rp','ri_number','provenance','transnational','category','person_physical_count','person_legal_count','status','version','created_at','updated_at']); writer.writerows([[safe_spreadsheet_cell(v) for v in dict(r).values()] for r in rows]); data=('\ufeff'+out.getvalue()).encode('utf-8')
    return StreamingResponse(io.BytesIO(data),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="sisa_export_cases.csv"'})
@app.get('/audit')
def get_audit(limit:int=100,u=Depends(require_roles('admin','supervisor'))):
    if limit<1 or limit>500: raise HTTPException(422,'limit entre 1 et 500')
    with db() as c: rows=c.execute('SELECT a.id,u.username,a.action,a.entity_type,a.entity_id,a.detail_json,a.created_at FROM audit_log a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT ?',(limit,)).fetchall()
    return {'items':[dict(r) for r in rows]}
@app.post('/admin/backup')
def backup(u=Depends(require_roles('admin'))):
    if DATABASE_URL:
        raise HTTPException(409,'PostgreSQL : utiliser les sauvegardes Render et la procédure de restauration documentée.')
    target=BACKUP_DIR/f'sisa_backup_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.db'
    with db() as src, sqlite3.connect(target) as dst: src.backup(dst)
    digest=hashlib.sha256(target.read_bytes()).hexdigest(); audit_id=None
    with db() as c: audit(c,u['id'],'backup','database',target.name,{'sha256':digest,'bytes':target.stat().st_size})
    return {'status':'created','file':target.name,'bytes':target.stat().st_size,'sha256':digest,'warning':'Copie locale non chiffrée. Déplacer vers un support chiffré et tester la restauration avant production.'}
@app.get('/', include_in_schema=False)
def home():
    return FileResponse(ROOT/'app'/'static'/'index.html')

app.mount('/static', StaticFiles(directory=ROOT/'app'/'static'), name='static')

# Platform endpoints: retain the v0.2 API and expose a browser-oriented layer.
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from urllib.parse import urlsplit

allowed_hosts = ['localhost', '127.0.0.1', 'testserver']
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    allowed_hosts.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
allowed_hosts.extend(filter(None, os.getenv('SISA_ALLOWED_HOSTS', '').split(',')))
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin and urlsplit(origin).netloc != request.headers.get('host'):
        return JSONResponse({'detail':'Origine non autorisée.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    if request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if CLOUD:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

async def integrity_error_handler(request, exc):
    return JSONResponse({'detail':'Conflit avec une donnée existante. Aucune modification enregistrée.'}, status_code=409)

app.add_exception_handler(sqlite3.IntegrityError, integrity_error_handler)
app.add_exception_handler(psycopg.IntegrityError, integrity_error_handler)


def safe_spreadsheet_cell(value):
    if isinstance(value, str) and (value.startswith(('\t','\r','\n')) or value.lstrip().startswith(('=', '+', '-', '@'))):
        return "'" + value
    return value


def confirm_postgres_preview(pid, user):
    with db(write=True) as c:
        row = c.execute('SELECT * FROM import_previews WHERE id=? FOR UPDATE', (pid,)).fetchone()
        if not row:
            raise HTTPException(404,'Aperçu absent, expiré ou déjà utilisé.')
        if row['user_id'] != user['id']:
            raise HTTPException(403,'Cet aperçu appartient à un autre utilisateur.')
        if time.time()-row['created_at']>1800:
            raise HTTPException(403,'Aperçu expiré.')
        payload = json.loads(row['payload'])
        if not payload['rows']:
            raise HTTPException(422,'Import bloqué : erreurs à corriger.')
        bid = str(uuid.uuid4()); now = utcnow()
        for d in payload['rows']:
            c.execute('''INSERT INTO cases(rp_number,rp_year,date_rp,ri_number,provenance,transnational,category,
              person_physical_count,person_legal_count,source_batch,created_by,updated_by,created_at,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (d['rp_number'],d['rp_year'],d['date_rp'],d['ri_number'],d['provenance'],d['transnational'],d['category'],
               d['person_physical_count'],d['person_legal_count'],bid,user['id'],user['id'],now,now))
        c.execute('INSERT INTO import_batches VALUES(?,?,?,?,?,?,?)',
                  (bid,payload['filename'],len(payload['rows']),len(payload['rows']),user['id'],now,payload['source']))
        audit(c,user['id'],'import','batch',bid,{'rows':len(payload['rows']),'source':payload['source']})
        c.execute('DELETE FROM import_previews WHERE id=?', (pid,))
    return {'status':'imported','batch_id':bid,'imported_rows':len(payload['rows'])}

@app.get('/ready')
def ready():
    try:
        with db() as c: c.execute('SELECT COUNT(*) n FROM users').fetchone()
    except Exception as exc:
        raise HTTPException(503,'Stockage indisponible.') from exc
    return {'status':'ready','storage':'postgresql' if DATABASE_URL else 'sqlite','data_mode':'synthetic'}

@app.get('/platform/config')
def platform_config():
    with db() as c: count = c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
    return {'initialized':bool(count),'version':'0.5.1','deployment':'Render' if CLOUD else 'Local',
            'data_mode':'synthetic','bootstrap_key_required':bool(os.getenv('SISA_BOOTSTRAP_KEY')) or CLOUD,
            'official_indicators':False,'external_ai':False,'public_publication':False}

@app.get('/dashboard')
def dashboard(u=Depends(user_from_token)):
    with db() as c:
        counts = c.execute('SELECT status,COUNT(*) n FROM cases GROUP BY status').fetchall()
        recent = c.execute('SELECT id,rp_number,ri_number,date_rp,category,status,updated_at FROM cases ORDER BY updated_at DESC,id DESC LIMIT 6').fetchall()
    result = {k:0 for k in ('draft','submitted','returned','validated')}
    result.update({r['status']:r['n'] for r in counts})
    return {'counts':result,'total':sum(result.values()),'recent':[dict(r) for r in recent],
            'statistics':stats(u=u)}

@app.get('/imports')
def import_history(u=Depends(user_from_token)):
    with db() as c:
        rows = c.execute('SELECT b.*,u.username FROM import_batches b JOIN users u ON u.id=b.imported_by ORDER BY b.created_at DESC LIMIT 100').fetchall()
    return {'items':[dict(r) for r in rows]}

class UserUpdate(BaseModel):
    active: bool

@app.patch('/users/{user_id}')
def set_user_active(user_id: int, x: UserUpdate, u=Depends(require_roles('admin'))):
    if user_id == u['id']: raise HTTPException(409,'Vous ne pouvez pas désactiver votre propre compte.')
    with db(write=True) as c:
        target = c.execute('SELECT id,role FROM users WHERE id=?',(user_id,)).fetchone()
        if not target: raise HTTPException(404,'Utilisateur introuvable.')
        if target['role']=='admin': raise HTTPException(403,'Compte administrateur protégé.')
        c.execute('UPDATE users SET active=? WHERE id=?',(int(x.active),user_id))
        if not x.active: c.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
        audit(c,u['id'],'activate' if x.active else 'deactivate','user',user_id)
    return {'id':user_id,'active':x.active}

class PasswordChange(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=14,max_length=200)

@app.post('/auth/password')
def change_password(x: PasswordChange, response: Response, u=Depends(user_from_token)):
    with db(write=True) as c:
        row=c.execute('SELECT password_hash FROM users WHERE id=?',(u['id'],)).fetchone()
        if not pw_verify(x.current_password,row['password_hash']): raise HTTPException(403,'Mot de passe actuel incorrect.')
        c.execute('UPDATE users SET password_hash=? WHERE id=?',(pw_hash(x.new_password),u['id']))
        c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
        audit(c,u['id'],'password_change','user',u['id'])
    response.delete_cookie('sisa_session',path='/')
    return {'status':'changed','message':'Toutes vos sessions ont été révoquées. Reconnectez-vous.'}

class EventIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    expected_version: int | None = Field(default=None,ge=1)
    event_type: str = Field(min_length=1,max_length=80)
    event_date: date | None = None
    decision_number: str | None = Field(default=None,max_length=100)
    fine_amount: str | None = Field(default=None,max_length=60)
    seizure_amount: str | None = Field(default=None,max_length=60)
    confiscation_amount: str | None = Field(default=None,max_length=60)
    notes: str | None = Field(default=None,max_length=2000)

@app.post('/cases/{case_id}/timeline')
def create_timeline_event(case_id:int, x:EventIn, u=Depends(require_roles('admin','collector','supervisor'))):
    return add_event(case_id,**x.model_dump(),u=u)

@app.get('/exports/cases.xlsx')
def export_xlsx(u=Depends(require_roles('admin','supervisor'))):
    from openpyxl import Workbook
    with db() as c:
        rows=c.execute('SELECT rp_number,rp_year,date_rp,ri_number,provenance,category,transnational,person_physical_count,person_legal_count,status,version FROM cases ORDER BY rp_year,rp_number').fetchall()
        audit(c,u['id'],'export','cases',detail={'format':'xlsx','rows':len(rows)})
    wb=Workbook(); ws=wb.active; ws.title='Dossiers'
    fields=['rp_number','rp_year','date_rp','ri_number','provenance','category','transnational','person_physical_count','person_legal_count','status','version']
    ws.append(fields)
    for row in rows: ws.append([safe_spreadsheet_cell(row[k]) for k in fields])
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
    meta=wb.create_sheet('Méthode'); meta.append(['SISA','Export de dossiers — tous statuts'])
    for pair in [('Auteur',u['username']),('Date UTC',utcnow()),('Version','0.5.1'),('Méthode','Provisoire, non officielle'),('Données','Synthétiques uniquement')]: meta.append(pair)
    buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="sisa_dossiers.xlsx"'})

@app.get('/reports/summary.pdf')
def report_pdf(start:date|None=None,end:date|None=None,jurisdiction:str|None=None,u=Depends(require_roles('admin','supervisor'))):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    result=stats(start=start,end=end,jurisdiction=jurisdiction,u=u)
    buf=io.BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4)
    pdf.setTitle('SISA - Rapport statistique provisoire')
    y=790
    lines=['SISA / PPEF','Rapport statistique provisoire - donnees synthetiques',
           f"Periode : {start or 'toutes dates'} au {end or 'toutes dates'}",
           f"Auteur : {u['username']} | UTC : {utcnow()}",'Version : 0.5.1 | Methode : draft-v0.2-not-approved',
           f"Juridiction : {jurisdiction or 'Toutes'}",'Population : dossiers valides uniquement',f"Dossiers recus : {result['received_cases']}",
           f"Dossiers transnationaux : {result['transnational_cases']}",'Ventilation par categorie :']
    lines += [f"{r['category']} : {r['n']}" for r in result['by_category']]
    lines += ['Ce rapport ne constitue pas une statistique officielle. Validation institutionnelle requise.']
    for line in lines:
        for part in simpleSplit(line, 'Helvetica',10,480):
            if y<55: pdf.showPage(); y=790
            pdf.setFont('Helvetica',10); pdf.drawString(50,y,part); y-=19
    pdf.save(); buf.seek(0)
    with db() as c: audit(c,u['id'],'export','report',detail={'format':'pdf','start':start,'end':end})
    return StreamingResponse(buf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="sisa_rapport.pdf"'})

@app.get('/admin/operations')
def operations(u=Depends(require_roles('admin'))):
    return {'database':'PostgreSQL' if DATABASE_URL else 'SQLite','backup_mode':'Sauvegardes gerees Render + export pg_dump' if DATABASE_URL else 'Copie SQLite manuelle',
            'restore_validated':False,'real_data_authorized':False,'external_ai':False,
            'version':'0.5.1','retention_policy':'A faire approuver','public_publication':False}

@app.get('/examples/template.csv')
def template_csv(u=Depends(user_from_token)):
    return FileResponse(ROOT/'examples'/'modele_import_dossiers.csv',media_type='text/csv',filename='modele_synthetique_sisa.csv')

class CorrectionIn(BaseModel):
    case: CaseIn
    reason: str = Field(min_length=5,max_length=1000)
    expected_version: int = Field(ge=1)

@app.post('/cases/{case_id}/corrections')
def correct_case_json(case_id:int, x:CorrectionIn, u=Depends(require_roles('admin','collector','supervisor'))):
    # Keep reasons and corrected values out of access-log query strings.
    return update_case(case_id,x.case,x.reason,x.expected_version,u)

# Additive legal model and versioned indicator catalogue.
from .legal import install_legal
install_legal(app, db, locked_case, audit, utcnow, user_from_token, require_roles, safe_spreadsheet_cell)

from .registry import install as install_registry
install_registry(app,db,locked_case,audit,utcnow,user_from_token,require_roles,safe_spreadsheet_cell)
