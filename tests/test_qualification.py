from collections import Counter
from datetime import date
from decimal import Decimal
import io,json,zipfile
from fastapi.testclient import TestClient
from app.main import app
from app.qualification_data import items,EXPECTED,bundle,PATHS
from app.registry_models import Register,quality,validate_dates
from tests.test_dashboard import context,case

def test_all_1500_fixtures_are_typed_balanced_and_match_independent_expectations():
 rows=list(items());assert len(rows)==1500
 counts=Counter();money=Counter();refs=set()
 for x in rows:
  assert x['synthetic'];refs.add(x['core']['rp_number']);r=validate_dates(Register.model_validate(x['record']),date.fromisoformat(x['core']['date_rp']))
  assert not quality(r,x['core'])
  counts['people']+=len(r.people);counts['decisions']+=len(r.decisions);counts['measures']+=len(r.measures)
  counts[r.procedure.observations.split(': ')[-1]]+=1
  for m in r.measures:money[m.kind]+=Decimal(m.amount.value)
 assert len(refs)==1500 and counts['people']==3000 and counts['decisions']==600 and counts['measures']==2400
 assert all(counts[k]==150 for k in PATHS)
 assert money['seizure']==Decimal('15000') and money['confiscation']==Decimal('1800') and money['fine']==Decimal('450')
 with zipfile.ZipFile(io.BytesIO(bundle())) as z:assert json.loads(z.read('attendus.json'))==EXPECTED

def test_readiness_is_not_certification_and_evidence_is_append_only():
 with TestClient(app) as c:
  h=context(c);cid=case(c,h,'SYNTH-A','A');d=c.get('/qualification',headers=h).json()
  assert not d['officially_approved'] and not d['operations']['automatic_production_backup_enabled']
  assert d['operations']['backup_attention'] and d['reference_status']=='originaux non disponibles'
  body={'kind':'restore','result':'passed','evidence':'Essai de restauration synthétique'}
  assert c.post('/qualification/evidence',headers=h,json=body).status_code==422
  for result in ('pending','failed'):
   assert c.post('/qualification/evidence',headers=h,json={**body,'result':result}).status_code==200
  assert len(c.get('/qualification',headers=h).json()['history'])==2
  assert c.post('/qualification/evidence',headers=h,json={**body,'archive_sha256':'a'*64,'target_name':'isolated_restore','table_counts':{'cases':1}}).status_code==200
  d=c.get('/qualification',headers=h).json();assert not d['operations']['backup_attention'] and not d['officially_approved']
  assert len(d['history'])==3
  assert c.get('/qualification/dataset.zip',headers=h).content.startswith(b'PK')
