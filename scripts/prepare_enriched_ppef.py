"""Explicit adapter for the supplied synthetic workbook; no name splitting or official classification."""
import json,sys,hashlib
from collections import defaultdict,Counter
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ppef_import import preview,norm
from app.registry_models import Register,CATALOGUES,validate_dates,quality
from datetime import date
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
raw=source.read_bytes();parsed=preview(source.name,raw)
assert not parsed['errors'],parsed['errors'][:2]
w=load_workbook(source,read_only=True,data_only=True)
def rows(name):
    values=iter(w[name].values);headers=next(values)
    return [dict(zip(headers,r)) for r in values if any(v is not None for v in r)]
people=defaultdict(list)
for p in rows('PERSONNES'):people[p['N° RP']].append(p)
scenarios={x['N° RP']:x for x in rows('SCENARIOS')}
def controlled(value,key):
    for k,label in CATALOGUES[key].items():
        if norm(value)==norm(label):return {key:k}
    return {key:'other',key+'_other':str(value)}
items=[];counts=Counter();money=defaultdict(Decimal);anomalies=[]
for item in parsed['items']:
    core=item['core'];r=item['record'];rp=core['rp_number'];pp=pm=0;r['people']=[];r['sentences']=[];r['declarations']['unresolved_people_text']=None;r['count_basis']='enumerated'
    d=r['decisions'][0];o=r['offences'][0];d['outcomes']=[]
    for person in people.pop(rp,[]):
        kind='physical' if person['Type']=='Personne physique' else 'legal' if person['Type']=='Personne morale' else None
        assert kind,(rp,person['Type'])
        pp+=kind=='physical';pm+=kind=='legal'
        p={'reference':person['ID personne'],'kind':kind,'role':'defendant','display_name':person['Nom fictif'],'sex':{'Masculin':'male','Féminin':'female'}.get(person['Sexe simulé'],'not_applicable' if kind=='legal' else 'undetermined'),'nationality':person['Nationalité simulée'] if kind=='physical' else None,'public_agent':{'Oui':'yes','Non':'no'}.get(person['Agent public simulé'],'not_applicable' if kind=='legal' else 'undetermined')}
        if kind=='physical':p.update(controlled(person['Profession'],'profession'))
        else:p.update(controlled(person['Activité'],'activity'));p.update(controlled(person['Forme juridique'],'legal_form'))
        r['people'].append(p)
        result={'Condamné':'conviction','Relaxé':'acquittal'}.get(person['Résultat individuel simulé'])
        assert result,(rp,person['Résultat individuel simulé'])
        d['outcomes'].append({'person_reference':p['reference'],'offence_reference':o['reference'],'result':result});counts[result]+=1
        months=person['Emprisonnement simulé (mois)']
        if kind=='physical' and result=='conviction' and months:
            assert isinstance(months,int) and months>0
            r['sentences'].append({'reference':'S-'+p['reference'],'decision_reference':d['reference'],'person_reference':p['reference'],'sentence_kind':'custody','duration_months':months,'source_text':'Durée individuelle simulée de PERSONNES ; qualification technique, non règle officielle'})
    assert (pp,pm)==(core['person_physical_count'],core['person_legal_count']),(rp,pp,pm)
    counts['physical']+=pp;counts['legal']+=pm
    scenario=scenarios.pop(rp)
    assert sum(x['result']=='conviction' for x in d['outcomes'])==scenario['Condamnés attendus']
    assert sum(x['result']=='acquittal' for x in d['outcomes'])==scenario['Relaxés attendus']
    # The supplied notice explicitly describes a first hearing followed by a merits decision.
    r['procedure']['first_hearing_held']=r['source_context']['first_hearing_source_date']
    # No orientation date is present. Keep it missing and visible as a quality issue.
    r['source_context']['specific_offence']=scenario['Sous-type explicatif']
    r['procedure']['observations']=scenario['Faits simulés']+' | '+scenario['Qualification juridique']+' | Sort des biens source : '+scenario['Sort des biens simulé']+' | Convention de fixture : date de confiscation/amende rattachée à la décision ; date propre absente du classeur.'
    o['amount_basis']='alleged_damage'
    for m in r['measures']:
        if m['kind']=='confiscation':m['disposition']='confiscated' if Decimal(m['amount']['value'])>0 else 'not_applicable'
    # Source notice: zero denotes known absence, not an unidentified measure.
    r['measures']=[m for m in r['measures'] if m['kind']=='seizure' or Decimal(m['amount']['value'])>0]
    model=validate_dates(Register.model_validate(r),date.fromisoformat(core['date_rp']))
    issues=quality(model,core)
    if issues:anomalies.append({'rp':rp,'issues':issues})
    counts['dossiers']+=1;counts['decisions']+=len(model.decisions);counts['measures']+=len(model.measures)
    counts['mixed_decisions']+=d['result']=='mixed'
    for m in model.measures:money[m.kind]+=Decimal(m.amount.value)
    money['alleged']+=Decimal(o['amount']['value'])
    items.append({'synthetic':True,'core':core,'record':model.model_dump(mode='json'),'source_sha256':hashlib.sha256(raw).hexdigest(),'fixture_id':'enriched-workbook-20261025'})
assert not people and not scenarios,'Orphan rows in supporting sheets'
assert len(items)==1500 and sum(len(x['record']['people']) for x in items)==3864
(out/'registres_enrichis.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in items)+'\n')
proof={'source_sha256':hashlib.sha256(raw).hexdigest(),'counts':dict(counts),'financial_xof':{k:str(v) for k,v in money.items()},'quality_cases':len(anomalies),'quality':anomalies,'officially_approved':False,'workflow':'All imported as drafts; target_status ignored','missing_orientation_date_preserved':True,'no_orphan_rows':True}
(out/'attendus_enrichis.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in proof.items() if k!='quality'},ensure_ascii=False))
