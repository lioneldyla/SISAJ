"""Operator-only management command. Uses registered import endpoints, never auto-runs.
Only the bundled fully synthetic fixture is accepted. Existing cases are never overwritten.
"""
import argparse,asyncio,hashlib,io,json,os,sys,zipfile
from pathlib import Path
from starlette.datastructures import UploadFile
p=argparse.ArgumentParser();p.add_argument('--admin',required=True);p.add_argument('--package',required=True);p.add_argument('--confirm-synthetic-load',action='store_true');p.add_argument('--backup-receipt',required=True);args=p.parse_args()
assert args.confirm_synthetic_load
assert args.backup_receipt=='sisa_pre_transfer_20261025_121331','Use the verified pre-transfer backup receipt'
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from app.main import app,db
assert os.getenv('SISA_DATA_MODE','synthetic')=='synthetic'
def endpoint(path):return next(r.endpoint for r in app.routes if getattr(r,'path',None)==path)
async def main():
    with db() as c:
        user=c.execute('SELECT id,username,role FROM users WHERE username=? AND active=1',(args.admin,)).fetchone()
        assert user and user['role']=='admin','Existing active administrator required'
        assert c.execute('SELECT count(*) n FROM cases').fetchone()['n']==0,'Existing cases: stop and review collisions; never overwrite'
    user=dict(user);archive=Path(args.package)
    with zipfile.ZipFile(archive) as z:
        data=z.read('enriched/registres_enrichis.jsonl')
        expected=json.loads(z.read('enriched/attendus_enrichis.json'))
        result=await endpoint('/registry/imports/preview')(file=UploadFile(filename='registres_enrichis.jsonl',file=io.BytesIO(data)),sheet=None,date_role=None,u=user)
        assert result['can_confirm'] and result['valid_rows']==1500 and result['error_count']==0,result['errors'][:2]
        confirmed=endpoint('/registry/imports/{preview_id}/confirm')(preview_id=result['preview_id'],u=user)
        documents=[]
        for name in z.namelist():
            if name.endswith('/') or name=='enriched/registres_enrichis.jsonl':continue
            body=z.read(name)
            if len(body)>15*1024*1024:continue
            d=await endpoint('/registry/documents')(file=UploadFile(filename=name.replace('/','__'),file=io.BytesIO(body)),purpose='technical_test' if '/anomalies/' in name else 'reference',u=user)
            documents.append(d['id'])
    with db() as c:
        rows=c.execute('SELECT r.payload,c.status FROM registry_records r JOIN cases c ON c.id=r.case_id WHERE c.source_batch=?',(confirmed['batch_id'],)).fetchall()
        assert len(rows)==1500 and all(r['status']=='draft' for r in rows)
        payloads=[json.loads(r['payload']) for r in rows]
        assert sum(len(r['people']) for r in payloads)==3864
        from app.dashboard import analyze
        dashboard=analyze(c,user,as_of=__import__('datetime').date(2026,10,25))
        cards={x['key']:x for x in dashboard['cards']}
        assert cards['received']['value']==1500 and cards['judged']['value']==1500
        assert cards['persons']['value']==3864
        assert cards['seizure']['value']==expected['financial_xof']['seizure']
        assert cards['confiscation']['value']==expected['financial_xof']['confiscation']
    preview=endpoint('/registry/batches/{bid}/reversal-preview')(bid=confirmed['batch_id'],u=user)
    assert preview['can_reverse'] and preview['dossiers']==1500 and preview['people']==3864
    proof={'success':True,'batch_id':confirmed['batch_id'],'cases':1500,'people':3864,'decisions':1500,'measures':sum(len(r['measures']) for r in payloads),'documents':len(set(documents)),'status':'draft','backup_receipt':args.backup_receipt,'officially_approved':False,'reversal_preview_verified':True,'sha256':hashlib.sha256(data).hexdigest()}
    Path('/tmp/sisaj_loaded_test_proof.json').write_text(json.dumps(proof,indent=2))
    print('SISAJ_TEST_LOAD_VERIFIED',json.dumps(proof))
asyncio.run(main())
