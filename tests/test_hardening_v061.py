"""Synthetic acceptance cases; never touches a deployment or a user workbook."""
import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app, db, DB_PATH, DATABASE_URL
from test_platform import auth, PASSWORD

BODY={'username':'admin_new','password':PASSWORD}

def test_bootstrap_missing_secret_fails_closed(monkeypatch):
    monkeypatch.setenv('SISA_BOOTSTRAP_KEY','')
    with TestClient(app) as c:
        assert c.post('/auth/bootstrap',json=BODY).status_code==403
    with db() as c: assert c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']==0

def test_account_throttle_survives_peer_rotation():
    for i in range(5):
        with TestClient(app,client=(f'192.0.2.{i+1}',50000)) as c:
            assert c.post('/auth/login',json={'username':'unknown','password':'bad'}).status_code==401
    with TestClient(app,client=('192.0.2.99',50000)) as c:
        r=c.post('/auth/login',json={'username':'unknown','password':'bad'})
        assert r.status_code==429 and int(r.headers['retry-after'])>0

def test_concurrent_attempt_reservations():
    def attempt(i):
        with TestClient(app,client=(f'192.0.2.{i+1}',50000)) as c:
            return c.post('/auth/login',json={'username':'unknown','password':'bad'}).status_code
    with ThreadPoolExecutor(max_workers=8) as pool: codes=list(pool.map(attempt,range(8)))
    assert codes.count(401)==5 and codes.count(429)==3

CSV=b'rp_number,rp_year,date_rp,provenance,category,transnational\n\nSYN-TRACE,2026,2026-01-01,OPJ fictif,Fictif,Non\n'

def test_legacy_source_is_exact_and_coordinates_preserved():
    with TestClient(app) as c:
        h=auth(c)
        r=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',CSV)})
        assert r.status_code==200
        p=r.json();assert p['can_confirm']
        done=c.post(f"/imports/{p['preview_id']}/confirm",headers=h)
        assert done.status_code==200,done.text
        bid=done.json()['batch_id']
        r=c.get(f'/imports/{bid}/source',headers=h)
        assert r.status_code==200 and r.content==CSV
        t=c.get(f'/imports/{bid}/provenance',headers=h).json()
        assert t['sha256']==hashlib.sha256(CSV).hexdigest()
        assert t['rows'][0]['row']==3
        assert t['rows'][0]['cells'][0]=={'column':'A','header':'rp_number','value':'SYN-TRACE'}
        assert c.post(f"/imports/{p['preview_id']}/confirm",headers=h).status_code==404

def test_duplicate_headers_block_legacy_import():
    with TestClient(app) as c:
        h=auth(c)
        r=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',b'rp_number,rp_number\nA,B\n')})
        assert r.status_code==400

def test_legacy_preview_private_on_sqlite():
    if DATABASE_URL:return
    with TestClient(app) as c:
        h=auth(c);p=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',CSV)}).json()
        assert (DB_PATH.parent/f"preview_{p['preview_id']}.json").stat().st_mode & 0o077==0

def test_throttle_expires_at_boundary(monkeypatch):
    monkeypatch.setattr('app.main.time.time',lambda:10000)
    with TestClient(app) as c:
        for _ in range(5):assert c.post('/auth/login',json={'username':'expired','password':'bad'}).status_code==401
        r=c.post('/auth/login',json={'username':'expired','password':'bad'})
        assert r.status_code==429 and r.headers['retry-after']=='900'
        monkeypatch.setattr('app.main.time.time',lambda:10900)
        assert c.post('/auth/login',json={'username':'expired','password':'bad'}).status_code==401

def test_peer_throttle_limits_rotating_usernames():
    with TestClient(app) as c:
        for i in range(30):
            assert c.post('/auth/login',json={'username':f'unknown-{i}','password':'bad'}).status_code==401
        assert c.post('/auth/login',json={'username':'another','password':'bad'}).status_code==429

def test_failure_audit_never_contains_credentials():
    with TestClient(app) as c:
        c.post('/auth/login',json={'username':'private-user','password':'private-password'})
    with db() as c:
        log=c.execute("SELECT detail_json FROM audit_log WHERE action='login_failure'").fetchone()
        assert log and 'private-' not in log['detail_json']

def test_exact_session_expiry_is_denied(monkeypatch):
    monkeypatch.setattr('app.main.time.time',lambda:10000)
    with TestClient(app) as c:
        h=auth(c)
        with db(write=True) as d:d.execute('UPDATE sessions SET expires_at=?',(10000,))
        assert c.get('/auth/me',headers=h).status_code==401

