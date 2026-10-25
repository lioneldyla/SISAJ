from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def bootstrap_and_login():
    r=client.post('/auth/bootstrap',headers={'X-SISA-Bootstrap-Key':'Synthetic-Bootstrap-Only-2026!'},json={'username':'admin1','password':'Correct-Horse-Battery-2026!'})
    assert r.status_code==200, r.text
    r=client.post('/auth/login',json={'username':'admin1','password':'Correct-Horse-Battery-2026!'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_health_no_cloud_or_external_ai():
    r=client.get('/health'); assert r.status_code==200
    assert r.json()['cloud_sync']=='disabled' and r.json()['external_ai']=='disabled'

def test_bootstrap_auth_rbac_and_workflow():
    h=bootstrap_and_login()
    assert client.post('/auth/bootstrap',headers={'X-SISA-Bootstrap-Key':'Synthetic-Bootstrap-Only-2026!'},json={'username':'second','password':'Correct-Horse-Battery-2026!'}).status_code==409
    assert client.post('/users',headers=h,json={'username':'agent1','password':'Agent-Strong-Password-2026!','role':'collector'}).status_code==200
    assert client.post('/users',headers=h,json={'username':'chef1','password':'Supervisor-Strong-2026!','role':'supervisor'}).status_code==200
    data={'rp_number':'RP-TEST-001','rp_year':2026,'date_rp':'2026-10-01','ri_number':'RI-TEST-001','provenance':'OPJ fictif','transnational':False,'category':'corruption fictive','person_physical_count':1,'person_legal_count':0}
    r=client.post('/cases',headers=h,json=data); assert r.status_code==200, r.text; cid=r.json()['id']
    assert client.post(f'/cases/{cid}/submit',headers=h).status_code==200
    # supervisor validation is required; admin also permitted
    assert client.post(f'/cases/{cid}/validate',headers=h).status_code==200
    stats=client.get('/stats',headers=h).json(); assert stats['received_cases']==1
    assert client.get('/cases',headers=h).json()['total']==1
    assert client.get('/audit',headers=h).status_code==200

def test_duplicate_and_year_validation():
    h=bootstrap_and_login()
    data={'rp_number':'RP-DUP','rp_year':2026,'date_rp':'2026-03-02','provenance':'OPJ test','transnational':False,'category':'cat test'}
    assert client.post('/cases',headers=h,json=data).status_code==200
    assert client.post('/cases',headers=h,json=data).status_code==409
    bad={**data,'rp_number':'RP-BAD','date_rp':'2025-03-02'}
    assert client.post('/cases',headers=h,json=bad).status_code==422

def test_import_canonical_csv_confirm_and_duplicate_rejection():
    h=bootstrap_and_login()
    csvdata='rp_number,rp_year,date_rp,provenance,transnational,category,ri_number,person_physical_count,person_legal_count\nRP-IMP-1,2026,2026-01-10,OPJ fictif,Non,corruption fictive,RI-1,2,0\n'
    r=client.post('/imports/preview',headers=h,files={'file':('test.csv',csvdata.encode(),'text/csv')}); assert r.status_code==200,r.text
    payload=r.json(); assert payload['can_confirm'] is True
    r=client.post('/imports/'+payload['preview_id']+'/confirm',headers=h); assert r.status_code==200,r.text
    assert r.json()['imported_rows']==1
    r=client.post('/imports/preview',headers=h,files={'file':('test.csv',csvdata.encode(),'text/csv')}); assert r.status_code==200
    assert r.json()['can_confirm'] is False

def test_backup_and_export_supervisor_only():
    h=bootstrap_and_login()
    assert client.post('/admin/backup',headers=h).status_code==200
    assert client.get('/exports/cases.csv',headers=h).status_code==200

def test_local_anomaly_rules_are_not_misrepresented_as_ml():
    h=bootstrap_and_login(); r=client.get('/intelligence/anomalies',headers=h)
    assert r.status_code==200 and r.json()['is_machine_learning'] is False

def test_no_auth_rejected():
    assert client.get('/cases').status_code==401

def test_ppef_source_workbook_mapping_synthetic():
    from openpyxl import Workbook
    from io import BytesIO
    h=bootstrap_and_login(); wb=Workbook(); ws=wb.active; ws.title='AUDIENCES PENALES'
    ws.append(['SUIVI DE DEMONSTRATION']); ws.append(['Juridiction fictive'])
    ws.append(['N° RP','Date RP','Unité (OPJ) de Provenance','Dossier à caractère transnational (oui/non)','Infraction retenue par le Parquet','N° RI','Nombre prévenus (PP)','Nombre prévenus (PM)'])
    ws.append(['RP-XLSX-001','2026-05-03','OPJ fictif','Non','qualification fictive','RI-XLSX-001',2,1])
    b=BytesIO(); wb.save(b)
    r=client.post('/imports/preview',headers=h,files={'file':('synthetic_ppef.xlsx',b.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert r.status_code==200,r.text
    data=r.json(); assert data['source_sheet']=='AUDIENCES PENALES' and data['can_confirm'] is True
    assert data['sample'][0]['rp_year']==2026 and data['sample'][0]['transnational']==0
    done=client.post('/imports/'+data['preview_id']+'/confirm',headers=h); assert done.status_code==200,done.text

