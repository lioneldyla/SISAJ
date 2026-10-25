"""Descriptive test dashboard. One cohort and one filter contract for cards, lists and exports."""
import csv,io,json
from collections import Counter,defaultdict
from datetime import date,datetime,timezone
from decimal import Decimal
from statistics import median,mean
from pathlib import Path
from fastapi import Depends,HTTPException,Query
from fastapi.responses import StreamingResponse
from .registry import read_record
from .registry_models import quality,CATALOGUES
INDICATORS=json.loads((Path(__file__).parent/'indicator_catalogue.json').read_text())

def analyze(c,u,start=None,end=None,as_of=None,date_basis='receipt',cabinet=None,provenance=None,category=None,subtype=None,party=None,transnational=None,status='all',jurisdiction=None,waiting_days=90,q=None,metric=None,sort='rp',direction='asc',limit=25,offset=0):
    if start and end and start>end:raise HTTPException(422,'Période inversée')
    if date_basis not in ('receipt','closure','hearing','decision'):raise HTTPException(422,'Date de rattachement invalide')
    if status not in ('all','draft','returned','submitted','validated'):raise HTTPException(422,'Statut invalide')
    if party not in (None,'','physical','legal','mixed'):raise HTTPException(422,'Nature des personnes invalide')
    if transnational not in (None,'','yes','no','unknown'):raise HTTPException(422,'Dimension transnationale invalide')
    if sort not in ('rp','received','cabinet','category','status','updated'):raise HTTPException(422,'Tri invalide')
    if direction not in ('asc','desc'):raise HTTPException(422,'Sens de tri invalide')
    as_of=as_of or end or date.today()
    if start and start>as_of:raise HTTPException(422,'Observation antérieure au début de période')
    def period(x):return bool(x and (not start or str(x)>=str(start)) and (not end or str(x)<=str(end)) and str(x)<=str(as_of))
    items=[];groups=defaultdict(set);cats=defaultdict(set);monthly=defaultdict(lambda:Counter());results=defaultdict(set);financial=defaultdict(Decimal);financial_missing=Counter();money_ids=defaultdict(set);alerts=[];professions=Counter();activities=Counter();person_results=Counter();delays=[];options=defaultdict(set);cabinets=defaultdict(Counter);decision_count=0;cabinet_options=set();quality_codes=defaultdict(set);hearing_counts=Counter()
    for row in c.execute('SELECT * FROM cases ORDER BY id').fetchall():
        case=dict(row);r=read_record(c,case);p=r.procedure;cid=case['id'];received=date.fromisoformat(case['date_rp'])
        from .access import permitted
        if not permitted(c,case,u):continue
        # Existing application roles have a common case perimeter. No unconfigured cabinet permission is invented.
        if status!='all' and case['status']!=status:continue
        if jurisdiction and r.jurisdiction_code!=jurisdiction:continue
        if received>as_of:continue
        dates={'receipt':[received],'closure':[p.closure_date],'hearing':[p.first_hearing_held,*[h.held_date for h in r.hearings]],'decision':[d.decision_date for d in r.decisions]}
        if not any(period(x) for x in dates[date_basis]):continue
        cabinet_options.add(p.cabinet or 'Non affecté')
        if cabinet and (p.cabinet or 'Non affecté') not in cabinet:continue
        if provenance and case['provenance']!=provenance:continue
        if category and case['category']!=category:continue
        if subtype and r.source_context.specific_offence!=subtype:continue
        pp=sum(x.kind=='physical' and x.role=='defendant' for x in r.people) if r.count_basis=='enumerated' else case['person_physical_count']
        pm=sum(x.kind=='legal' and x.role=='defendant' for x in r.people) if r.count_basis=='enumerated' else case['person_legal_count']
        nature='mixed' if pp and pm else 'physical' if pp and pm==0 else 'legal' if pm and pp==0 else 'unknown'
        if party and party!=nature:continue
        tn=r.transnational_state if r.transnational_state in ('yes','no') else 'unknown'
        if transnational and tn!=transnational:continue
        if q and q.casefold() not in ' '.join(str(case[k] or '') for k in ('rp_number','ri_number','provenance','category')).casefold():continue
        groups['cohort'].add(cid);cats[case['category']].add(cid)
        cabinets[p.cabinet or 'Non affecté']['cases']+=1
        if pp is not None:cabinets[p.cabinet or 'Non affecté']['physical']+=pp
        if pm is not None:cabinets[p.cabinet or 'Non affecté']['legal']+=pm
        for k,v in [('cabinet',p.cabinet),('provenance',case['provenance']),('category',case['category']),('subtype',r.source_context.specific_offence),('jurisdiction',r.jurisdiction_code)]:
            if v:options[k].add(v)
        if period(received):groups['received'].add(cid);monthly[str(received)[:7]]['received']+=1
        if pp is not None and pm is not None:groups['persons'].add(cid)
        case_delays=[];events=[(str(received),'Réception RP')]
        if p.closure_date and p.closure_date<=as_of:events.append((str(p.closure_date),'Clôture de l’instruction'))
        if p.first_hearing_held and p.first_hearing_held<=as_of and not any(h.held_date==p.first_hearing_held for h in r.hearings):events.append((str(p.first_hearing_held),'Audience tenue'))
        future=[]
        if p.first_hearing_planned and p.first_hearing_planned>=as_of:future.append((str(p.first_hearing_planned),'Audience prévue'))
        for h in r.hearings:
            when=h.held_date or h.planned_date
            if period(when):hearing_counts[h.status]+=1
            if h.held_date and h.held_date<=as_of:events.append((str(h.held_date),'Audience '+{'held':'tenue','adjourned':'renvoyée'}.get(h.status,h.status)))
            if h.status=='planned' and h.planned_date and h.planned_date>=as_of:future.append((str(h.planned_date),'Audience prévue'))
            if h.status=='adjourned' and h.next_date and h.next_date>=as_of:future.append((str(h.next_date),'Renvoi enregistré'))
        for d in r.decisions:
            if d.decision_date and d.decision_date<=as_of:events.append((str(d.decision_date),'Décision '+(d.number or d.reference)))
            if not period(d.decision_date):continue
            decision_count+=1;groups['decisions'].add(cid);cabinets[p.cabinet or 'Non affecté']['decisions']+=1
            monthly[str(d.decision_date)[:7]]['decisions']+=1
            if d.nature in ('merits','mixed','partial_merits'):
                groups['judged'].add(cid)
                values={o.result for o in d.outcomes}
                conviction='conviction' in values or d.result in ('conviction','mixed');acquittal='acquittal' in values or d.result in ('acquittal','mixed')
                key='mixed' if conviction and acquittal else 'conviction_only' if conviction else 'acquittal_only' if acquittal else 'unknown'
                results[key].add((cid,d.reference));groups['result_'+key].add(cid)
                days=(d.decision_date-received).days
                if days>=0:delays.append(days);case_delays.append(days);groups['delay'].add(cid)
                for o in d.outcomes:person_results[o.result]+=1
        for person in r.people:
            if person.role!='defendant':continue
            if person.kind=='physical':professions[person.profession_other or CATALOGUES['profession'].get(person.profession,person.profession)]+=1
            if person.kind=='legal':activities[person.activity_other or CATALOGUES['activity'].get(person.activity,person.activity)]+=1
        amounts=defaultdict(Decimal)
        for m in r.measures:
            if not period(m.measure_date):continue
            if m.amount.state=='known':
                key=(m.kind,m.amount.currency,m.valuation_basis);financial[key]+=Decimal(m.amount.value);amounts[(m.kind,m.amount.currency)]+=Decimal(m.amount.value)
                money_ids[m.kind].add(cid);groups[m.kind].add(cid)
            else:financial_missing[m.kind]+=1
        for o in r.offences:
            if o.amount.state=='known':financial[('alleged',o.amount.currency,o.amount_basis)]+=Decimal(o.amount.value);money_ids['alleged'].add(cid);groups['alleged'].add(cid)
            else:financial_missing['alleged']+=1
        issues=quality(r,case)
        if issues:groups['quality'].add(cid)
        for issue in issues:quality_codes[issue['code']].add(cid)
        for issue in issues:alerts.append({'id':cid,'rp':case['rp_number'],'type':'quality','reason':issue['message'],'action':'Compléter et vérifier la pièce source','responsible':p.cabinet or None})
        age=(as_of-received).days
        last=max(events)[0]
        inactive=(as_of-date.fromisoformat(last)).days
        if age>waiting_days:groups['old'].add(cid)
        if inactive>waiting_days:groups['inactive'].add(cid)
        if case['status']=='returned':groups['returned'].add(cid)
        groups['age_mean'].add(cid)
        if inactive>waiting_days:alerts.append({'id':cid,'rp':case['rp_number'],'type':'followup','reason':f'Aucun événement daté depuis {inactive} jours ; seuil indicatif {waiting_days}','action':'Vérifier le stade et les prochaines actions','responsible':p.cabinet or None})
        for when,label in future:
            if (date.fromisoformat(when)-as_of).days<=14:alerts.append({'id':cid,'rp':case['rp_number'],'type':'followup','reason':label+' le '+when,'action':'Préparer l’audience','responsible':p.cabinet or None})
        items.append({'id':cid,'rp':case['rp_number'],'received':str(received),'cabinet':p.cabinet,'category':case['category'],'subtype':r.source_context.specific_offence,'pp':pp,'pm':pm,'count_basis':r.count_basis,'orientation':p.orientation_other or CATALOGUES['orientation'].get(p.orientation,p.orientation),'status':case['status'],'last_event':' · '.join(max(events)),'next_event':' · '.join(min(future)) if future else None,'seizure_xof':str(amounts[('seizure','XOF')]) if cid in money_ids['seizure'] and any(m.kind=='seizure' and m.amount.currency=='XOF' and m.amount.state=='known' and period(m.measure_date) for m in r.measures) else None,'confiscation_xof':str(amounts[('confiscation','XOF')]) if any(m.kind=='confiscation' and m.amount.currency=='XOF' and m.amount.state=='known' and period(m.measure_date) for m in r.measures) else None,'issue_count':len(issues),'age_days':age,'updated':case['updated_at']})
    def card(key,label,value,unit,definition,available=True):return {'key':key,'label':label,'value':value if available else None,'unit':unit,'definition':definition,'dossiers':len(groups[key]),'available':available}
    pp_known=all(x['pp'] is not None for x in items);pm_known=all(x['pm'] is not None for x in items)
    def money(kind):
        vals=[v for (k,cur,b),v in financial.items() if k==kind and cur=='XOF'];return str(sum(vals,Decimal())) if vals and not financial_missing[kind] else None
    cards=[card('received','Dossiers reçus',len(groups['received']),'dossiers','RP + année distincts ; date RP dans la période et le périmètre sélectionné.'),card('judged','Dossiers avec décision au fond',len(groups['judged']),'dossiers','Au moins une décision au fond datée dans la période ; chaque dossier compte une fois.'),card('stock','Dossiers en cours',None,'dossiers','Non calculable : la clôture d’instruction ne prouve pas la fin du dossier judiciaire ; historique de terminaison à valider.',False),card('persons','Personnes poursuivies',sum((x['pp'] or 0)+(x['pm'] or 0) for x in items),'personnes dans leurs dossiers','Fiches individuelles si énumérées ; sinon effectifs déclarés. Aucune déduplication entre dossiers.',bool(items) and pp_known and pm_known),card('seizure','Montants saisis',money('seizure'),'FCFA','Mesures datées dans la période ; XOF seulement, sans conversion. Montants inconnus bloquent le total complet.',money('seizure') is not None),card('confiscation','Montants confisqués',money('confiscation'),'FCFA','Mesures datées dans la période ; valeurs saisies, sans présumer leur exécution.',money('confiscation') is not None),card('delay','Délai médian réception → décision',median(delays) if delays else None,'jours','Observations par décision au fond ; intervalles complets et positifs, pas une estimation des dossiers ouverts.',bool(delays)),card('quality','Dossiers à vérifier',len(groups['quality']),'dossiers','Dossiers distincts ayant au moins un contrôle de qualité ; ne constitue pas une conclusion juridique.')]
    groups['delay_mean']=groups['delay'];groups['completion']={x['id'] for x in items if not x['issue_count']}
    cards.extend([card('decisions','Décisions rendues',decision_count,'décisions','Toutes natures de décisions datées dans la période ; une décision ne constitue pas nécessairement un dossier distinct.'),card('age_mean','Ancienneté moyenne depuis RP',round(mean(x['age_days'] for x in items),1) if items else None,'jours','Ancienneté de la cohorte depuis la réception ; ne désigne pas un stock de dossiers ouverts.',bool(items)),card('old','Dossiers anciens',len(groups['old']),'dossiers',f'Ancienneté depuis RP supérieure au seuil indicatif de {waiting_days} jours, sans conclusion juridique.'),card('inactive','Dossiers sans mouvement récent',len(groups['inactive']),'dossiers',f'Aucun événement daté depuis plus de {waiting_days} jours ; seuil de suivi indicatif.'),card('returned','Dossiers retournés pour correction',len(groups['returned']),'dossiers','Statut de validation retourné dans la cohorte.'),card('delay_mean','Délai moyen réception → décision',round(mean(delays),1) if delays else None,'jours','Moyenne des intervalles connus jusqu’aux décisions au fond ; aucune prévision.',bool(delays)),card('completion','Dossiers sans anomalie détectée',round(100*len(groups['completion'])/len(items),1) if items else None,'%', 'Dossiers sans alerte du contrôleur actuel divisés par les dossiers de la cohorte ; pas une certification de complétude.',bool(items))])
    if metric and metric not in {x['key'] for x in cards}|set(groups):raise HTTPException(422,'Indicateur inconnu')
    filtered=[x for x in items if not metric or x['id'] in groups[metric]]
    filtered.sort(key=lambda x:(x.get(sort) is None,str(x.get(sort) or '')),reverse=direction=='desc')
    params={'start':str(start) if start else None,'end':str(end) if end else None,'as_of':str(as_of),'date_basis':date_basis,'cabinet':cabinet,'provenance':provenance,'category':category,'subtype':subtype,'party':party,'transnational':transnational,'status':status,'jurisdiction':jurisdiction,'waiting_days':waiting_days,'q':q,'metric':metric,'sort':sort,'direction':direction}
    output={'generated_at':datetime.now(timezone.utc).isoformat(),'filters':params,'population':('Tous les statuts' if status=='all' else {'draft':'Brouillons','submitted':'Soumis','returned':'Retournés','validated':'Validés'}[status]),'officially_approved':False,'cards':cards,'persons':{'physical':sum(x['pp'] or 0 for x in items) if pp_known else None,'legal':sum(x['pm'] or 0 for x in items) if pm_known else None,'professions':dict(professions),'activities':dict(activities),'individual_outcomes':dict(person_results)},'monthly':[{'month':k,**v} for k,v in sorted(monthly.items())],'categories':[{'label':k,'count':len(v)} for k,v in sorted(cats.items(),key=lambda x:-len(x[1]))],'results':[{'key':k,'count':len(v),'unit':'décisions'} for k,v in results.items()],'financial':[{'kind':k,'currency':cur,'basis':b,'amount':str(v)} for (k,cur,b),v in sorted(financial.items())],'financial_missing':dict(financial_missing),'alerts':alerts[:200],'alerts_total':len(alerts),'rows':filtered[offset:offset+limit],'total':len(filtered),'cohort_size':len(items),'options':{k:sorted(v) for k,v in options.items()},'limits':['Les habilitations par profil, cabinet et juridiction sont appliquées côté serveur ; les comptes historiques sans profil conservent leur périmètre existant.','Audiences successives disponibles si saisies ; calendrier non exhaustif et exécution des confiscations non établie.','Jeu enrichi : tous les dossiers suivent une instruction et une décision au fond ; autres parcours absents.','Les montants de bases de valorisation différentes sont détaillés séparément ; leur comparaison économique nécessite un périmètre validé.'],'delay_distribution':dict(Counter('0–30 jours' if x<=30 else '31–90 jours' if x<=90 else '91–180 jours' if x<=180 else 'Plus de 180 jours' for x in delays))}


    output['by_cabinet']=[{'label':k,**v} for k,v in sorted(cabinets.items())]
    output['options']['cabinet']=sorted(cabinet_options)
    output['indicator_catalogue']=INDICATORS
    output['by_status']=[{'label':k,'count':v} for k,v in Counter(x['status'] for x in items).items()]
    output['dataset_kind']='synthetic'
    output['quality_summary']=[{'code':k,'dossiers':len(v)} for k,v in sorted(quality_codes.items())]
    output['hearing_summary']={'recorded_only':True,'by_status':dict(hearing_counts),'definition':'Audiences détaillées enregistrées, comptées à leur date tenue ou, à défaut, prévue. Première audience historique non ajoutée pour éviter les doublons.'}
    return output

