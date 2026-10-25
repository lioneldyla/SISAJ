import hashlib
from fastapi.testclient import TestClient
from app.main import app,db

def setup(c):
    p='Synthetic-Transfer-2026!'
    assert c.post('/auth/bootstrap',json={'username':'transfer_admin','password':p}).status_code==200
    return {'Authorization':'Bearer '+c.post('/auth/login',json={'username':'transfer_admin','password':p}).json()['access_token']}

def imported(c,h):
    body=b'N\xc2\xb0 RP,Date RP\nSYNTH-TRANSFER,2026-01-01\n'
    r=c.post('/registry/imports/preview',headers=h,files={'file':('test.csv',body)});assert r.status_code==200,r.text
    r=c.post('/registry/imports/'+r.json()['preview_id']+'/confirm',headers=h);assert r.status_code==200,r.text
    return r.json()['batch_id']

def test_reversal_restore_preserves_original_and_audit():
    with TestClient(app) as c:
        h=setup(c);bid=imported(c,h)
        original=c.get(f'/registry/imports/{bid}/source',headers=h).content
        before=c.get('/registry/export.json',headers=h).json()
        r=c.get(f'/registry/batches/{bid}/reversal-preview',headers=h).json();assert r['can_reverse']
        url=f'/registry/batches/{bid}'
        assert c.post(url+'/reverse',headers=h,json={'reason':'Annulation essai','fingerprint':'0'*64}).status_code==409
        assert c.post(url+'/reverse',headers=h,json={'reason':'Annulation essai','fingerprint':r['fingerprint']}).status_code==200
        assert c.get('/cases',headers=h).json()['total']==0
        assert c.get(f'/registry/imports/{bid}/source',headers=h).content==original
        assert c.post(url+'/reverse',headers=h,json={'reason':'Annulation essai','fingerprint':r['fingerprint']}).status_code==409
        assert c.post(url+'/restore',headers=h,json={'reason':'Rétablir essai'}).status_code==200
        assert c.get('/registry/export.json',headers=h).json()==before
        with db() as con:
            assert con.execute("SELECT count(*) n FROM audit_log WHERE action IN ('reverse','restore')").fetchone()['n']==2

def test_changed_draft_and_collector_cannot_reverse():
    with TestClient(app) as c:
        h=setup(c);bid=imported(c,h)
        p=c.get(f'/registry/batches/{bid}/reversal-preview',headers=h).json()
        cid=c.get('/cases',headers=h).json()['items'][0]['id']
        with db(write=True) as con:con.execute('UPDATE cases SET version=3 WHERE id=?',(cid,))
        assert c.post(f'/registry/batches/{bid}/reverse',headers=h,json={'reason':'Annulation essai','fingerprint':p['fingerprint']}).status_code==409
        assert not c.get(f'/registry/batches/{bid}/reversal-preview',headers=h).json()['can_reverse']
        c.post('/users',headers=h,json={'username':'collector_fixture','password':'Synthetic-Collector-2026!','role':'collector'})
        ch={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'collector_fixture','password':'Synthetic-Collector-2026!'}).json()['access_token']}
        assert c.post(f'/registry/batches/{bid}/reverse',headers=ch,json={'reason':'Annulation essai','fingerprint':p['fingerprint']}).status_code==403

def test_restore_conflict_is_atomic_and_documents_are_not_cases():
    with TestClient(app) as c:
        h=setup(c);bid=imported(c,h);p=c.get(f'/registry/batches/{bid}/reversal-preview',headers=h).json()
        c.post(f'/registry/batches/{bid}/reverse',headers=h,json={'reason':'Annulation essai','fingerprint':p['fingerprint']})
        imported(c,h)
        assert c.post(f'/registry/batches/{bid}/restore',headers=h,json={'reason':'Rétablir essai'}).status_code==409
        assert c.get('/cases',headers=h).json()['total']==1

def test_typed_package_preserves_relationships_but_never_validates():
    import json
    from tests.test_registry import complete
    from app.registry_models import Register
    core={'rp_number':'SYNTH-PACKAGE','rp_year':2026,'date_rp':'2026-01-01','provenance':'Fictif','category':'Fictif','transnational':False}
    record=complete()
    raw={'synthetic':True,'core':core,'record':record,'target_status':'validated'}
    with TestClient(app) as c:
        h=setup(c)
        p=c.post('/registry/imports/preview',headers=h,files={'file':('registers.jsonl',json.dumps(raw).encode())}).json();assert p['can_confirm'],p
        result=c.post('/registry/imports/'+p['preview_id']+'/confirm',headers=h).json()
        case=c.get('/cases',headers=h).json()['items'][0]
        assert case['status']=='draft' and case['version']==2
        assert c.get(f'/cases/{case["id"]}/register',headers=h).json()['record']==Register.model_validate(record).model_dump(mode='json')
        assert c.get('/registry/statements',headers=h).json()['counts'].get('received',0)==0
        assert c.get('/registry/batches/'+result['batch_id']+'/reversal-preview',headers=h).json()['can_reverse']
        data=b'Matrice : aucune ligne ne constitue un dossier'
        r=c.post('/registry/documents',headers=h,data={'purpose':'reference'},files={'file':('matrice.txt',data)});assert r.status_code==200
        did=r.json()['id'];assert r.json()['creates_cases'] is False
        assert c.post('/registry/documents',headers=h,data={'purpose':'reference'},files={'file':('copie.txt',data)}).json()['status']=='already_present'
        assert c.get(f'/registry/documents/{did}/source',headers=h).content==data
        assert c.get('/registry/documents',headers=h).json()['items'][0]['sha256']==hashlib.sha256(data).hexdigest()
        assert c.get('/cases',headers=h).json()['total']==1
