"""Synthetic Docker/PostgreSQL integration and restore test.
Requires the isolated test container sisa-postgres-test and its temporary configuration.
Never point this script at an institutional database. Does not deploy to Render.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
import psycopg

config = Path('/tmp/sisa-postgres-test.json')
url = json.loads(config.read_text())['url']
assert urlsplit(url).hostname == '127.0.0.1' and urlsplit(url).path == '/sisa_test'
with psycopg.connect(url) as conn:
    for name in ('users','sessions','cases','case_events','import_batches','audit_log','indicator_definitions','import_previews','login_attempts'):
        # All names are fixed internal identifiers, never user input.
        conn.execute('TRUNCATE '+name+' RESTART IDENTITY CASCADE')


def docker(*args, check=True, **kw):
    result=subprocess.run(['docker',*args],capture_output=True,**kw)
    if check and result.returncode:
        raise RuntimeError('Docker operation failed: '+args[0])
    return result


def wait_ready(client):
    for _ in range(100):
        try:
            r=client.get('/ready')
            if r.status_code==200:
                assert r.json()['storage']=='postgresql'
                return
        except httpx.TransportError:
            pass
        time.sleep(.2)
    raise RuntimeError('Readiness timeout')

key=secrets.token_urlsafe(32)
password=secrets.token_urlsafe(32)
parts=urlsplit(url)
internal=urlunsplit((parts.scheme,parts.netloc.replace('127.0.0.1:55432','sisa-postgres-test:5432'),parts.path,'',''))
env_file=Path('/tmp/sisa-container-test.env')
env_file.write_text('DATABASE_URL='+internal+'\nSISA_DEPLOYMENT=render\nSISA_DATA_MODE=synthetic\nSISA_BOOTSTRAP_KEY='+key+'\nPORT=10000\n')
env_file.chmod(0o600)
docker('network','create','sisa-test-net',check=False)
docker('network','connect','sisa-test-net','sisa-postgres-test',check=False)
try:
    docker('run','-d','--name','sisa-platform-test','--network','sisa-test-net','-p','127.0.0.1:8878:10000','--env-file',str(env_file),'sisa-platform:audit')
    with httpx.Client(base_url='http://127.0.0.1:8878',timeout=15) as client:
        wait_ready(client)
        assert client.post('/auth/bootstrap',json={'username':'container_admin','password':password}).status_code==403
        assert client.post('/auth/bootstrap',headers={'X-SISA-Bootstrap-Key':key},json={'username':'container_admin','password':password}).status_code==200
        h={'Authorization':'Bearer '+client.post('/auth/login',json={'username':'container_admin','password':password}).json()['access_token']}
        data=dict(rp_number='SYNTH-CONTAINER-001',rp_year=2026,date_rp='2026-01-10',provenance='OPJ fictif',category='Qualification fictive',transnational=False)
        cid=client.post('/cases',headers=h,json=data).json()['id']
        assert client.post(f'/cases/{cid}/submit',headers=h).status_code==200
        assert client.post(f'/cases/{cid}/validate',headers=h).status_code==200
        content=b'rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-PREVIEW-001,2026,2026-02-02,Unite fictive,Qualification fictive,Non\n'
        pid=client.post('/imports/preview',headers=h,files={'file':('synthetic.csv',content,'text/csv')}).json()['preview_id']
        docker('restart','sisa-platform-test')
        wait_ready(client)
        assert client.get('/auth/me',headers=h).status_code==200
        assert client.post(f'/imports/{pid}/confirm',headers=h).json()['imported_rows']==1
        before=client.get('/stats',headers=h).json()
        assert before['received_cases']==1
        assert client.get('/exports/cases.xlsx',headers=h).content.startswith(b'PK')
        assert client.get('/reports/summary.pdf',headers=h).content.startswith(b'%PDF-')
        # Verify browser security flags in the exact Docker image.
        login=client.post('/auth/login',json={'username':'container_admin','password':password})
        cookie=login.headers['set-cookie']
        assert all(flag in cookie for flag in ('HttpOnly','Secure','SameSite=strict'))
        assert client.get('/').status_code==200
        assert client.get('/static/app.js').status_code==200
        print('Container: protected bootstrap, workflow, PostgreSQL, exports and secure-cookie flags verified.')
        print('Restart: records, bearer session and unconfirmed import preview preserved.')

    dump=docker('exec','sisa-postgres-test','pg_dump','-U','sisa','-d','sisa_test','-Fc').stdout
    assert dump.startswith(b'PGDMP')
    dump_path=Path('/tmp/sisa-test-restore.dump');dump_path.write_bytes(dump);dump_path.chmod(0o600)
    # Always create a new restoration database; never clean or replace an existing database.
    restore_name='sisa_restore_'+secrets.token_hex(4)
    docker('exec','sisa-postgres-test','createdb','-U','sisa',restore_name)
    try:
        result=subprocess.run(['docker','exec','-i','sisa-postgres-test','pg_restore','-U','sisa','-d',restore_name,'--no-owner','--no-acl','--single-transaction','--exit-on-error'],input=dump,capture_output=True)
        assert result.returncode==0
        restored_url=urlunsplit((parts.scheme,parts.netloc,'/'+restore_name,'',''))
        with psycopg.connect(url) as source, psycopg.connect(restored_url) as target:
            for table in ('users','sessions','cases','case_events','import_batches','audit_log','indicator_definitions','import_previews'):
                a=source.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
                b=target.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
                assert a==b,table
        restore_env=Path('/tmp/sisa-restore-container.env')
        restore_env.write_text(env_file.read_text().replace('/sisa_test','/'+restore_name))
        restore_env.chmod(0o600)
        try:
            docker('run','-d','--name','sisa-platform-restore-test','--network','sisa-test-net','-p','127.0.0.1:8879:10000','--env-file',str(restore_env),'sisa-platform:audit')
            with httpx.Client(base_url='http://127.0.0.1:8879',timeout=15) as restored:
                wait_ready(restored)
                assert restored.get('/auth/me',headers=h).status_code==200
                assert restored.get('/stats',headers=h).json()==before
                assert restored.get('/cases',headers=h).json()['total']==2
                assert len(restored.get('/imports',headers=h).json()['items'])==1
        finally:
            docker('rm','-f','sisa-platform-restore-test',check=False)
            restore_env.unlink(missing_ok=True)
        print('Restore: pg_dump/pg_restore into a new database; eight complete tables match; restored application authenticates and returns identical statistics, two cases and one import batch.')
        print('Archive SHA256:',hashlib.sha256(dump).hexdigest())
    finally:
        docker('exec','sisa-postgres-test','dropdb','-U','sisa',restore_name)
        dump_path.unlink(missing_ok=True)
finally:
    docker('rm','-f','sisa-platform-test',check=False)
    env_file.unlink(missing_ok=True)
