import os, tempfile, json, csv, io
from pathlib import Path
os.environ['DATABASE_URL']=''
os.environ['SISA_DEPLOYMENT']='local'
os.environ['SISA_BOOTSTRAP_KEY']='Synthetic-Restore-Bootstrap-2026!'
with tempfile.TemporaryDirectory(prefix='sisa-audit-synthetic-') as tmp:
 os.environ['SISA_DB_PATH']=str(Path(tmp)/'audit.db')
 os.environ['SISA_BACKUP_DIR']=str(Path(tmp)/'backups')
 from fastapi.testclient import TestClient
 from app.main import app, map_import
 c=TestClient(app,raise_server_exceptions=False)
 c.post('/auth/bootstrap',headers={'X-SISA-Bootstrap-Key':'Synthetic-Restore-Bootstrap-2026!'},json={'username':'audit_admin','password':'Synthetic-Audit-Password-2026!'})
 token=c.post('/auth/login',json={'username':'audit_admin','password':'Synthetic-Audit-Password-2026!'}).json()['access_token']
 h={'Authorization':'Bearer '+token}
 base=dict(rp_number='RP-SYNTH-A',rp_year=2026,date_rp='2026-01-01',provenance='OPJ fictif',transnational=False,category='=1+1')
 a=c.post('/cases',headers=h,json=base).json()['id']
 b=c.post('/cases',headers=h,json={**base,'rp_number':'RP-SYNTH-B'}).json()['id']
 print('duplicate PATCH HTTP',c.patch(f'/cases/{b}',headers=h,params={'reason':'synthetic conflict'},json=base).status_code)
 print('blank fields POST HTTP',c.post('/cases',headers=h,json={**base,'rp_number':'   ','provenance':'   ','category':'   '}).status_code)
 print('fractional import mapping',map_import({**base,'person_physical_count':'1.9','rp_year':'2026.9'})['person_physical_count'],map_import({**base,'rp_year':'2026.9'})['rp_year'])
 c.post(f'/cases/{a}/submit',headers=h);c.post(f'/cases/{a}/validate',headers=h)
 event=c.post(f'/cases/{a}/events',headers=h,params={'event_type':'synthetic','fine_amount':'NaN'})
 print('NaN event HTTP',event.status_code,'case status',c.get(f'/cases/{a}',headers=h).json()['status'])
 exported=list(csv.DictReader(io.StringIO(c.get('/exports/cases.csv',headers=h).content.decode('utf-8-sig'))))
 print('CSV formula preserved',any(r['category']=='=1+1' for r in exported))
 backup=c.post('/admin/backup',headers=h).json()
 import sqlite3,hashlib,shutil
 path=Path(tmp)/'backups'/backup['file']; restored=Path(tmp)/'restored.db';shutil.copy2(path,restored)
 with sqlite3.connect(restored) as con:
  print('backup hash correct',hashlib.sha256(path.read_bytes()).hexdigest()==backup['sha256'],'restored integrity',con.execute('PRAGMA integrity_check').fetchone()[0],'restored cases',con.execute('SELECT COUNT(*) FROM cases').fetchone()[0])

