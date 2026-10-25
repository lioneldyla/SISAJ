"""Destructive ONLY to isolated loopback sisa_test, then restores into a new random DB.
For CI/test use. Refuses all remote hosts, other ports and other source database names.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import urlsplit,urlunsplit
import psycopg
from psycopg import sql

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
url=os.environ.get('DATABASE_URL','');parts=urlsplit(url)
if not (parts.hostname=='127.0.0.1' and parts.port==55432 and parts.path=='/sisa_test' and os.environ.get('SISA_TEST_POSTGRES')=='1'):
    raise SystemExit('Refused: isolated 127.0.0.1:55432/sisa_test and SISA_TEST_POSTGRES=1 required.')
os.environ.update(SISA_DEPLOYMENT='local',SISA_BOOTSTRAP_KEY='',SISA_SECURE_COOKIE='0')
from app.main import app
from fastapi.testclient import TestClient
with psycopg.connect(url) as c:
    c.execute('TRUNCATE users,sessions,cases,case_events,import_batches,audit_log,indicator_definitions,import_previews,login_attempts RESTART IDENTITY CASCADE')
    c.execute('DELETE FROM jurisdictions')
with TestClient(app) as client:
    password='Synthetic-Pg-Restore-2026!'
    assert client.post('/auth/bootstrap',json={'username':'restore_admin','password':password}).status_code==200
    headers={'Authorization':'Bearer '+client.post('/auth/login',json={'username':'restore_admin','password':password}).json()['access_token']}
    case=client.post('/cases',headers=headers,json={'rp_number':'SYNTH-RESTORE','rp_year':2026,'date_rp':'2026-01-01','provenance':'Fictif','category':'Fictif','transnational':False}).json()['id']
    assert client.put(f'/cases/{case}/legal',headers=headers,json={'expected_version':1,'reason':'Exercice de restauration','people':[{'reference':'P1','kind':'physical','role':'defendant','display_name':'Fictif'}],'offences':[{'reference':'I1','code':'TEST','label':'Fictif'}],'decisions':[{'reference':'D1','decision_date':'2026-02-01','on_merits':True,'outcomes':[{'person_reference':'P1','offence_reference':'I1','result':'conviction'}]}],'measures':[{'reference':'M1','kind':'fine','measure_date':'2026-02-01','amount':'12.50','currency':'XOF'}]}).status_code==200
    full=client.get(f'/cases/{case}/register',headers=headers).json()['record']
    full['procedure']['cabinet']='Cabinet synthétique restauré';full['procedure']['cabinet_state']='known'
    full['people'][0]['profession']='other';full['people'][0]['profession_other']='Profession synthétique restaurée'
    assert client.put(f'/cases/{case}/register',headers=headers,json={'expected_version':2,'reason':'Contrôle du registre complet','record':full}).status_code==200
    source_csv=b'rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-SOURCE-ARCHIVE,2026,2026-04-01,Fictif,Fictif,Non\n'
    source_preview=client.post('/registry/imports/preview',headers=headers,files={'file':('synthetic.csv',source_csv)}).json()['preview_id']
    source_batch=client.post('/registry/imports/'+source_preview+'/confirm',headers=headers).json()['batch_id']
    assert client.post(f'/cases/{case}/submit?expected_version=3',headers=headers).status_code==200
    assert client.post(f'/cases/{case}/validate?expected_version=4',headers=headers).status_code==200
    before=client.get('/stats/legal',headers=headers).json()
    assert client.post('/compliance/reviews',headers=headers,json={'scenario':'restore','result':'pending','expected':'Comparaison intégrale après restauration','observed':'Exercice synthétique en cours de vérification','evidence':'Restauration isolée exécutée par le script de test'}).status_code==200
    frozen=client.post('/dashboard/snapshots',headers=headers,json={'title':'État fictif avant restauration'}).json()
    preview=client.post('/imports/preview',headers=headers,files={'file':('synthetic.csv',b'rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-RESTORE-IMPORT,2026,2026-03-01,Fictif,Fictif,Non\n','text/csv')}).json()['preview_id']
pg_env={**os.environ,'PGPASSWORD':parts.password or ''}
base=['-h','127.0.0.1','-p','55432','-U',parts.username or 'sisa']
container=os.environ.get('SISA_TEST_PG_CONTAINER','')
if container and not __import__('re').fullmatch(r'[0-9a-f]{12,64}',container):
    raise SystemExit('Invalid isolated PostgreSQL test container ID.')
def pg_tool(name,database,flags,input=None):
    # Use the matching server image's client in CI, including PostgreSQL 18.
    cmd=['docker','exec','-i',container,name,'-U',parts.username or 'sisa','-d',database,*flags] if container else [name,*base,'-d',database,*flags]
    return subprocess.run(cmd,env=pg_env,input=input,capture_output=True)
dump=pg_tool('pg_dump','sisa_test',['-Fc'])
if dump.returncode:raise RuntimeError('pg_dump failed; connection details suppressed.')
assert dump.stdout.startswith(b'PGDMP')
restore_name='sisa_restore_'+secrets.token_hex(6);created=False
try:
    with psycopg.connect(url,autocommit=True) as c:
        c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restore_name)));created=True
    result=pg_tool('pg_restore',restore_name,['--no-owner','--no-acl','--single-transaction','--exit-on-error'],input=dump.stdout)
    if result.returncode:raise RuntimeError('pg_restore failed; connection details suppressed.')
    target=urlunsplit((parts.scheme,parts.netloc,'/'+restore_name,'',''))
    with psycopg.connect(url) as source,psycopg.connect(target) as restored:
        tables=[r[0] for r in source.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
        for name in tables:
            query=sql.SQL('SELECT * FROM {} ORDER BY 1,2').format(sql.Identifier(name))
            assert source.execute(query).fetchall()==restored.execute(query).fetchall(),name
    check='''
import json,os
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
 h=json.loads(os.environ['SISA_RESTORE_TEST_HEADER'])
 assert c.get('/auth/me',headers=h).status_code==200
 assert c.get('/stats/legal',headers=h).json()==json.loads(os.environ['SISA_RESTORE_TEST_STATS'])
 assert c.get('/cases/1/legal',headers=h).json()['measures'][0]['amount']=='12.50'
 assert c.post('/imports/'+os.environ['SISA_RESTORE_TEST_PREVIEW']+'/confirm',headers=h).json()['imported_rows']==1
 assert c.get('/cases',headers=h).json()['total']==3
 assert c.get('/cases/1/register',headers=h).json()['record']['procedure']['cabinet']=='Cabinet synthétique restauré'
 assert c.get('/registry/imports/'+os.environ['SISA_RESTORE_SOURCE_BATCH']+'/source',headers=h).content.startswith(b'rp_number')
 assert len(c.get('/compliance/reviews',headers=h).json()['items'])==1
 snap=c.get('/dashboard/snapshots/'+os.environ['SISA_RESTORE_SNAPSHOT_ID'],headers=h).json()
 assert snap['sha256']==os.environ['SISA_RESTORE_SNAPSHOT_HASH'] and snap['snapshot']['analysis']['cohort_size']==2
'''
    result=subprocess.run([sys.executable,'-c',check],cwd=root,env={**os.environ,'DATABASE_URL':target,'SISA_RESTORE_TEST_HEADER':json.dumps(headers),'SISA_RESTORE_TEST_STATS':json.dumps(before),'SISA_RESTORE_TEST_PREVIEW':preview,'SISA_RESTORE_SOURCE_BATCH':source_batch,'SISA_RESTORE_SNAPSHOT_ID':frozen['id'],'SISA_RESTORE_SNAPSHOT_HASH':frozen['sha256']},capture_output=True)
    if result.returncode:raise RuntimeError('Restored application verification failed; connection details suppressed.')
    print(f'PostgreSQL: pg_dump restored into a NEW isolated database; all {len(tables)} tables match.')
    print('Restored application: authentication, legal relations, indicators, pending import and record count verified.')
    print('Archive SHA256:',hashlib.sha256(dump.stdout).hexdigest())
finally:
    if created:
        with psycopg.connect(url,autocommit=True) as c:c.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(restore_name)))
