"""Reproduced regressions; all identities and records are synthetic."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def context():
    with TestClient(app) as c:
        credentials={'username':'audit_test','password':'Synthetic-Audit-2026!'}
        assert c.post('/auth/bootstrap',json=credentials).status_code==200
        h={'Authorization':'Bearer '+c.post('/auth/login',json=credentials).json()['access_token']}
        core={'rp_number':'SYNTH-AUDIT','rp_year':2026,'date_rp':'2026-01-01','provenance':'Unité fictive','category':'Qualification fictive','transnational':None}
        cid=c.post('/cases',headers=h,json=core).json()['id']
        yield c,h,core,cid

def test_header_correction_preserves_category_and_register_state(context):
    c,h,core,cid=context
    response=c.patch(f'/cases/{cid}?reason=Correction%20synthétique&expected_version=1',headers=h,json={**core,'category':'Qualification corrigée'})
    assert response.status_code==200
    result=c.get(f'/cases/{cid}',headers=h).json()
    assert result['category']=='Qualification corrigée'
    assert result['transnational'] is None
    assert result['version']==2

def test_list_keeps_unknown_distinct_from_no(context):
    c,h,core,cid=context
    assert c.post('/cases',headers=h,json={**core,'rp_number':'SYNTH-NO','transnational':False}).status_code==200
    items={r['id']:r for r in c.get('/cases',headers=h).json()['items']}
    assert items[cid]['transnational'] is None
    assert next(r for r in items.values() if r['id']!=cid)['transnational'] is False

def test_correction_rejects_case_insensitive_duplicate_without_mutation(context):
    c,h,core,cid=context
    second=c.post('/cases',headers=h,json={**core,'rp_number':'SYNTH-SECOND'}).json()['id']
    response=c.patch(f'/cases/{second}?reason=Correction%20synthétique&expected_version=1',headers=h,json={**core,'rp_number':core['rp_number'].lower()})
    assert response.status_code==409
    result=c.get(f'/cases/{second}',headers=h).json()
    assert result['version']==1 and result['rp_number']=='SYNTH-SECOND'

def test_typed_import_unknown_transnational_confirms(context):
    c,h,core,_=context
    payload={'synthetic':True,'core':{**core,'rp_number':'SYNTH-IMPORT'},'record':{'transnational_state':'undetermined'}}
    preview=c.post('/registry/imports/preview',headers=h,files={'file':('synthetic.jsonl',json.dumps(payload).encode())}).json()
    assert preview['can_confirm'] is True
    result=c.post('/registry/imports/'+preview['preview_id']+'/confirm',headers=h)
    assert result.status_code==200 and result.json()['imported_rows']==1
    cid=next(r['id'] for r in c.get('/cases',headers=h).json()['items'] if r['rp_number']=='SYNTH-IMPORT')
    assert c.get(f'/cases/{cid}',headers=h).json()['transnational'] is None

def test_technical_profile_cannot_claim_ineffective_restrictions(context):
    c,h,_,_=context
    uid=c.post('/superadmin/users',headers=h,json={'username':'audit_tech','password':'Synthetic-Audit-2026!','profile_id':'technical','reason':'Test synthétique','active':True,'super_admin':False}).json()['id']
    response=c.put(f'/users/{uid}/data-profile',headers=h,json={'profile':'technical','cabinets':['Cabinet fictif']})
    assert response.status_code==422

@pytest.mark.parametrize('content',[
    b'rp_number,rp_number,date_rp\nSYNTH-A,SYNTH-B,2026-01-01\n',
    b'rp_number,date_rp\nSYNTH-A,2026-01-01,unmapped\n',
    b'rp_number,date_rp\n"unterminated,2026-01-01\n',
])
def test_legacy_csv_rejects_silent_loss(context,content):
    c,h,_,_=context
    assert c.post('/imports/preview',headers=h,files={'file':('synthetic.csv',content)}).status_code in (400,413,422)

def test_standard_xlsx_audiences_sheet_uses_first_row(context):
    from io import BytesIO
    from openpyxl import Workbook
    c,h,core,_=context
    workbook=Workbook();sheet=workbook.active;sheet.title='AUDIENCES PENALES'
    sheet.append(list(core));sheet.append([('SYNTH-XLSX' if k=='rp_number' else False if k=='transnational' else v) for k,v in core.items()])
    out=BytesIO();workbook.save(out)
    response=c.post('/imports/preview',headers=h,files={'file':('synthetic.xlsx',out.getvalue())})
    assert response.status_code==200
    assert response.json()['can_confirm'] is True
    assert response.json()['valid_rows']==1
