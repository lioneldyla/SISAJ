"""Independent synthetic legal fixtures; expected counts are specified rather than copied from SQL."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app.main import app, db

PASSWORD='Synthetic-Legal-2026!'
@pytest.fixture
def setup():
    with TestClient(app) as c:
        assert c.post('/auth/bootstrap',json={'username':'legal_admin','password':PASSWORD}).status_code==200
        h={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'legal_admin','password':PASSWORD}).json()['access_token']}
        data=dict(rp_number='SYNTH-LEGAL-1',rp_year=2026,date_rp='2026-01-10',provenance='Fictif',category='Source fictive',transnational=False)
        cid=c.post('/cases',headers=h,json=data).json()['id']
        yield c,h,cid,data

def bundle(version=1):
    return {'expected_version':version,'reason':'Complément synthétique de recette','jurisdiction_code':None,
      'people':[{'reference':'P1','kind':'physical','role':'defendant','display_name':'Personne fictive A'},{'reference':'P2','kind':'legal','role':'defendant','display_name':'Société fictive B'}],
      'offences':[{'reference':'I1','code':'TEST-1','label':'Qualification fictive A'},{'reference':'I2','code':'TEST-2','label':'Qualification fictive B'}],
      'decisions':[{'reference':'D1','decision_date':'2026-02-01','on_merits':True,'outcomes':[{'person_reference':'P1','offence_reference':'I1','result':'conviction'},{'person_reference':'P2','offence_reference':'I2','result':'acquittal'}]},
       {'reference':'D2','decision_date':'2026-03-01','on_merits':True,'outcomes':[]},
       {'reference':'D3','decision_date':'2026-03-10','on_merits':False,'outcomes':[]}],
      'measures':[{'reference':'M1','decision_reference':'D1','kind':'fine','measure_date':'2026-02-01','amount':'0.10','currency':'XOF'},
       {'reference':'M2','kind':'fine','measure_date':'2026-02-02','amount':'0.20','currency':'XOF'},
       {'reference':'M3','kind':'fine','measure_date':'2026-02-03','amount':'100','currency':'EUR'},
       {'reference':'M4','kind':'seizure','measure_date':'2026-03-01','amount':None,'currency':None},
       {'reference':'M5','kind':'confiscation','measure_date':'2026-04-01','amount':'0','currency':'XOF'}]}

def validate(c,h,cid,version):
    assert c.post(f'/cases/{cid}/submit?expected_version={version}',headers=h).status_code==200
    assert c.post(f'/cases/{cid}/validate?expected_version={version+1}',headers=h).status_code==200

def test_independent_oracle_mixed_unknown_currency_period_and_exports(setup):
    c,h,cid,_=setup
    assert c.put(f'/cases/{cid}/legal',headers=h,json=bundle()).status_code==200
    assert c.get('/stats/legal',headers=h).json()['decisions']==0
    validate(c,h,cid,2)
    d=c.get('/stats/legal',headers=h).json()
    assert {k:d[k] for k in ('received_cases','judged_cases','decisions','merits_decisions','conviction_decisions','acquittal_decisions','mixed_decisions','unknown_outcome_decisions','unknown_amount_measures')}==dict(received_cases=1,judged_cases=1,decisions=3,merits_decisions=2,conviction_decisions=1,acquittal_decisions=1,mixed_decisions=1,unknown_outcome_decisions=1,unknown_amount_measures=1)
    assert d['amounts']==[{'kind':'confiscation','currency':'XOF','amount':'0.00'},{'kind':'fine','currency':'EUR','amount':'100.00'},{'kind':'fine','currency':'XOF','amount':'0.30'}]
    feb=c.get('/stats/legal?start=2026-02-01&end=2026-02-01',headers=h).json()
    assert (feb['received_cases'],feb['judged_cases'],feb['decisions'],feb['measures'])==(0,1,1,1)
    wb=load_workbook(BytesIO(c.get('/reports/legal.xlsx',headers=h).content))
    assert wb['Montants']['C4'].value=='0.30'
    assert dict(wb['Indicateurs'].values)['mixed_decisions']==1
    assert c.get('/reports/legal.pdf',headers=h).content.startswith(b'%PDF-')
    assert c.get('/stats/legal?start=2026-03-01&end=2026-01-01',headers=h).status_code==422

def test_jurisdiction_filters_and_legacy_preservation(setup):
    c,h,cid,original=setup
    assert c.post('/jurisdictions',headers=h,json={'code':'TEST-A','name':'Juridiction fictive A'}).status_code==200
    body=bundle();body['jurisdiction_code']='TEST-A'
    assert c.put(f'/cases/{cid}/legal',headers=h,json=body).status_code==200
    validate(c,h,cid,2)
    assert c.get('/stats/legal?jurisdiction=TEST-A',headers=h).json()['judged_cases']==1
    assert c.get('/stats/legal?jurisdiction=TEST-B',headers=h).json()['judged_cases']==0
    assert c.get('/stats?jurisdiction=TEST-B',headers=h).json()['received_cases']==0
    assert c.get(f'/cases/{cid}',headers=h).json()['category']==original['category']
    # Additive schema is idempotent and leaves source rows untouched.
    from app.legal import SCHEMA
    with db() as conn:
        before=[dict(r) for r in conn.execute('SELECT * FROM cases').fetchall()]
        conn.executescript(SCHEMA);conn.executescript(SCHEMA)
        assert [dict(r) for r in conn.execute('SELECT * FROM cases').fetchall()]==before

@pytest.mark.parametrize('change', ['unknown_person','duplicate','unknown_decision','bad_amount','no_currency','before_rp','victim_outcome'])
def test_invalid_legal_bundle_is_atomic(setup,change):
    c,h,cid,_=setup;b=bundle()
    if change=='unknown_person':b['decisions'][0]['outcomes'][0]['person_reference']='ABSENT'
    if change=='duplicate':b['people'].append(deepcopy(b['people'][0]))
    if change=='unknown_decision':b['measures'][0]['decision_reference']='ABSENT'
    if change=='bad_amount':b['measures'][0]['amount']='NaN'
    if change=='no_currency':b['measures'][0]['currency']=None
    if change=='before_rp':b['decisions'][0]['decision_date']='2025-01-01'
    if change=='victim_outcome':b['people'][0]['role']='victim'
    assert c.put(f'/cases/{cid}/legal',headers=h,json=b).status_code==422
    result=c.get(f'/cases/{cid}/legal',headers=h).json()
    assert result['version']==1 and result['people']==[]

def test_stale_editor_and_validated_record_are_protected(setup):
    c,h,cid,_=setup
    assert c.put(f'/cases/{cid}/legal',headers=h,json=bundle()).status_code==200
    assert c.put(f'/cases/{cid}/legal',headers=h,json=bundle()).status_code==409
    assert c.post(f'/cases/{cid}/submit?expected_version=1',headers=h).status_code==409
    validate(c,h,cid,2)
    assert c.put(f'/cases/{cid}/legal',headers=h,json=bundle(4)).status_code==409
    assert c.post(f'/cases/{cid}/timeline',headers=h,json={'event_type':'Fictif','expected_version':4}).status_code==409


def test_two_writers_have_one_winner_and_no_partial_children(setup):
    c,h,cid,_=setup
    def save(_):
        with TestClient(app) as other:
            return other.put(f'/cases/{cid}/legal',headers=h,json=bundle()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,range(2)))
    assert sorted(results)==[200,409]
    d=c.get(f'/cases/{cid}/legal',headers=h).json()
    assert d['version']==2 and len(d['people'])==2 and len(d['measures'])==5


def test_collector_cannot_validate_export_or_create_jurisdiction(setup):
    c,h,cid,_=setup
    assert c.post('/users',headers=h,json={'username':'legal_agent','password':PASSWORD,'role':'collector'}).status_code==200
    agent={'Authorization':'Bearer '+c.post('/auth/login',json={'username':'legal_agent','password':PASSWORD}).json()['access_token']}
    assert c.put(f'/cases/{cid}/legal',headers=agent,json=bundle()).status_code==200
    assert c.post(f'/cases/{cid}/submit?expected_version=2',headers=agent).status_code==200
    assert c.post(f'/cases/{cid}/validate?expected_version=3',headers=agent).status_code==403
    for route in ('/reports/legal.pdf','/reports/legal.xlsx'):
        assert c.get(route,headers=agent).status_code==403
    assert c.post('/jurisdictions',headers=agent,json={'code':'BAD','name':'Test'}).status_code==403


def test_transition_and_legacy_event_increment_version(setup):
    c,h,cid,data=setup
    assert c.post(f'/cases/{cid}/timeline',headers=h,json={'event_type':'Test','expected_version':1}).json()['version']==2
    assert c.post(f'/cases/{cid}/timeline',headers=h,json={'event_type':'Test','expected_version':1}).status_code==409
    assert c.post(f'/cases/{cid}/submit?expected_version=2',headers=h).json()['version']==3
    assert c.post(f'/cases/{cid}/return?expected_version=3',headers=h,json={'reason':'Retour pour contrôle'}).json()['version']==4
    assert c.post(f'/cases/{cid}/corrections',headers=h,json={'case':data,'expected_version':2,'reason':'Ancien écran'}).status_code==409


def test_changing_rp_date_cannot_invalidate_existing_legal_dates(setup):
    c,h,cid,data=setup
    assert c.put(f'/cases/{cid}/legal',headers=h,json=bundle()).status_code==200
    changed={**data,'date_rp':'2026-05-01'}
    assert c.post(f'/cases/{cid}/corrections',headers=h,json={'case':changed,'reason':'Date incompatible','expected_version':2}).status_code==422
    assert c.get(f'/cases/{cid}',headers=h).json()['date_rp']=='2026-01-10'


def test_event_and_validation_serialize_on_the_same_case(setup):
    c,h,cid,_=setup
    assert c.post(f'/cases/{cid}/submit?expected_version=1',headers=h).status_code==200
    def mutate(action):
        with TestClient(app) as other:
            if action=='event':return other.post(f'/cases/{cid}/timeline',headers=h,json={'event_type':'Audience fictive','expected_version':2}).status_code
            return other.post(f'/cases/{cid}/validate?expected_version=2',headers=h).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(mutate,['event','validate']))
    assert sorted(results)==[200,409]
    detail=c.get(f'/cases/{cid}',headers=h).json()
    assert detail['version']==3
    assert (detail['status']=='validated' and detail['events']==[]) or (detail['status']=='submitted' and len(detail['events'])==1)
