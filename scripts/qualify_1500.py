"""Repeatable complete qualification; always creates its own isolated synthetic SQLite database."""
import argparse,io,json,os,sqlite3,sys,tempfile,time,zipfile
from decimal import Decimal
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
p=argparse.ArgumentParser();p.add_argument('--report',type=Path);a=p.parse_args();report={'officially_approved':False,'scope':'isolated synthetic technical qualification','checks':{},'profile_matrix':[]}
with tempfile.TemporaryDirectory(prefix='sisaj-qualify-1500-') as tmp:
 os.environ.update(DATABASE_URL='',SISA_DEPLOYMENT='local',SISA_BOOTSTRAP_KEY='',SISA_SECURE_COOKIE='0',SISA_DB_PATH=str(Path(tmp)/'source.db'),SISA_BACKUP_DIR=str(Path(tmp)/'backups'))
 from fastapi.testclient import TestClient
 from app.main import app
 from app.qualification_data import items,EXPECTED,anomalies
 from secure_backup import pack,unpack
 password='Synthetic-Qualification-2026!'
 with TestClient(app) as c:
  assert c.post('/auth/bootstrap',json={'username':'qualification_admin','password':password}).status_code==200
  h={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'qualification_admin','password':password}).json()['access_token']}
  rows=list(items());raw=('\n'.join(json.dumps(r) for r in rows)+'\n').encode();start=time.perf_counter()
  r=c.post('/registry/imports/preview',headers=h,files={'file':('qualification.jsonl',raw)});assert r.status_code==200,r.text;preview=r.json();assert preview['can_confirm'],preview['errors'][:2]
  result=c.post('/registry/imports/'+preview['preview_id']+'/confirm',headers=h);assert result.status_code==200,result.text
  bad=('\n'.join(json.dumps(v) for v in anomalies())+'\n').encode()
  rejected=c.post('/registry/imports/preview',headers=h,files={'file':('anomalies.jsonl',bad)}).json();assert not rejected['can_confirm'];report['checks']['intentional_anomalies_rejected']=True
  report['import_seconds']=round(time.perf_counter()-start,3);report['checks']['import_1500']=True
  repeat=c.post('/registry/imports/preview',headers=h,files={'file':('qualification.jsonl',raw)}).json();assert not repeat['can_confirm'];report['checks']['repeated_import_blocked']=True
  start=time.perf_counter();data=c.get('/dashboard/analysis?as_of=2026-10-26',headers=h).json();report['dashboard_seconds']=round(time.perf_counter()-start,3);cards={v['key']:v for v in data['cards']}
  assert cards['received']['value']==1500 and cards['judged']['value']==600 and cards['persons']['value']==3000 and cards['quality']['value']==0
  assert cards['delay']['value']==40
  assert Decimal(cards['seizure']['value'])==Decimal(EXPECTED['saisies_xof']) and Decimal(cards['confiscation']['value'])==Decimal(EXPECTED['confiscations_xof'])
  assert len(data['procedural_coverage'])>=4;report['checks']['independent_expected_statistics']=True
  cid=c.get('/cases?q=RECETTE-V2-00001',headers=h).json()['items'][0]['id'];other=c.get('/cases?q=RECETTE-V2-00002',headers=h).json()['items'][0]['id']
  for profile in ('technical','direction','statistician','cabinet','clerk'):
   name='recipe_'+profile;scoped=profile in ('cabinet','clerk')
   response=c.post('/superadmin/users',headers=h,json={'username':name,'password':password,'profile_id':profile,'cabinets':['Cabinet de recette 1'] if scoped else [],'reason':'Qualification automatisée des profils'});assert response.status_code==200,response.text
   uh={'Authorization':'Bearer '+c.post('/auth/login',json={'username':name,'password':password}).json()['access_token']}
   count=c.get('/cases',headers=uh).json()['total'];assert count==(300 if scoped else 1500)
   assert c.get(f'/cases/{other}',headers=uh).status_code==(404 if scoped else 200)
   assert c.get('/dashboard/analysis',headers=uh).json()['cohort_size']==count
   ex=c.get('/dashboard/export.csv',headers=uh);assert ex.status_code==(403 if profile=='clerk' else 200)
   if scoped and ex.status_code==200:assert 'RECETTE-V2-00002' not in ex.text
   event={'kind':'deadline','event_date':'2026-10-26','due_date':'2026-10-28','status':'pending','source_reference':'TEST-PIECE','description':'Échéance intégralement fictive','reason':'Recette des droits de modification','expected_version':c.get(f'/cases/{cid}',headers=h).json()['version']}
   change=c.post(f'/cases/{cid}/followup',headers=uh,json=event);assert change.status_code==(403 if profile in ('direction','statistician') else 200),change.text
   report['profile_matrix'].append({'profile':profile,'perimeter_cases':count,'export_http':ex.status_code,'followup_write_http':change.status_code,'passed':True})
  report['checks']['profile_boundaries']=True
  ready=c.get('/qualification',headers=h).json();assert ready['quality']['cases_with_issues']==0 and not ready['officially_approved']
  backup=c.post('/admin/backup',headers=h).json();source=Path(tmp)/'backups'/backup['file'];encrypted=Path(tmp)/'backup.encrypted';restored=Path(tmp)/'restored.db';secret='Synthetic-Backup-Encryption-2026!'
  pack(source,encrypted,secret);unpack(encrypted,restored,secret)
  with sqlite3.connect(source) as s,sqlite3.connect(restored) as r:
   assert r.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not r.execute('PRAGMA foreign_key_check').fetchall()
   tables=[v[0] for v in s.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
   for table in tables:assert s.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()==r.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall(),table
  report['checks']['encrypted_backup_restored_full_comparison']=True;report['restored_tables']=len(tables);report['expected']=EXPECTED
if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
