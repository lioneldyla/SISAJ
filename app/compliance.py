"""Evidence of tests, never an assertion of institutional/legal certification."""
import csv
import hashlib
import io
import json
import uuid
from datetime import date,datetime,timezone
from typing import Literal
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from .dashboard import analyze
from .access import permitted

SCHEMA = '''
CREATE TABLE IF NOT EXISTS business_reviews(id TEXT PRIMARY KEY, scenario TEXT NOT NULL, result TEXT NOT NULL, expected TEXT NOT NULL, observed TEXT NOT NULL, evidence TEXT NOT NULL, reviewer INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analysis_snapshots(id TEXT PRIMARY KEY, title TEXT NOT NULL, filters TEXT NOT NULL, payload TEXT NOT NULL, sha256 TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
'''
SCENARIOS = [
 ('duplicate','Doublon RP / année','Refus sans écrasement ; clé institutionnelle à confirmer'),
 ('multi_offence','Dossier multi-infractions','Un dossier distinct ; plusieurs infractions sans multiplication des effectifs'),
 ('mixed_decision','Décision mixte','Condamnation et relaxe reliées aux bonnes personnes et infractions'),
 ('multiple_measures','Mesures multiples','Montants exacts par nature, devise et base ; zéro distinct d’inconnu'),
 ('repeated_import','Import répété','Aucun dossier recréé ou écrasé ; source conservée'),
 ('permissions','Habilitations','Autres cabinets refusés sur fiches, statistiques et exports'),
 ('reports','Rapports et indicateurs','Filtres, unités, population et dossiers justificatifs concordants'),
 ('restore','Sauvegarde et restauration','Tables, séquences et données comparées sur cible isolée'),
 ('hearings','Audiences et renvois','Dates et motifs conservés sans déduire une audience tenue'),
 ('workflow','Circuit de validation','Retour motivé, contrôle préalable et correction historisée'),
 ('alternative_paths','Autres parcours procéduraux','Classement, non-lieu et affaires sans décision représentés sans inventer une terminaison')
]

