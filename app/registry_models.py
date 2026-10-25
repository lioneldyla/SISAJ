"""PPEF register: typed documents supplement the existing relational v0.4 model.
Catalogue entries are design proposals from the supplied specifications, not official law.
"""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

STATES={'not_recorded':'Non renseigné','undetermined':'À déterminer','pending':'En attente','not_applicable':'Non applicable','other':'Autre — préciser'}
CATALOGUES={
 'transnational_state':{'yes':'Oui','no':'Non',**STATES},
 'orientation':dict(prosecution='Poursuites engagées',trial_referral='Saisine de la juridiction de jugement',investigation='Ouverture d’une information judiciaire',introductory_order='Réquisitoire introductif',dismissal='Classement sans suite',transfer='Transmission à une autre autorité',joinder='Jonction à un autre dossier',alternative='Mesure alternative',**STATES),
 'closure_kind':dict(referral='Ordonnance de renvoi',total_dismissal='Non-lieu total',partial_dismissal='Non-lieu partiel',**STATES),
 'profession':dict(civil_servant='Fonctionnaire de l’État',contract_agent='Agent contractuel de l’État',local_agent='Agent de collectivité territoriale',public_institution='Agent d’un établissement public',elected='Élu / mandat public',magistrate='Magistrat',judicial_staff='Personnel judiciaire',public_company='Agent d’entreprise publique',liberal='Profession libérale',trader='Commerçant / entrepreneur',private_employee='Salarié du privé',no_known_profession='Sans profession connue',**STATES),
 'activity':dict(finance='Banque et services financiers',trade='Commerce et distribution',telecom='Télécommunications',digital='Informatique et numérique',transport='Transport et logistique',construction='BTP',industry='Industrie',agriculture='Agriculture',energy='Mines et énergie',health='Santé et pharmacie',education='Éducation',insurance='Assurance',real_estate='Immobilier',hospitality='Hôtellerie / restauration',import_export='Import-export',services='Services',ngo='Association / ONG',cooperative='Coopérative',administration='Administration / établissement public',**STATES),
 'legal_form':dict(individual='Entreprise individuelle',sarl='SARL',sa='SA',sas='SAS',snc='SNC',scs='SCS',sca='SCA',cooperative='Société coopérative',association='Association',ngo='ONG',foundation='Fondation',public_institution='Établissement public',public_company='Société d’État / entreprise publique',gie='GIE',branch='Succursale',**STATES),
 'nature':dict(merits='Décision au fond',interlocutory='Avant dire droit',mixed='Décision mixte',partial_merits='Partielle au fond',not_merits='Ne statuant pas au fond',**STATES),
 'result':dict(conviction='Condamnation',acquittal='Relaxe / acquittement selon juridiction',mixed='Condamnation et relaxe',referral='Renvoi',stay='Sursis à statuer',extinction='Extinction de l’action publique',inadmissible='Irrecevabilité',not_rendered='Non encore rendue',**STATES),
 'object_kind':dict(cash='Espèces',bank='Compte / avoirs bancaires',vehicle='Véhicule',real_estate='Bien immobilier',phone='Téléphone',computer='Matériel informatique',digital='Supports / données',documents='Documents',goods='Marchandises',equipment='Matériel professionnel',valuables='Bijoux / objets de valeur',substances='Produits ou substances',securities='Parts sociales / titres',none='Aucun bien',**STATES),
 'valuation_basis':dict(actual='Somme effectivement saisie / prononcée',blocked='Montant bloqué',estimated='Valeur estimée du bien',**STATES),
 'sentence_kind':dict(custody='Emprisonnement ferme',suspended='Emprisonnement avec sursis',fine='Amende',additional='Peine complémentaire',confiscation='Confiscation',none='Aucune peine',**STATES),
 'offence_group':dict(corruption='Corruption',assimilated='Infractions assimilées',abuse_office='Abus de fonction',corporate_assets='Abus de biens sociaux',concussion='Concussion',extortion='Extorsion de fonds',embezzlement='Détournement de deniers publics',laundering='Blanchiment autonome',tax='Fraude fiscale',environment='Crimes environnementaux',cyber='Cybercriminalité',drugs='Trafic de stupéfiants',trafficking='Traite des personnes',terrorism='Financement du terrorisme',pharmaceutical='Produits pharmaceutiques illicites',agricultural='Produits agricoles illicites',**STATES)
}

