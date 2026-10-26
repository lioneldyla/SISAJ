import csv,io
from fastapi.testclient import TestClient
from app.main import app,db
from tests.test_dashboard import context,case
from tests.test_compliance import account

def entry(version=2,**kw):return {'kind':'deadline','event_date':'2026-03-01','due_date':'2026-03-10','status':'pending','source_reference':'PIECE-TEST','description':'Échéance fictive à vérifier','reason':'Recette du suivi procédural','expected_version':version,**kw}
def test_append_only_corrections_do_not_change_judicial_outcomes():
 with TestClient(app) as c:
  h=context(c);cid=case(c,h,'SYNTH-A','A');before=c.get('/dashboard/analysis',headers=h).json()['cards']
  r=c.post(f'/cases/{cid}/followup',headers=h,json=entry());assert r.status_code==200,r.text;ident=r.json()['id']
  assert c.post(f'/cases/{cid}/followup',headers=h,json=entry()).status_code==409
  assert c.get('/followup?as_of=2026-03-11',headers=h).json()['items'][0]['attention']=='à examiner'
  r=c.post(f'/cases/{cid}/followup',headers=h,json=entry(3,supersedes=ident,status='cancelled'));assert r.status_code==200,r.text
  records=c.get(f'/cases/{cid}/followup',headers=h).json()['items'];assert len(records)==2 and sum(r['superseded'] for r in records)==1
  assert c.get('/followup?status=pending',headers=h).json()['total']==0
  assert c.post(f'/cases/{cid}/followup',headers=h,json=entry(4,supersedes=ident)).status_code==409
  after=c.get('/dashboard/analysis',headers=h).json()['cards']
  for key in ['judged','seizure','confiscation','delay']:
   assert next(v['value'] for v in before if v['key']==key)==next(v['value'] for v in after if v['key']==key)
  assert next(v for v in after if v['key']=='stock')['available'] is False

def test_followup_scopes_and_exports_fail_closed():
 with TestClient(app) as c:
  h=context(c);a=case(c,h,'SYNTH-A','A');b=case(c,h,'SYNTH-B','B')
  assert c.post(f'/cases/{a}/followup',headers=h,json=entry()).status_code==200
  assert c.post(f'/cases/{b}/followup',headers=h,json=entry(description='=Confidentiel cabinet B')).status_code==200
  _,manager=account(c,h,'manager_follow',profile='cabinet',cabinets=['A'])
  assert c.get('/followup',headers=manager).json()['total']==1
  assert c.get(f'/cases/{b}/followup',headers=manager).status_code==404
  assert c.post(f'/cases/{b}/followup',headers=manager,json=entry(3)).status_code==404
  export=c.get('/followup/export.csv',headers=manager);assert export.status_code==200 and 'SYNTH-B' not in export.text
  _,clerk=account(c,h,'clerk_follow',role='collector',profile='clerk',cabinets=['A'])
  assert c.get('/followup/export.csv',headers=clerk).status_code==403
  _,direction=account(c,h,'reader_follow',profile='direction')
  assert c.post(f'/cases/{a}/followup',headers=direction,json=entry(3)).status_code==403
  assert c.get('/qualification',headers=manager).status_code==403

def test_source_links_dates_and_execution_remain_explicit():
 with TestClient(app) as c:
  h=context(c);cid=case(c,h,'SYNTH-A','A')
  for change in [{'due_date':None},{'event_date':'2025-12-01'},{'due_date':'2026-01-01'},{'kind':'appeal','decision_reference':'ABSENT'},{'kind':'execution','measure_reference':'ABSENT'},{'responsible_id':99999}]:
   assert c.post(f'/cases/{cid}/followup',headers=h,json=entry(**change)).status_code==422,change
  assert c.post(f'/cases/{cid}/followup',headers=h,json=entry(kind='appeal',decision_reference='D1')).status_code==200
  r=c.get(f'/cases/{cid}/register',headers=h).json();record=r['record'];record['measures'].append({'reference':'CONF1','kind':'confiscation','measure_date':'2026-02-01','object_kind':'cash','amount':{'state':'known','value':'10.00','currency':'XOF'}})
  assert c.put(f'/cases/{cid}/register',headers=h,json={'record':record,'expected_version':3,'reason':'Ajouter confiscation fictive'}).status_code==200
  assert c.post(f'/cases/{cid}/followup',headers=h,json=entry(4,kind='execution',measure_reference='CONF1',amount={'state':'known','value':'5.00','currency':'EUR'})).status_code==422
  ok=c.post(f'/cases/{cid}/followup',headers=h,json=entry(4,kind='execution',measure_reference='CONF1',amount={'state':'known','value':'5.00','currency':'XOF'}));assert ok.status_code==200,ok.text
  assert c.get(f'/cases/{cid}/register',headers=h).json()['record']['measures'][-1]['amount']['value']=='10.00'
