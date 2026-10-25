import csv,io
from fastapi.testclient import TestClient
from app.main import app,db
from tests.test_registry import complete

def context(c):
    p='Synthetic-Dashboard-2026!';c.post('/auth/bootstrap',json={'username':'dash_admin','password':p})
    return {'Authorization':'Bearer '+c.post('/auth/login',json={'username':'dash_admin','password':p}).json()['access_token']}
def case(c,h,rp,cabinet,received='2026-01-01'):
    cid=c.post('/cases',headers=h,json={'rp_number':rp,'rp_year':2026,'date_rp':received,'provenance':'Fictif','category':'Catégorie fictive','transnational':False}).json()['id']
    r=complete();r['procedure']['cabinet']=cabinet
    assert c.put(f'/cases/{cid}/register',headers=h,json={'expected_version':1,'record':r,'reason':'Fixture dashboard complète'}).status_code==200
    return cid
def test_cards_drilldown_filters_and_export_share_population():
    with TestClient(app) as c:
        h=context(c);a=case(c,h,'SYNTH-A','Cabinet A');case(c,h,'SYNTH-B','Cabinet B')
        url='/dashboard/analysis?cabinet=Cabinet%20A&date_basis=decision&start=2026-02-01&end=2026-02-28'
        d=c.get(url,headers=h).json();assert d['cohort_size']==1
        assert d['rows'][0]['id']==a
        cards={x['key']:x for x in d['cards']};assert cards['received']['value']==0 and cards['judged']['value']==1
        assert cards['stock']['value'] is None and cards['stock']['available'] is False
        assert cards['persons']['value']==2
        assert d['persons']['physical']==1 and d['persons']['legal']==1
        assert d['results']==[{'key':'mixed','count':1,'unit':'décisions'}]
        p=c.get(url+'&metric=judged',headers=h).json();assert p['total']==1 and p['rows'][0]['id']==a
        p=c.get(url+'&metric=received',headers=h).json();assert p['total']==0
        export=c.get(url.replace('/analysis','/export.csv')+'&metric=judged',headers=h)
        assert export.status_code==200 and 'SYNTH-A' in export.text and 'SYNTH-B' not in export.text
        assert 'FCFA' in export.text and 'date_basis' in export.text
        assert c.get('/dashboard/analysis?date_basis=invalid',headers=h).status_code==422
        assert c.get('/dashboard/analysis?start=2026-12-01&end=2026-01-01',headers=h).status_code==422

def test_scoped_profile_is_enforced_on_cards_details_lists_and_exports():
    with TestClient(app) as c:
        h=context(c);a=case(c,h,'SYNTH-A','Cabinet A');b=case(c,h,'SYNTH-B','Cabinet B')
        p='Synthetic-Supervisor-2026!'
        r=c.post('/users',headers=h,json={'username':'cabinet_manager','password':p,'role':'supervisor'});assert r.status_code==200
        with db() as con:uid=con.execute("SELECT id FROM users WHERE username='cabinet_manager'").fetchone()['id']
        assert c.put(f'/users/{uid}/data-profile',headers=h,json={'profile':'cabinet','cabinets':['Cabinet A']}).status_code==200
        uh={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'cabinet_manager','password':p}).json()['access_token']}
        assert c.get('/dashboard/analysis',headers=uh).json()['cohort_size']==1
        assert c.get('/cases',headers=uh).json()['total']==1
        assert c.get(f'/cases/{a}',headers=uh).status_code==200
        assert c.get(f'/cases/{b}',headers=uh).status_code==404
        assert c.get(f'/cases/{b}/register',headers=uh).status_code==404
        assert c.get(f'/cases/{b}/legal',headers=uh).status_code==404
        core={'rp_number':'SYNTH-B','rp_year':2026,'date_rp':'2026-01-01','provenance':'Fictif','category':'Fictif','transnational':False}
        assert c.post(f'/cases/{b}/corrections',headers=uh,json={'case':core,'reason':'Correction hors périmètre','expected_version':2}).status_code==404
        record=complete();record['procedure']['cabinet']='Cabinet B'
        assert c.put(f'/cases/{a}/register',headers=uh,json={'record':record,'reason':'Déplacement hors périmètre','expected_version':2}).status_code==403
        ex=c.get('/dashboard/export.csv',headers=uh);assert 'SYNTH-A' in ex.text and 'SYNTH-B' not in ex.text
        assert c.get('/registry/records.xlsx',headers=uh).status_code==403
        assert c.get('/registry/reports/pdf',headers=uh).status_code==403
        assert c.get('/registry/documents',headers=uh).status_code==403
        assert c.put(f'/users/{uid}/data-profile',headers=uh,json={'profile':'technical'}).status_code==403
