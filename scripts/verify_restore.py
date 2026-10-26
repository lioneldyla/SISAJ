"""Self-contained SQLite backup, isolated restore and application restart; synthetic only.
Uses no caller database URL and never modifies any pre-existing database.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
with tempfile.TemporaryDirectory(prefix='sisaj-restore-') as tmp:
    path=Path(tmp);source=path/'source'/'source.db';target=path/'restore'/'restored.db';backups=path/'backups'
    target.parent.mkdir()
    os.environ.update(DATABASE_URL='',SISA_DEPLOYMENT='local',SISA_BOOTSTRAP_KEY='',SISA_SECURE_COOKIE='0',SISA_DB_PATH=str(source),SISA_BACKUP_DIR=str(backups))
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        password='Synthetic-Restore-2026!'
        assert c.post('/auth/bootstrap',json={'username':'restore_admin','password':password}).status_code==200
        h={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'restore_admin','password':password}).json()['access_token']}
        cid=c.post('/cases',headers=h,json={'rp_number':'SYNTH-RESTORE','rp_year':2026,'date_rp':'2026-01-01','category':'Test fictif','provenance':'Test fictif','transnational':False}).json()['id']
        assert c.put(f'/cases/{cid}/legal',headers=h,json={'expected_version':1,'reason':'Exercice de restauration','people':[{'reference':'P1','kind':'physical','role':'defendant','display_name':'Personne fictive'}],'offences':[{'reference':'I1','code':'TEST','label':'Fictif'}],'decisions':[{'reference':'D1','decision_date':'2026-02-01','on_merits':True,'outcomes':[{'person_reference':'P1','offence_reference':'I1','result':'conviction'}]}],'measures':[{'reference':'M1','kind':'fine','measure_date':'2026-02-01','amount':'1200.50','currency':'XOF'}]}).status_code==200
        full=c.get(f'/cases/{cid}/register',headers=h).json()['record']
        full['procedure']['cabinet']='Cabinet synthétique restauré';full['procedure']['cabinet_state']='known'
        full['people'][0]['profession']='other';full['people'][0]['profession_other']='Profession synthétique restaurée'
        assert c.put(f'/cases/{cid}/register',headers=h,json={'expected_version':2,'reason':'Contrôle du registre complet','record':full}).status_code==200
        source_csv=b'rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-SOURCE-ARCHIVE,2026,2026-04-01,Fictif,Fictif,Non\n'
        source_preview=c.post('/registry/imports/preview',headers=h,files={'file':('synthetic.csv',source_csv)}).json()['preview_id']
        source_batch=c.post('/registry/imports/'+source_preview+'/confirm',headers=h).json()['batch_id']
        assert c.post(f'/cases/{cid}/submit?expected_version=3',headers=h).status_code==200
        assert c.post(f'/cases/{cid}/validate?expected_version=4',headers=h).status_code==200
        before=c.get('/stats/legal',headers=h).json()
        assert c.post('/compliance/reviews',headers=h,json={'scenario':'restore','result':'pending','expected':'Comparaison intégrale après restauration','observed':'Exercice synthétique en cours de vérification','evidence':'Restauration isolée exécutée par le script de test'}).status_code==200
        settings=c.get('/superadmin',headers=h).json()['settings']
        settings['site_name']='SISAJ restauration test'
        assert c.put('/superadmin/configuration',headers=h,json={'settings':settings,'expected_version':c.get('/superadmin',headers=h).json()['version'],'reason':'Exercice de sauvegarde et restauration'}).status_code==200
        frozen=c.post('/dashboard/snapshots',headers=h,json={'title':'État fictif avant restauration'}).json()
        content=b'rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-RESTORED-IMPORT,2026,2026-03-01,Test fictif,Test fictif,Non\n'
        pid=c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',content,'text/csv')}).json()['preview_id']
        backup=c.post('/admin/backup',headers=h).json();archive=backups/backup['file']
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==backup['sha256']
        # The source receives an audit entry after the backup snapshot. Compare snapshot -> restore.
        with sqlite3.connect(archive) as a,sqlite3.connect(target) as b:a.backup(b)
        tables=[]
        with sqlite3.connect(archive) as a,sqlite3.connect(target) as b:
            assert b.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert b.execute('PRAGMA foreign_key_check').fetchall()==[]
            tables=[r[0] for r in a.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for table in tables:
                assert a.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()==b.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall(),table
        # SQLite previews are sidecars: restore the separately copied pending preview as well.
        preview=source.parent/f'preview_{pid}.json'
        assert preview.exists()
        shutil.copy2(preview,target.parent/preview.name)
        check='''
import json,os
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
 h=json.loads(os.environ['SISA_RESTORE_TEST_HEADER'])
 assert c.get('/auth/me',headers=h).json()['super_admin'] is True
 assert c.get('/superadmin',headers=h).json()['settings']['site_name']=='SISAJ restauration test'
 assert len(c.get('/superadmin/configuration/history',headers=h).json()['items'])>=2
 assert c.get('/stats/legal',headers=h).json()==json.loads(os.environ['SISA_RESTORE_TEST_STATS'])
 assert c.get('/cases/1/legal',headers=h).json()['measures'][0]['amount']=='1200.50'
 assert c.post('/imports/'+os.environ['SISA_RESTORE_TEST_PREVIEW']+'/confirm',headers=h).json()['imported_rows']==1
 assert c.get('/cases',headers=h).json()['total']==3
 assert c.get('/cases/1/register',headers=h).json()['record']['procedure']['cabinet']=='Cabinet synthétique restauré'
 assert c.get('/registry/imports/'+os.environ['SISA_RESTORE_SOURCE_BATCH']+'/source',headers=h).content.startswith(b'rp_number')
 assert len(c.get('/compliance/reviews',headers=h).json()['items'])==1
 snap=c.get('/dashboard/snapshots/'+os.environ['SISA_RESTORE_SNAPSHOT_ID'],headers=h).json()
 assert snap['sha256']==os.environ['SISA_RESTORE_SNAPSHOT_HASH'] and snap['snapshot']['analysis']['cohort_size']==2
 print('Restored application: authentication, full legal record, identical indicators and pending import verified.')
'''
        result=subprocess.run([sys.executable,'-c',check],cwd=root,env={**os.environ,'SISA_DB_PATH':str(target),'SISA_RESTORE_TEST_HEADER':json.dumps(h),'SISA_RESTORE_TEST_STATS':json.dumps(before),'SISA_RESTORE_TEST_PREVIEW':pid,'SISA_RESTORE_SOURCE_BATCH':source_batch,'SISA_RESTORE_SNAPSHOT_ID':frozen['id'],'SISA_RESTORE_SNAPSHOT_HASH':frozen['sha256']},text=True,capture_output=True)
        if result.returncode:raise RuntimeError(result.stderr)
        print(result.stdout.strip())
        print(f'SQLite snapshot restored into a new database; {len(tables)} tables compared completely; integrity and foreign keys valid.')
        print('Archive SHA256:',backup['sha256'])
        print('Scope: isolated local synthetic exercise; no Render/PostgreSQL restore claimed.')
