"""Deterministic technical fixtures; no foreign categories or official rules inferred."""
import csv,io,json,zipfile
from copy import deepcopy
from datetime import date,timedelta
PATHS=['attente_orientation','classement','transmission','non_lieu_total','non_lieu_partiel','saisine_jugement','decision_mixte','relaxe','audience_renvoyee','instruction_ouverte']
EXPECTED={'dossiers':1500,'personnes':3000,'personnes_physiques':1500,'personnes_morales':1500,'infractions':3000,'decisions':600,'mesures':2400,'decision_mixte':150,'saisies_xof':'15000.00','confiscations_xof':'1800.00','amendes_xof':'450.00','delai_median_jours':40,'anomalies_attendues':0,'parcours':{p:150 for p in PATHS},'officially_approved':False}
def items():
 for n in range(1500):
  k=n%10;received=date(2024,1,1)+timedelta(days=n%365);d=lambda x:(received+timedelta(days=x)).isoformat()
  rp=f'RECETTE-V2-{n+1:05d}'
  core={'rp_number':rp,'rp_year':received.year,'date_rp':d(0),'provenance':'Unité fictive de recette','category':'Qualification fictive de recette','transnational':n%3==0,'person_physical_count':1,'person_legal_count':1}
  procedure={'cabinet_state':'known','cabinet':'Cabinet de recette '+str(n%5+1),'orientation':'pending' if k==0 else 'dismissal' if k==1 else 'transfer' if k==2 else 'trial_referral' if k==5 else 'investigation','observations':'Données intégralement fictives. Convention de scénario : '+PATHS[k]}
  if k!=0:procedure['orientation_date']=d(2)
  if k in (3,4,6,7):procedure.update(closure_date=d(20),closure_kind='total_dismissal' if k==3 else 'partial_dismissal' if k==4 else 'referral')
  people=[{'reference':'P1','kind':'physical','role':'defendant','display_name':'Personne fictive '+str(n+1),'profession':'private_employee','legal_form':'not_applicable'}, {'reference':'P2','kind':'legal','role':'defendant','display_name':'Société fictive '+str(n+1),'activity':'services','legal_form':'sarl'}]
  offences=[{'reference':f'I{i}','parquet_label':f'Qualification fictive {i}','offence_group':'other','offence_group_other':'Catégorie de recette sans homologation','amount_basis':'alleged_damage','amount':{'state':'known','value':str(i*100),'currency':'XOF'}} for i in (1,2)]
  decisions=[];measures=[{'reference':'M1','kind':'seizure','measure_date':d(5),'object_kind':'cash','valuation_basis':'actual','amount':{'state':'known','value':'10.00','currency':'XOF'}}]
  if k in (4,5,6,7):
   result='mixed' if k==6 else 'acquittal' if k==7 else 'conviction';day=30 if k==5 else 40
   outcomes=[{'person_reference':p,'offence_reference':o,'result':'acquittal' if k==7 or (k==6 and p=='P2') else 'conviction'} for p in ('P1','P2') for o in ('I1','I2')]
   decisions=[{'reference':'D1','number':rp+'-DEC','decision_date':d(day),'nature':'merits','result':result,'outcomes':outcomes}]
   if k!=7:
    for ref,kind,value in [('M2','confiscation','4.00'),('M3','fine','1.00')]:measures.append({'reference':ref,'kind':kind,'decision_reference':'D1','measure_date':d(day),'object_kind':'cash' if kind=='confiscation' else 'not_applicable','valuation_basis':'actual','amount':{'state':'known','value':value,'currency':'XOF'}})
  hearings=[{'reference':'A1','planned_date':d(25),'held_date':d(25),'status':'adjourned','next_date':d(50),'reason':'Renvoi fictif documenté'}] if k==8 else []
  yield {'synthetic':True,'fixture_id':'qualification-v2','core':core,'record':{'ri_state':'not_applicable','count_basis':'enumerated','transnational_state':'yes' if core['transnational'] else 'no','procedure':procedure,'people':people,'offences':offences,'decisions':decisions,'measures':measures,'hearings':hearings}}
def anomalies():
 rows=list(items());values=[deepcopy(rows[0]),deepcopy(rows[0])]
 for change in ('date','rp','amount','orphan','chronology','synthetic'):
  x=deepcopy(rows[5]);x['core']['rp_number']='ANOMALIE-'+change
  if change=='date':x['core']['date_rp']='2026-02-30'
  elif change=='rp':x['core']['rp_number']=''
  elif change=='amount':x['record']['measures'][0]['amount']['value']='-10.00'
  elif change=='orphan':x['record']['decisions'][0]['outcomes'][0]['person_reference']='ABSENT'
  elif change=='chronology':x['record']['procedure']['orientation_date']='1900-01-01'
  elif change=='synthetic':x['synthetic']=False
  values.append(x)
 return values
def bundle():
 rows=list(items());buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('registres_recette_v2.jsonl','\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n')
  z.writestr('anomalies_a_refuser.jsonl','\n'.join(json.dumps(r,ensure_ascii=False) for r in anomalies())+'\n')
  z.writestr('attendus.json',json.dumps(EXPECTED,ensure_ascii=False,indent=2))
  table=io.StringIO();w=csv.writer(table);w.writerow(['rp_number','rp_year','date_rp','provenance','category','transnational','person_physical_count','person_legal_count'])
  for r in rows:w.writerow([r['core'][k] for k in ('rp_number','rp_year','date_rp','provenance','category','transnational','person_physical_count','person_legal_count')])
  z.writestr('dossiers_techniques.csv',table.getvalue())
  z.writestr('NOTICE.txt','RECETTE FICTIVE V2. Importer le JSONL pour le registre complet. Le CSV ne contient que les champs de base. Dix parcours équilibrés de 150 dossiers. Dates et montants sont des conventions de fixture, sans portée juridique. Ne remplace pas le classeur historique : références nouvelles RECETTE-V2. Importer en base isolée. Ne pas considérer les résultats comme une réception du greffe.')
 return buf.getvalue()
