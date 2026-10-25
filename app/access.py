"""Optional profiles bounded by the existing security roles; scoped legacy exports fail closed."""
import json,hashlib,time
from contextvars import ContextVar
from fastapi import Depends,HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field
principal=ContextVar('sisa_principal',default=None)
SCHEMA='CREATE TABLE IF NOT EXISTS user_data_profiles(user_id INTEGER PRIMARY KEY REFERENCES users(id), profile TEXT NOT NULL, cabinets TEXT NOT NULL, jurisdictions TEXT NOT NULL);'
def augment(c,u):
    r=c.execute('SELECT * FROM user_data_profiles WHERE user_id=?',(u['id'],)).fetchone()
    if r:u['data_profile']={'profile':r['profile'],'cabinets':json.loads(r['cabinets']),'jurisdictions':json.loads(r['jurisdictions'])}
    return u
def permitted(c,case,u=None):
    u=u or principal.get();p=u.get('data_profile') if u else None
    if not p or p['profile']=='technical':return True
    if p['profile'] in ('cabinet','clerk') and not (p['cabinets'] or p['jurisdictions']):return False
    row=c.execute('SELECT payload FROM registry_records WHERE case_id=?',(case['id'],)).fetchone();r=json.loads(row['payload']) if row else {}
    return (not p['cabinets'] or r.get('procedure',{}).get('cabinet') in p['cabinets']) and (not p['jurisdictions'] or r.get('jurisdiction_code') in p['jurisdictions'])
def check(c,case):
    if not permitted(c,case):raise HTTPException(404,'Dossier introuvable dans le périmètre autorisé')
def check_record(record,u):
    p=u.get('data_profile')
    if not p or p['profile']=='technical':return
    if p['cabinets'] and record.procedure.cabinet not in p['cabinets']:raise HTTPException(403,'Affectation hors du cabinet autorisé')
    if p['jurisdictions'] and record.jurisdiction_code not in p['jurisdictions']:raise HTTPException(403,'Affectation hors de la juridiction autorisée')
class Profile(BaseModel):
    profile:str
    cabinets:list[str]=Field(default_factory=list,max_length=100)
    jurisdictions:list[str]=Field(default_factory=list,max_length=100)
def install(app,db,audit,utcnow,require_roles):
    with db() as c:c.executescript(SCHEMA)
    @app.put('/users/{uid}/data-profile')
    def assign(uid:int,x:Profile,u=Depends(require_roles('admin'))):
        roles={'technical':'admin','direction':'supervisor','cabinet':'supervisor','clerk':'collector','statistician':'supervisor'}
        with db(write=True) as c:
            r=c.execute('SELECT role FROM users WHERE id=?',(uid,)).fetchone()
            if not r:raise HTTPException(404,'Compte introuvable')
            if x.profile not in roles or roles[x.profile]!=r['role']:raise HTTPException(422,'Profil incompatible avec le rôle de sécurité')
            if x.profile in ('cabinet','clerk') and not (x.cabinets or x.jurisdictions):raise HTTPException(422,'Périmètre obligatoire')
            c.execute('DELETE FROM user_data_profiles WHERE user_id=?',(uid,));c.execute('INSERT INTO user_data_profiles VALUES (?,?,?,?)',(uid,x.profile,json.dumps(x.cabinets),json.dumps(x.jurisdictions)))
            audit(c,u['id'],'assign','data_profile',uid,x.model_dump())
        return {'status':'assigned','profile':x.profile}
    @app.middleware('http')
    async def guard(request,call_next):
        auth=request.headers.get('authorization','');token=auth[7:] if auth.startswith('Bearer ') else request.cookies.get('sisa_session');u=None
        if token:
            with db() as c:
                r=c.execute('SELECT u.id,u.role,u.active,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
                if r and r['active'] and r['expires_at']>=int(time.time()):u=augment(c,dict(r))
        handle=principal.set(u)
        try:
            p=u.get('data_profile') if u else None;path=request.url.path
            if p and p['profile']!='technical':
                scoped=bool(p['cabinets'] or p['jurisdictions']) or p['profile'] in ('cabinet','clerk')
                global_path=path.startswith(('/stats','/reports','/exports','/registry/export','/registry/records','/registry/reports','/registry/statements','/imports','/registry/imports','/registry/batches','/registry/documents','/audit','/intelligence','/admin')) or path=='/dashboard'
                if scoped and global_path:return JSONResponse({'detail':'Vue globale indisponible ; utiliser le tableau de bord et son export filtré.'},status_code=403)
                if p['profile'] in ('direction','statistician') and request.method not in ('GET','HEAD','OPTIONS') and not path.startswith('/auth/'):
                    return JSONResponse({'detail':'Profil de consultation uniquement.'},status_code=403)
                if scoped and request.method=='POST' and path=='/cases':return JSONResponse({'detail':'Affectation initiale d’un nouveau dossier par le responsable global requise.'},status_code=403)
            return await call_next(request)
        finally:principal.reset(handle)