def test_bad_source_hash_rolls_back_confirmation():
    with TestClient(app) as c:
        h=auth(c);p=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',CSV)}).json()['preview_id']
        if DATABASE_URL:
            with db(write=True) as d:
                row=d.execute('SELECT payload FROM import_previews WHERE id=?',(p,)).fetchone()
                value=json.loads(row['payload']);value['provenance']['sha256']='0'*64
                d.execute('UPDATE import_previews SET payload=? WHERE id=?',(json.dumps(value),p))
        else:
            path=DB_PATH.parent/f'preview_{p}.json';value=json.loads(path.read_text())
            value['provenance']['sha256']='0'*64;path.write_text(json.dumps(value))
        assert c.post(f'/imports/{p}/confirm',headers=h).status_code==409
        assert c.get('/cases',headers=h).json()['total']==0
        with db() as d:
            assert d.execute('SELECT COUNT(*) n FROM import_batches').fetchone()['n']==0
            assert d.execute('SELECT COUNT(*) n FROM import_sources').fetchone()['n']==0

def test_source_download_is_supervised_and_integrity_checked():
    with TestClient(app) as c:
        h=auth(c);p=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',CSV)}).json()['preview_id']
        bid=c.post(f'/imports/{p}/confirm',headers=h).json()['batch_id']
        c.post('/users',headers=h,json={'username':'agent','password':PASSWORD,'role':'collector'})
        a={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'agent','password':PASSWORD}).json()['access_token']}
        for route in ['source','provenance']:
            assert c.get(f'/imports/{bid}/{route}',headers=a).status_code==403
        with db(write=True) as d:d.execute('UPDATE import_sources SET sha256=? WHERE batch_id=?',('0'*64,bid))
        assert c.get(f'/imports/{bid}/source',headers=h).status_code==409

def test_error_locations_are_physical_source_lines():
    with TestClient(app) as c:
        h=auth(c);content=CSV.replace(b'2026-01-01',b'bad-date')
        r=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',content)}).json()
        assert r['can_confirm'] is False
        assert r['errors'][0]['row']==3 and r['errors'][0]['sheet']=='CSV'
        assert r['errors'][0]['columns'][0]['column']=='A'

def test_xlsx_source_coordinates_and_formulas():
    from openpyxl import Workbook
    from io import BytesIO
    wb=Workbook();ws=wb.active;ws.title='AUDIENCES PENALES'
    ws.append(['Contexte fictif']);ws.append([])
    ws.append(['N° RP','Date RP','Unité (OPJ) de Provenance','Dossier à caractère transnational (oui/non)','Infraction retenue par le Parquet'])
    ws.append(['SYN-XLSX','2026-01-01','Fictif','Non','Fictif'])
    buf=BytesIO();wb.save(buf)
    with TestClient(app) as c:
        h=auth(c)
        p=c.post('/imports/preview',headers=h,files={'file':('synthetic.xlsx',buf.getvalue())}).json()
        assert p['can_confirm']
        bid=c.post(f"/imports/{p['preview_id']}/confirm",headers=h).json()['batch_id']
        t=c.get(f'/imports/{bid}/provenance',headers=h).json()
        assert t['header_row']==3 and t['rows'][0]['row']==4 and t['rows'][0]['case_id']
        assert c.get(f'/imports/{bid}/source',headers=h).content==buf.getvalue()
        ws['A4']='="EXECUTABLE"';bad=BytesIO();wb.save(bad)
        assert c.post('/imports/preview',headers=h,files={'file':('formula.xlsx',bad.getvalue())}).status_code==422

def test_large_exponents_rejected_before_integer_or_money_expansion():
    import pytest
    from app.main import parse_integer
    from app.ppef_import import integer,money
    for parser in (parse_integer,integer,money):
        with pytest.raises(ValueError):parser('1e100000000')

def test_local_operator_setup_without_http_secret(monkeypatch,capsys):
    import pytest
    from scripts.provision_admin import main
    if DATABASE_URL:return
    monkeypatch.setenv('SISA_BOOTSTRAP_KEY','')
    monkeypatch.setattr('sys.argv',['provision_admin.py','operator_admin'])
    monkeypatch.setattr('getpass.getpass',lambda _:PASSWORD)
    main()
    out=capsys.readouterr().out
    assert PASSWORD not in out and 'créé' in out
    with TestClient(app) as c:
        assert c.post('/auth/login',json={'username':'operator_admin','password':PASSWORD}).status_code==200
    with pytest.raises(SystemExit):main()

def test_operator_setup_refuses_remote_database_before_password_prompt(monkeypatch):
    import pytest
    from scripts.provision_admin import main
    monkeypatch.setenv('DATABASE_URL','postgresql://example@remote.invalid/test')
    monkeypatch.setattr('sys.argv',['provision_admin.py','operator_admin'])
    monkeypatch.setattr('getpass.getpass',lambda _: (_ for _ in ()).throw(AssertionError('must not prompt')))
    with pytest.raises(SystemExit) as e:main()
    assert e.value.code==2