class Model(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
 @model_validator(mode='after')
 def controlled_values(self):
  for key,options in CATALOGUES.items():
   if key not in type(self).model_fields:continue
   value=getattr(self,key)
   if value not in options:raise ValueError(f'{key}: valeur non autorisée')
   if value=='other' and not getattr(self,key+'_other',None):raise ValueError(f'{key}: préciser la valeur Autre')
  for key in type(self).model_fields:
   if key.endswith('_other') and getattr(self,key[:-6],None)=='other' and not getattr(self,key,None):raise ValueError(key+': précision obligatoire')
  return self

class Money(Model):
 state:Literal['known','not_recorded','undetermined','pending','not_applicable']='not_recorded'
 value:str|None=Field(default=None,max_length=40)
 currency:str=Field(default='XOF',pattern=r'^[A-Z]{3}$')
 @model_validator(mode='after')
 def exact(self):
  import re
  if self.state=='known':
   if self.value is None or not re.fullmatch(r'\d{1,18}(\.\d{1,2})?',self.value):raise ValueError('Montant connu : 18 chiffres, 2 décimales maximum, positif ou nul')
   self.value=format(Decimal(self.value).quantize(Decimal('0.01')),'f')
  elif self.value is not None:raise ValueError('Un montant inconnu ne peut contenir une valeur ; zéro est un montant connu')
  return self

class Person(Model):
 reference:str=Field(min_length=1,max_length=80)
 kind:Literal['physical','legal','undetermined']='undetermined'
 role:Literal['defendant','victim','other']='defendant'
 identity_state:Literal['known','unknown']='known'
 display_name:str|None=Field(default=None,max_length=250)
 profession:str='not_recorded';profession_other:str|None=Field(default=None,max_length=250)
 activity:str='not_applicable';activity_other:str|None=Field(default=None,max_length=250)
 legal_form:str='not_applicable';legal_form_other:str|None=Field(default=None,max_length=250)
 public_agent:Literal['yes','no','undetermined','not_applicable']='undetermined'
 sex:Literal['male','female','undetermined','not_applicable']='undetermined'
 nationality:str|None=Field(default=None,max_length=100)
 @model_validator(mode='after')
 def identity(self):
  if self.identity_state=='known' and not self.display_name:raise ValueError('Nom requis pour une identité connue')
  if self.identity_state=='unknown' and self.display_name:raise ValueError('Identité inconnue : laisser le nom vide')
  if self.kind=='physical' and self.legal_form!='not_applicable':raise ValueError('Forme juridique non applicable à une personne physique')
  return self

class Offence(Model):
 reference:str=Field(min_length=1,max_length=80)
 parquet_label:str|None=Field(default=None,max_length=500)
 tribunal_label:str|None=Field(default=None,max_length=500)
 harmonised_label:str|None=Field(default=None,max_length=500)
 offence_group:str='undetermined';offence_group_other:str|None=Field(default=None,max_length=250)
 amount:Money=Field(default_factory=Money)
 amount_basis:Literal['alleged_damage','diverted_funds','fraud','asset_value','undetermined','other']='undetermined'
 amount_basis_other:str|None=Field(default=None,max_length=500)
 @model_validator(mode='after')
 def basis(self):
  if self.amount_basis=='other' and not self.amount_basis_other:raise ValueError('Préciser la définition du montant de l’infraction')
  return self

class Outcome(Model):
 person_reference:str;offence_reference:str
 result:Literal['conviction','acquittal','other','unknown']

class Decision(Model):
 reference:str=Field(min_length=1,max_length=80)
 number:str|None=Field(default=None,max_length=150)
 decision_date:date|None=None
 nature:str='undetermined';nature_other:str|None=Field(default=None,max_length=250)
 result:str='not_rendered';result_other:str|None=Field(default=None,max_length=500)
 content:str|None=Field(default=None,max_length=10000)
 outcomes:list[Outcome]=Field(default_factory=list,max_length=1000)

class Sentence(Model):
 reference:str=Field(min_length=1,max_length=80)
 decision_reference:str=Field(min_length=1,max_length=80)
 person_reference:str|None=None
 sentence_kind:str='undetermined';sentence_kind_other:str|None=Field(default=None,max_length=500)
 duration_months:int|None=Field(default=None,ge=0,le=12000,strict=True)
 source_text:str|None=Field(default=None,max_length=4000)

class Measure(Model):
 reference:str=Field(min_length=1,max_length=80)
 kind:Literal['fine','seizure','confiscation','compensation']
 decision_reference:str|None=Field(default=None,max_length=80)
 person_reference:str|None=Field(default=None,max_length=80)
 measure_date:date|None=None
 object_kind:str='not_applicable';object_kind_other:str|None=Field(default=None,max_length=500)
 description:str|None=Field(default=None,max_length=4000)
 asset_reference:str|None=Field(default=None,max_length=150)
 disposition:Literal['pending','maintained','returned','confiscated','other','not_applicable']='pending'
 disposition_other:str|None=Field(default=None,max_length=500)
 valuation_basis:str='undetermined';valuation_basis_other:str|None=Field(default=None,max_length=250)
 amount:Money=Field(default_factory=Money)

class Procedure(Model):
 cabinet_state:Literal['known','not_recorded','undetermined','pending','not_applicable']='not_recorded'
 orientation:str='not_recorded';orientation_other:str|None=Field(default=None,max_length=500)
 orientation_date:date|None=None
 cabinet:str|None=Field(default=None,max_length=250)
 closure_date:date|None=None
 closure_kind:str='not_recorded';closure_kind_other:str|None=Field(default=None,max_length=500)
 first_hearing_planned:date|None=None
 first_hearing_held:date|None=None
 transmission_date:date|None=None
 position:str|None=Field(default=None,max_length=500)
 observations:str|None=Field(default=None,max_length=10000)

 @model_validator(mode='after')
 def assignment(self):
  if self.cabinet and 'cabinet_state' not in self.model_fields_set:self.cabinet_state='known'
  if self.cabinet_state=='known' and not self.cabinet:raise ValueError('Cabinet connu : saisir son intitulé exact')
  if self.cabinet and self.cabinet_state!='known':raise ValueError('Un cabinet non affecté ne peut contenir un nom de cabinet')
  return self

class Declarations(Model):
 convicted_total:int|None=Field(default=None,ge=0,strict=True)
 convicted_male:int|None=Field(default=None,ge=0,strict=True)
 convicted_female:int|None=Field(default=None,ge=0,strict=True)
 victim_total:int|None=Field(default=None,ge=0,strict=True)
 convicted_nationalities:str|None=Field(default=None,max_length=2000)
 unresolved_people_text:str|None=Field(default=None,max_length=10000)
 @model_validator(mode='after')
 def totals(self):
  if self.convicted_total is not None and sum(x or 0 for x in (self.convicted_male,self.convicted_female))>self.convicted_total:raise ValueError('Ventilation par sexe supérieure au total des condamnés')
  return self

class SourceContext(Model):
 party_type_source:str|None=Field(default=None,max_length=500)
 trafficking_source_text:str|None=Field(default=None,max_length=500)
 first_hearing_source_date:date|None=None
 source_date:str|None=Field(default=None,max_length=150)
 order_number:str|None=Field(default=None,max_length=150)
 specific_offence:str|None=Field(default=None,max_length=1000)
 other_specificity:str|None=Field(default=None,max_length=2000)
 offence_treatment:str|None=Field(default=None,max_length=2000)
 matter:str|None=Field(default=None,max_length=250)

class Register(Model):
 ri_state:Literal['assigned','not_recorded','pending','not_applicable']='not_recorded'
 source_context:SourceContext=Field(default_factory=SourceContext)
 jurisdiction_code:str|None=None
 jurisdiction_name:str|None=Field(default=None,max_length=250)
 transnational_state:str='undetermined';transnational_state_other:str|None=Field(default=None,max_length=500)
 trafficking_state:Literal['yes','no','undetermined','not_recorded']='not_recorded'
 count_basis:Literal['declared','enumerated','undetermined']='declared'
 procedure:Procedure=Field(default_factory=Procedure)
 declarations:Declarations=Field(default_factory=Declarations)
 people:list[Person]=Field(default_factory=list,max_length=1000)
 offences:list[Offence]=Field(default_factory=list,max_length=1000)
 decisions:list[Decision]=Field(default_factory=list,max_length=1000)
 sentences:list[Sentence]=Field(default_factory=list,max_length=1000)
 measures:list[Measure]=Field(default_factory=list,max_length=1000)
 @model_validator(mode='after')
 def links(self):
  for group in ('people','offences','decisions','sentences','measures'):
   vals=getattr(self,group)
   if len({v.reference for v in vals})!=len(vals):raise ValueError('Référence dupliquée dans '+group)
  p={x.reference:x for x in self.people};off={x.reference for x in self.offences};dec={x.reference:x for x in self.decisions}
  for d in self.decisions:
   pairs=set()
   for o in d.outcomes:
    if o.person_reference not in p or o.offence_reference not in off:raise ValueError('Résultat sans personne / infraction du dossier')
    if p[o.person_reference].role!='defendant':raise ValueError('Résultat pénal réservé à une personne poursuivie')
    pair=(o.person_reference,o.offence_reference)
    if pair in pairs:raise ValueError('Résultat dupliqué pour une personne / infraction')
    pairs.add(pair)
  for x in [*self.sentences,*self.measures]:
   if x.decision_reference and x.decision_reference not in dec:raise ValueError('Décision de rattachement absente')
   if x.person_reference and x.person_reference not in p:raise ValueError('Personne de rattachement absente')
  for m in self.measures:
   if m.kind=='compensation' and m.person_reference and p[m.person_reference].role!='victim':raise ValueError('Une réparation individuelle doit être rattachée à une victime')
   if m.decision_reference and m.measure_date and dec[m.decision_reference].decision_date and m.measure_date<dec[m.decision_reference].decision_date:raise ValueError('Mesure antérieure à sa décision')
  if self.count_basis=='enumerated' and any(x.kind=='undetermined' for x in self.people if x.role=='defendant'):raise ValueError('Effectifs calculés : préciser la nature des personnes poursuivies')
  return self

class SaveRegister(Model):
 expected_version:int=Field(ge=1)
 reason:str=Field(min_length=5,max_length=1000)
 record:Register

def validate_dates(record,received):
 dates=[('orientation',record.procedure.orientation_date),('clôture',record.procedure.closure_date),('audience prévue',record.procedure.first_hearing_planned),('audience tenue',record.procedure.first_hearing_held),('transmission',record.procedure.transmission_date)]
 dates += [('décision',d.decision_date) for d in record.decisions]+[('mesure',m.measure_date) for m in record.measures]
 for label,d in dates:
  if d and d<received:raise ValueError(label+' antérieure à la date RP')
 return record

def quality(record,case):
 issues=[];add=lambda code,msg:issues.append({'code':code,'message':msg})
 p=record.procedure
 if record.ri_state=='assigned' and not case.get('ri_number'):add('RI_MISSING','RI annoncé attribué mais référence absente de la fiche dossier')
 if record.source_context.first_hearing_source_date and not (p.first_hearing_planned or p.first_hearing_held):add('HEARING_MEANING','Préciser si la première audience source était prévue ou tenue')
 if p.orientation not in ('not_recorded','undetermined','pending','not_applicable') and not p.orientation_date:add('ORIENTATION_DATE','Orientation sans date')
 if p.closure_kind not in ('not_recorded','undetermined','pending','not_applicable') and not p.closure_date:add('CLOSURE_DATE','Ordonnance de clôture sans date')
 if p.closure_date and p.closure_kind in ('not_recorded','undetermined','pending'):add('CLOSURE_KIND','Date de clôture sans nature confirmée')
 if record.count_basis=='declared' and record.people:
  for kind,field in [('physical','person_physical_count'),('legal','person_legal_count')]:
   n=sum(x.kind==kind and x.role=='defendant' for x in record.people)
   if case.get(field) is not None and case[field]!=n:add('COUNT_MISMATCH','Effectif déclaré différent des fiches détaillées : '+kind)
 if record.declarations.unresolved_people_text:add('PEOPLE_UNRESOLVED','Identités source groupées à répartir en fiches individuelles')
 for d in record.decisions:
  if d.result not in ('not_rendered','not_recorded','pending') and (not d.number or not d.decision_date):add('DECISION_REFERENCE','Décision rendue sans date ou numéro : '+d.reference)
 for m in record.measures:
  if not m.measure_date:add('MEASURE_DATE','Date de mesure manquante : '+m.reference)
  if m.kind in ('seizure','confiscation') and m.object_kind in ('not_recorded','undetermined','not_applicable'):add('OBJECT_KIND','Bien à préciser : '+m.reference)
 return issues
