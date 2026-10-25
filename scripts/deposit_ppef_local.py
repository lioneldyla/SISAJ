"""Deposit supplied/generated documents in the isolated prepared SISAJ copy only."""
import os,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
target=root/'outputs/charged_sisaj/SISAJ_charge.sqlite'
assert target.is_file(),'Prepare the isolated copy and verify its backup first'
assert Path(str(target)+'.backup').is_file()
os.environ.update(DATABASE_URL='',SISA_DEPLOYMENT='local',SISA_BOOTSTRAP_KEY='',SISA_SECURE_COOKIE='0',SISA_DB_PATH=str(target))
sys.path.insert(0,str(root))
from app.main import app
from fastapi.testclient import TestClient
files=[p for p in (root/'outputs/ppef_1500').rglob('*') if p.is_file() and p.suffix.lower() in ('.csv','.xlsx','.json','.jsonl','.md','.txt') and p.name!='donnees_classeur.json']
files+=list((root.parent/'upload').glob('*'))
with TestClient(app) as c:
    login=c.post('/auth/login',json={'username':'fixture_admin','password':'Test-PPEF-1500-2026!'})
    assert login.status_code==200
    h={'Authorization':'Bearer '+login.json()['access_token']}
    manifest=[]
    for path in sorted(files):
        data=path.read_bytes()
        r=c.post('/registry/documents',headers=h,data={'purpose':'technical_test' if 'anomalies' in path.parts else 'reference'},files={'file':(path.name,data)})
        assert r.status_code==200,(path.name,r.status_code)
        item=r.json();assert c.get('/registry/documents/'+item['id']+'/source',headers=h).content==data
        manifest.append({'filename':path.name,'id':item['id'],'bytes':len(data),'status':item['status']})
    assert c.get('/cases',headers=h).json()['total']==1500
    proof={'database':'SISAJ_charge.sqlite','remote_modified':False,'cases':1500,'documents':manifest,'byte_round_trip_verified':True}
    (target.parent/'chargement_verifie.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
    print(json.dumps({'cases':1500,'documents':len(manifest),'success':True}))