def install(app,db,audit,utcnow,user_from_token,require_roles,safe_cell):
    def arguments(start:date|None=None,end:date|None=None,as_of:date|None=None,date_basis:str='receipt',cabinet:list[str]|None=Query(default=None),provenance:str|None=None,category:str|None=None,subtype:str|None=None,party:str|None=None,transnational:str|None=None,status:str='all',jurisdiction:str|None=None,waiting_days:int=Query(default=90,ge=1,le=3650),q:str|None=None,metric:str|None=None,sort:str='rp',direction:str='asc',limit:int=Query(default=25,ge=1,le=500),offset:int=Query(default=0,ge=0)):
        return locals()
    @app.get('/dashboard/analysis')
    def analysis(args=Depends(arguments),u=Depends(user_from_token)):
        with db() as c:return analyze(c,u,**args)
    @app.get('/dashboard/export.csv')
    def export(args=Depends(arguments),u=Depends(require_roles('admin','supervisor'))):
        args.update(limit=2147483647,offset=0)
        with db(write=True) as c:
            data=analyze(c,u,**args);audit(c,u['id'],'export','dashboard',detail={'filters':data['filters'],'rows':data['total']})
        buf=io.StringIO();w=csv.writer(buf)
        w.writerow(['SISAJ / État filtré']);w.writerow(['Nature des données','Fictives / test ; méthode non approuvée']);w.writerow(['Génération UTC',data['generated_at']]);w.writerow(['Filtres',json.dumps(data['filters'],ensure_ascii=False)]);w.writerow(['Unités','FCFA pour XOF ; jours ; personnes dans leurs dossiers'])
        keys=list(data['rows'][0]) if data['rows'] else ['id','rp'];w.writerow(keys)
        for row in data['rows']:w.writerow([safe_cell(row.get(k)) for k in keys])
        return StreamingResponse(io.BytesIO(('\ufeff'+buf.getvalue()).encode()),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="tableau_bord_filtre.csv"'})