class Review(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 scenario:str
 result:Literal['passed','failed','pending']
 expected:str=Field(min_length=10,max_length=3000)
 observed:str=Field(min_length=10,max_length=3000)
 evidence:str=Field(min_length=10,max_length=4000)

class Filters(BaseModel):
 model_config=ConfigDict(extra='forbid')
 start:date|None=None
 end:date|None=None
 as_of:date|None=None
 date_basis:Literal['receipt','closure','hearing','decision']='receipt'
 cabinet:list[str]|None=Field(default=None,max_length=100)
 provenance:str|None=None
 category:str|None=None
 subtype:str|None=None
 party:str|None=None
 transnational:str|None=None
 status:str='all'
 jurisdiction:str|None=None
 waiting_days:int=Field(default=90,ge=1,le=3650)
 q:str|None=None
 metric:str|None=None
 sort:str='rp'
 direction:str='asc'

class Snapshot(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 title:str=Field(min_length=3,max_length=200)
 filters:Filters=Field(default_factory=Filters)

def install(app,db,audit,utcnow,user_from_token,require_roles,safe_cell):
 with db() as c:c.executescript(SCHEMA)

 @app.get('/compliance')
 def overview(u=Depends(require_roles('admin','supervisor'))):
  with db() as c:
   rows=c.execute('SELECT b.*,u.username FROM business_reviews b JOIN users u ON u.id=b.reviewer ORDER BY b.created_at DESC,b.id DESC').fetchall()
   latest={}
   for row in rows:latest.setdefault(row['scenario'],dict(row))
   documents=[dict(r) for r in c.execute('SELECT id,filename,sha256 FROM reference_documents').fetchall()]
   references=[d for d in documents if 'tdr' in d['filename'].lower() or 'charte' in d['filename'].lower()]
  return {'officially_approved':False,'dataset_kind':'synthetic','scope':'Recette technique et observations humaines ; ne vaut pas validation institutionnelle',
   'reference_status':'Documents à examiner et rapprocher des exigences' if references else 'TDR et charte originaux à joindre pour le rapprochement contractuel',
   'references':references,'scenarios':[{'code':k,'label':label,'expected':expected,'latest':latest.get(k)} for k,label,expected in SCENARIOS],
   'limits':['Le résultat concluant d’un test fictif ne certifie pas la validité métier du greffe.','Les règles de terminaison judiciaire, nomenclatures et responsabilités doivent être approuvées par les personnes habilitées.','La clé RP / année actuelle ne permet pas encore de généraliser aux juridictions partageant une référence.']}

 @app.post('/compliance/reviews')
 def record_review(x:Review,u=Depends(require_roles('admin','supervisor'))):
  if x.scenario not in {s[0] for s in SCENARIOS}:raise HTTPException(422,'Scénario inconnu')
  rid=str(uuid.uuid4());now=datetime.now(timezone.utc).isoformat(timespec='microseconds')
  with db(write=True) as c:
   c.execute('INSERT INTO business_reviews VALUES (?,?,?,?,?,?,?,?)',(rid,x.scenario,x.result,x.expected,x.observed,x.evidence,u['id'],now))
   audit(c,u['id'],'record','business_review',rid,{'scenario':x.scenario,'result':x.result,'dataset_kind':'synthetic','officially_approved':False})
  return {'id':rid,'recorded_at':now,'officially_approved':False}

 @app.get('/compliance/reviews')
 def history(u=Depends(require_roles('admin','supervisor'))):
  with db() as c:rows=c.execute('SELECT b.*,u.username FROM business_reviews b JOIN users u ON u.id=b.reviewer ORDER BY created_at DESC,id DESC LIMIT 500').fetchall()
  return {'items':[dict(r) for r in rows],'officially_approved':False}

 def load_snapshot(c,sid,u):
  row=c.execute('SELECT * FROM analysis_snapshots WHERE id=?',(sid,)).fetchone()
  if not row:raise HTTPException(404,'État figé introuvable')
  technical=u['role']=='admin' and (not u.get('data_profile') or u['data_profile']['profile']=='technical')
  if row['created_by']!=u['id'] and not technical:raise HTTPException(404,'État figé introuvable')
  if hashlib.sha256(row['payload'].encode()).hexdigest()!=row['sha256']:raise HTTPException(409,'Intégrité de l’état non vérifiée')
  data=json.loads(row['payload'])
  # A previous authorization never grants access after a reassignment or deletion.
  for cid in data['authorized_case_ids']:
   case=c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
   if not case or not permitted(c,dict(case),u):raise HTTPException(403,'Périmètre modifié ; état historique inaccessible')
  return dict(row),data

 @app.post('/dashboard/snapshots')
 def freeze(x:Snapshot,u=Depends(require_roles('admin','supervisor'))):
  sid=str(uuid.uuid4());now=utcnow()
  with db(write=True) as c:
   args=x.filters.model_dump();args.update(limit=2147483647,offset=0)
   data=analyze(c,u,**args)
   # Cards describe the cohort, even if the selected list metric narrows rows.
   cohort=analyze(c,u,**{**args,'metric':None}) if args['metric'] else data
   payload={'title':x.title,'created_at':now,'dataset_kind':'synthetic','officially_approved':False,'method_version':'dashboard-v0.7-provisional','authorized_case_ids':[r['id'] for r in cohort['rows']],'analysis':data}
   encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(encoded.encode()).hexdigest()
   c.execute('INSERT INTO analysis_snapshots VALUES (?,?,?,?,?,?,?)',(sid,x.title,json.dumps(data['filters'],ensure_ascii=False),encoded,digest,u['id'],now))
   audit(c,u['id'],'freeze','analysis_snapshot',sid,{'sha256':digest,'rows':data['total'],'dataset_kind':'synthetic'})
  return {'id':sid,'sha256':digest,'created_at':now,'rows':data['total'],'officially_approved':False}

 @app.get('/dashboard/snapshots')
 def snapshots(u=Depends(require_roles('admin','supervisor'))):
  items=[]
  with db() as c:
   for row in c.execute('SELECT id FROM analysis_snapshots WHERE created_by=? ORDER BY created_at DESC,id DESC LIMIT 100',(u['id'],)).fetchall():
    try:r,data=load_snapshot(c,row['id'],u)
    except HTTPException as e:
     if e.status_code in (403,404):continue
     raise
    items.append({k:r[k] for k in ('id','title','sha256','created_at')})
  return {'items':items}

 @app.get('/dashboard/snapshots/{sid}')
 def snapshot(sid:str,u=Depends(require_roles('admin','supervisor'))):
  with db() as c:r,data=load_snapshot(c,sid,u)
  return {'id':sid,'sha256':r['sha256'],'snapshot':data}

 @app.get('/dashboard/snapshots/{sid}/export/{format}')
 def export(sid:str,format:str,u=Depends(require_roles('admin','supervisor'))):
  if format not in ('json','csv'):raise HTTPException(404,'Format indisponible')
  with db(write=True) as c:
   r,data=load_snapshot(c,sid,u)
   audit(c,u['id'],'export','analysis_snapshot',sid,{'format':format,'sha256':r['sha256']})
  if format=='json':content=r['payload'];media='application/json'
  else:
   buf=io.StringIO();w=csv.writer(buf)
   w.writerow(['SISAJ / État figé',safe_cell(data['title'])]);w.writerow(['Données','Fictives / test ; méthode non approuvée']);w.writerow(['Date UTC',data['created_at']]);w.writerow(['SHA-256 du JSON de référence',r['sha256']]);w.writerow(['Filtres',safe_cell(json.dumps(data['analysis']['filters'],ensure_ascii=False))])
   w.writerow(['Indicateur','Valeur','Unité','Définition'])
   for card in data['analysis']['cards']:w.writerow([safe_cell(card['label']),card['value'] if card['available'] else 'Non calculable',card['unit'],safe_cell(card['definition'])])
   rows=data['analysis']['rows'];keys=list(rows[0]) if rows else ['id','rp'];w.writerow([]);w.writerow(keys)
   for row in rows:w.writerow([safe_cell(row.get(k)) for k in keys])
   content='\ufeff'+buf.getvalue();media='text/csv'
  return StreamingResponse(io.BytesIO(content.encode()),media_type=media,headers={'Content-Disposition':f'attachment; filename="etat_fige_{sid}.{format}"','X-SISA-SHA256':r['sha256']})
