"""Source-backed procedural follow-up, separate from substantive judicial outcomes."""
import csv,io,json,uuid
from datetime import date,datetime,timezone
from typing import Literal
from fastapi import Depends,HTTPException,Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,ConfigDict,Field
from .registry_models import Money
from .registry import read_record
from .access import permitted,augment
SCHEMA='''
CREATE TABLE IF NOT EXISTS procedural_followup(id TEXT PRIMARY KEY,case_id INTEGER NOT NULL REFERENCES cases(id),kind TEXT NOT NULL,event_date TEXT NOT NULL,due_date TEXT,status TEXT NOT NULL,source_reference TEXT NOT NULL,description TEXT NOT NULL,decision_reference TEXT,measure_reference TEXT,amount TEXT,currency TEXT,responsible_id INTEGER REFERENCES users(id),supersedes TEXT UNIQUE,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,reason TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_followup_case ON procedural_followup(case_id);
'''
KINDS={'appeal':'Recours','deadline':'Échéance renseignée','execution':'Exécution d’une confiscation','action':'Action de suivi'}
class Entry(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 expected_version:int=Field(ge=1)
 kind:Literal['appeal','deadline','execution','action']
 event_date:date
 due_date:date|None=None
 status:Literal['pending','in_progress','completed','cancelled']='pending'
 source_reference:str=Field(min_length=2,max_length=250)
 description:str=Field(min_length=5,max_length=2000)
 decision_reference:str|None=Field(default=None,max_length=80)
 measure_reference:str|None=Field(default=None,max_length=80)
 amount:Money|None=None
 responsible_id:int|None=None
 supersedes:str|None=None
 reason:str=Field(min_length=5,max_length=1000)
def install(app,db,locked_case,audit,utcnow,user_from_token,require_roles,safe_cell):
 with db() as c:c.executescript(SCHEMA)
 def options(c,case):
  r=read_record(c,case)
  users=[]
  for row in c.execute('SELECT id,username,role FROM users WHERE active=1 ORDER BY username').fetchall():
   candidate=augment(c,dict(row))
   if permitted(c,case,candidate):users.append({'id':row['id'],'username':row['username']})
  return {'decisions':[{'reference':d.reference,'number':d.number} for d in r.decisions], 'confiscations':[{'reference':m.reference,'description':m.description} for m in r.measures if m.kind=='confiscation'],'responsibles':users}
 @app.get('/cases/{cid}/followup')
 def dossier(cid:int,u=Depends(user_from_token)):
  with db() as c:
   case=dict(locked_case(c,cid));records=[dict(r) for r in c.execute('SELECT f.*,u.username FROM procedural_followup f JOIN users u ON u.id=f.created_by WHERE case_id=? ORDER BY created_at,id',(cid,)).fetchall()]
   old={r['supersedes'] for r in records if r['supersedes']}
   for r in records:r['superseded']=r['id'] in old
   return {'case_id':cid,'version':case['version'],'rp':case['rp_number'],'items':records,**options(c,case),'legal_deadlines_inferred':False}
 @app.post('/cases/{cid}/followup')
 def add(cid:int,x:Entry,u=Depends(require_roles('admin','collector','supervisor'))):
  with db(write=True) as c:
   case=dict(locked_case(c,cid,x.expected_version));r=read_record(c,case)
   if x.event_date<date.fromisoformat(case['date_rp']):raise HTTPException(422,'Date d’événement antérieure à la réception RP.')
   if x.due_date and x.due_date<x.event_date:raise HTTPException(422,'Échéance antérieure à l’événement.')
   if x.decision_reference and x.decision_reference not in {d.reference for d in r.decisions}:raise HTTPException(422,'Décision absente du dossier.')
   if x.kind=='appeal' and not x.decision_reference:raise HTTPException(422,'Rattacher le recours à une décision renseignée.')
   if x.kind=='deadline' and not x.due_date:raise HTTPException(422,'Date d’échéance obligatoire ; aucun délai légal n’est déduit.')
   if x.kind=='execution':
    measure=next((m for m in r.measures if m.reference==x.measure_reference and m.kind=='confiscation'),None)
    if not measure:raise HTTPException(422,'Rattacher l’exécution à une confiscation du dossier.')
    if measure.measure_date and x.event_date<measure.measure_date:raise HTTPException(422,'Exécution antérieure à la confiscation renseignée.')
    if x.amount and x.amount.state=='known' and x.amount.currency!=measure.amount.currency:raise HTTPException(422,'Devise différente de la confiscation renseignée.')
   elif x.measure_reference or x.amount:raise HTTPException(422,'Montant et mesure réservés au suivi d’exécution.')
   if x.responsible_id and x.responsible_id not in {v['id'] for v in options(c,case)['responsibles']}:raise HTTPException(422,'Responsable inactif ou hors du périmètre du dossier.')
   if x.supersedes:
    old=c.execute('SELECT case_id,kind FROM procedural_followup WHERE id=?',(x.supersedes,)).fetchone()
    if not old or old['case_id']!=cid or old['kind']!=x.kind:raise HTTPException(422,'Événement à corriger absent ou de nature différente.')
    if c.execute('SELECT id FROM procedural_followup WHERE supersedes=?',(x.supersedes,)).fetchone():raise HTTPException(409,'Événement déjà remplacé. Rechargez la fiche.')
   ident=uuid.uuid4().hex
   c.execute('INSERT INTO procedural_followup VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(ident,cid,x.kind,str(x.event_date),str(x.due_date) if x.due_date else None,x.status,x.source_reference,x.description,x.decision_reference,x.measure_reference,x.amount.value if x.amount else None,x.amount.currency if x.amount else None,x.responsible_id,x.supersedes,u['id'],datetime.now(timezone.utc).isoformat(timespec='microseconds'),x.reason))
   c.execute('UPDATE cases SET version=version+1,updated_at=?,updated_by=? WHERE id=?',(utcnow(),u['id'],cid));audit(c,u['id'],'record','procedural_followup',ident,x.model_dump(mode='json'))
  return {'id':ident,'version':x.expected_version+1,'status':'recorded','judicial_outcomes_modified':False}
 def listing(c,u,as_of,days,status,q):
  values=[]
  for row in c.execute('SELECT f.*,c.rp_number,c.date_rp,c.status case_status,r.username responsible FROM procedural_followup f JOIN cases c ON c.id=f.case_id LEFT JOIN users r ON r.id=f.responsible_id WHERE NOT EXISTS (SELECT 1 FROM procedural_followup newer WHERE newer.supersedes=f.id) ORDER BY f.due_date,f.event_date,f.id').fetchall():
   v=dict(row);case={'id':v['case_id']}
   if not permitted(c,case,u):continue
   if status!='all' and v['status']!=status:continue
   if q and q.casefold() not in (v['rp_number']+' '+v['description']).casefold():continue
   due=date.fromisoformat(v['due_date']) if v['due_date'] else None
   v['attention']='annulé' if v['status']=='cancelled' else 'terminé' if v['status']=='completed' else 'à examiner' if due and due<as_of else 'échéance proche' if due and (due-as_of).days<=days else 'suivi courant'
   values.append(v)
  # Include planned/adjourned hearings already recorded in the register.
  hearings=[]
  for row in c.execute('SELECT * FROM cases ORDER BY id').fetchall():
   case=dict(row)
   if not permitted(c,case,u):continue
   r=read_record(c,case)
   if r.procedure.first_hearing_planned and r.procedure.first_hearing_planned>=as_of and not any(h.planned_date==r.procedure.first_hearing_planned for h in r.hearings):
    hearings.append({'case_id':case['id'],'rp':case['rp_number'],'reference':'Première audience renseignée','date':str(r.procedure.first_hearing_planned),'cabinet':r.procedure.cabinet,'source':'Champ historique','status':'planned'})
   for h in r.hearings:
    planned=h.next_date if h.status=='adjourned' else h.planned_date if h.status=='planned' else None
    if planned and planned>=as_of and (not q or q.casefold() in case['rp_number'].casefold()):hearings.append({'case_id':case['id'],'rp':case['rp_number'],'reference':h.reference,'date':str(planned),'cabinet':r.procedure.cabinet,'source':h.source_reference,'status':h.status})
  return {'items':values,'hearings':sorted(hearings,key=lambda h:(h['date'],h['rp'])),'as_of':str(as_of),'attention_days':days,'legal_deadlines_inferred':False}
 @app.get('/followup')
 def overview(as_of:date|None=None,attention_days:int=Query(default=7,ge=1,le=365),status:Literal['all','pending','in_progress','completed','cancelled']='all',q:str=Query(default='',max_length=200),offset:int=Query(default=0,ge=0),limit:int=Query(default=30,ge=1,le=100),u=Depends(user_from_token)):
  with db() as c:data=listing(c,u,as_of or date.today(),attention_days,status,q)
  data['total']=len(data['items']);data['items']=data['items'][offset:offset+limit];data['hearings']=data['hearings'][:200]
  return data
 @app.get('/followup/export.csv')
 def export(as_of:date|None=None,attention_days:int=Query(default=7,ge=1,le=365),status:Literal['all','pending','in_progress','completed','cancelled']='all',q:str=Query(default='',max_length=200),u=Depends(require_roles('admin','supervisor'))):
  with db(write=True) as c:
   data=listing(c,u,as_of or date.today(),attention_days,status,q);audit(c,u['id'],'export','followup',detail={'as_of':data['as_of'],'status':status,'q':q,'rows':len(data['items'])})
  b=io.StringIO();w=csv.writer(b);w.writerow(['Suivi technique ; aucun délai légal calculé',data['as_of'],status,safe_cell(q)]);keys=['rp_number','kind','event_date','due_date','status','description','source_reference','responsible','attention'];w.writerow(keys)
  for v in data['items']:w.writerow([safe_cell(v.get(k)) for k in keys])
  w.writerow([]);w.writerow(['Audiences renseignées à venir','RP','Date','Référence','Source'])
  for h in data['hearings']:w.writerow(['Audience',safe_cell(h['rp']),h['date'],safe_cell(h['reference']),safe_cell(h['source'])])
  return StreamingResponse(io.BytesIO(('\ufeff'+b.getvalue()).encode()),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="sisaj_suivi.csv"'})
