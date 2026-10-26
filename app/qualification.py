"""Readiness evidence, never legal approval or a claim that a scheduler is running."""
import io,json,uuid
from collections import Counter
from datetime import datetime,timezone
from fastapi import Depends,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,ConfigDict,Field
from .registry_models import quality
from .registry import read_record
from .qualification_data import EXPECTED,bundle
SCHEMA='''
CREATE TABLE IF NOT EXISTS operation_evidence(id TEXT PRIMARY KEY,kind TEXT NOT NULL,result TEXT NOT NULL,evidence TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,archive_sha256 TEXT,target_name TEXT,table_counts TEXT);
'''
RULES=[
 {'code':'dossier_key','subject':'Identité du dossier','implemented':'Unicité RP + année ; doublon refusé sans écrasement','pending':'Clé comprenant la juridiction à confirmer avant généralisation','test':'tests/test_registry.py, tests/test_platform.py'},
 {'code':'counting','subject':'Dossiers, personnes et infractions','implemented':'Dossiers distincts ; PP/PM séparés ; infractions et résultats individuels reliés','pending':'Unités et exclusions à approuver par le greffe','test':'tests/test_registry.py, tests/test_qualification.py'},
 {'code':'decisions','subject':'Décisions mixtes et successives','implemented':'Résultats reliés à la personne et à l’infraction ; décisions au fond distinguées','pending':'Traitement statistique des recours et décisions définitives à approuver','test':'tests/test_compliance.py, tests/test_legal.py'},
 {'code':'money','subject':'Mesures et montants','implemented':'Décimales exactes, nature et devise séparées, inconnu distinct de zéro','pending':'Bases de valorisation, comparabilité et exécution à approuver','test':'tests/test_registry.py, tests/test_followup.py'},
 {'code':'dates','subject':'Dates, stocks et délais','implemented':'Date de réception distincte de décision ; aucune date source manquante inventée','pending':'Définition de la clôture judiciaire et délais légaux non approuvés','test':'tests/test_dashboard.py, tests/test_compliance.py'},
 {'code':'access','subject':'Habilitations et exports','implemented':'Contrôles serveur par rôle et périmètre ; sessions révoquées après changement','pending':'Matrice nominative et séparation des responsabilités à signer','test':'tests/test_superadmin.py, tests/test_followup.py'},
 {'code':'imports','subject':'Import et reversement','implemented':'Aperçu, anomalies, source conservée ; annulation limitée aux brouillons intacts','pending':'Recette utilisateur des lots et corrections à consigner','test':'tests/test_transfer.py, tests/test_registry.py'}]
class Evidence(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 kind:str
 result:str
 evidence:str=Field(min_length=10,max_length=4000)
 archive_sha256:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
 target_name:str|None=Field(default=None,max_length=100)
 table_counts:dict[str,int]|None=Field(default=None,max_length=200)

def install(app,db,audit,utcnow,require_roles):
 with db() as c:c.executescript(SCHEMA)
 @app.get('/qualification')
 def readiness(u=Depends(require_roles('admin','supervisor'))):
  with db() as c:
   counts=Counter();total=0
   for row in c.execute('SELECT * FROM cases').fetchall():
    case=dict(row);issues=quality(read_record(c,case),case);total+=bool(issues)
    counts.update(i['code'] for i in issues)
   references=[dict(r) for r in c.execute('SELECT id,filename,sha256 FROM reference_documents').fetchall() if any(w in r['filename'].lower() for w in ('tdr','charte'))]
   history=[dict(r) for r in c.execute('SELECT e.*,u.username FROM operation_evidence e JOIN users u ON u.id=e.created_by ORDER BY e.created_at DESC,e.id DESC LIMIT 100').fetchall()]
  latest={}
  for e in history:
   if e['table_counts']:e['table_counts']=json.loads(e['table_counts'])
   latest.setdefault(e['kind'],e)
  backup=latest.get('restore');age=None
  if backup:age=round((datetime.now(timezone.utc)-datetime.fromisoformat(backup['created_at'])).total_seconds()/3600,2)
  return {'officially_approved':False,'references':references,'reference_status':'à examiner' if references else 'originaux non disponibles','rules':RULES,'quality':{'cases_with_issues':total,'codes':dict(counts)},'fixture':EXPECTED,'operations':{'latest':latest,'backup_evidence_age_hours':age,'backup_attention':not backup or backup['result']!='passed' or age>24,'automatic_production_backup_enabled':False,'scheduler_note':'Planificateur externe à configurer et à vérifier ; les tests CI programmés ne sauvegardent pas la production.'},'history':history,'limits':['TDR et charte originaux nécessaires au rapprochement contractuel.','Essais synthétiques et observations ne valent pas réception institutionnelle.','Les dates absentes du classeur historique restent à vérifier sur les pièces source.']}
 @app.post('/qualification/evidence')
 def evidence(x:Evidence,u=Depends(require_roles('admin'))):
  if x.kind not in ('restore','backup_schedule','retention','security_review','training','incident_exercise','profile_acceptance'):raise HTTPException(422,'Contrôle inconnu.')
  if x.result not in ('passed','failed','pending'):raise HTTPException(422,'Résultat inconnu.')
  if x.kind=='restore' and x.result=='passed' and (not x.archive_sha256 or not x.target_name or not x.table_counts):raise HTTPException(422,'Empreinte, cible isolée et comptages comparés requis pour une restauration déclarée réussie.')
  if x.table_counts and any(not isinstance(n,int) or n<0 for n in x.table_counts.values()):raise HTTPException(422,'Comptages invalides.')
  ident=uuid.uuid4().hex
  with db(write=True) as c:
   c.execute('INSERT INTO operation_evidence VALUES (?,?,?,?,?,?,?,?,?)',(ident,x.kind,x.result,x.evidence,u['id'],datetime.now(timezone.utc).isoformat(timespec='microseconds'),x.archive_sha256,x.target_name,json.dumps(x.table_counts) if x.table_counts else None));audit(c,u['id'],'record','operation_evidence',ident,x.model_dump())
  return {'id':ident,'officially_approved':False,'evidence_type':'déclaration documentée, non certification automatique'}
 @app.get('/qualification/dataset.zip')
 def dataset(u=Depends(require_roles('admin','supervisor'))):
  return StreamingResponse(io.BytesIO(bundle()),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="SISAJ_recette_v2_1500.zip"'})
 @app.get('/qualification/export.json')
 def export(u=Depends(require_roles('admin','supervisor'))):
  data=readiness(u)
  with db(write=True) as c:audit(c,u['id'],'export','qualification',detail={'officially_approved':False})
  return StreamingResponse(io.BytesIO(json.dumps(data,ensure_ascii=False,indent=2).encode()),media_type='application/json',headers={'Content-Disposition':'attachment; filename="SISAJ_validation_progressive.json"'})
