"""Audited control plane: bounded profiles and versioned site settings."""
import json,uuid,time
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
SCHEMA='''
CREATE TABLE IF NOT EXISTS super_administrators(user_id INTEGER PRIMARY KEY REFERENCES users(id));
CREATE TABLE IF NOT EXISTS admin_profiles(id TEXT PRIMARY KEY,label TEXT NOT NULL,base_profile TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_profile_assignments(user_id INTEGER PRIMARY KEY REFERENCES users(id),profile_id TEXT NOT NULL REFERENCES admin_profiles(id));
CREATE TABLE IF NOT EXISTS site_configuration(id INTEGER PRIMARY KEY,version INTEGER NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS site_configuration_history(id TEXT PRIMARY KEY,version INTEGER NOT NULL,payload TEXT NOT NULL,reason TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
'''
BASES={'technical':'admin','direction':'supervisor','cabinet':'supervisor','clerk':'collector','statistician':'supervisor'}
LABELS={'technical':'Administration technique','direction':'Direction','cabinet':'Responsable de cabinet','clerk':'Greffe / saisie','statistician':'Statistiques'}
DEFAULTS={'site_name':'SISAJ','subtitle':'PPEF · ABIDJAN','welcome':'La précision au service de votre mission.','accent':'forest','density':'comfortable','support_message':''}
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Reason(Strict):
    reason:str=Field(min_length=5,max_length=1000)
class ProfileIn(Strict):
    label:str=Field(min_length=3,max_length=80)
    base_profile:str
class Account(Reason):
    profile_id:str
    cabinets:list[str]=Field(default_factory=list,max_length=100)
    jurisdictions:list[str]=Field(default_factory=list,max_length=100)
    active:bool=True
    super_admin:bool=False
class NewAccount(Account):
    username:str=Field(min_length=3,max_length=80)
    password:str=Field(min_length=14,max_length=200)
class ResetPassword(Reason):
    password:str=Field(min_length=14,max_length=200)
class Appearance(Strict):
    site_name:str=Field(min_length=2,max_length=40)
    subtitle:str=Field(max_length=80)
    welcome:str=Field(max_length=180)
    accent:str
    density:str
    support_message:str=Field(max_length=300)
class Configuration(Reason):
    expected_version:int=Field(ge=1)
    settings:Appearance
class RestoreConfiguration(Reason):
    expected_version:int=Field(ge=1)
def is_super(c,uid):return bool(c.execute('SELECT user_id FROM super_administrators WHERE user_id=?',(uid,)).fetchone())
def appearance(c):
    r=c.execute('SELECT * FROM site_configuration WHERE id=1').fetchone()
    return {'version':r['version'],'settings':json.loads(r['payload'])} if r else {'version':1,'settings':DEFAULTS.copy()}
def seed(c):
    c.execute('INSERT OR IGNORE INTO site_configuration VALUES (1,1,?)',(json.dumps(DEFAULTS,ensure_ascii=False),))
    for key in BASES:c.execute('INSERT OR IGNORE INTO admin_profiles VALUES (?,?,?,?)',(key,LABELS[key],key,'2026-10-26T00:00:00+00:00'))
def install(app,db,audit,utcnow,user_from_token,pw_hash,database_url):
    with db(write=True) as c:
        c.executescript(SCHEMA);seed(c)
        owner=c.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if owner and not c.execute('SELECT user_id FROM super_administrators').fetchone():
            c.execute('INSERT INTO super_administrators VALUES (?)',(owner['id'],));audit(c,owner['id'],'migrate_owner','super_administrator',owner['id'])
    def owner(u=Depends(user_from_token)):
        with db() as c:ok=u['role']=='admin' and is_super(c,u['id'])
        if not ok:raise HTTPException(403,'Accès réservé au super administrateur.')
        return u
    def lock(c,u):
        c.execute('SELECT id FROM users ORDER BY id'+(' FOR UPDATE' if database_url else '')).fetchall()
        r=c.execute('SELECT active,role FROM users WHERE id=?',(u['id'],)).fetchone()
        if not r or not r['active'] or r['role']!='admin' or not is_super(c,u['id']):raise HTTPException(403,'Habilitation révoquée.')
    @app.get('/superadmin')
    def overview(u=Depends(owner)):
        with db() as c:
            users=[]
            for r in c.execute('SELECT id,username,role,active,created_at FROM users ORDER BY id').fetchall():
                v=dict(r);v['super_admin']=is_super(c,r['id'])
                p=c.execute('SELECT * FROM user_data_profiles WHERE user_id=?',(r['id'],)).fetchone();a=c.execute('SELECT profile_id FROM admin_profile_assignments WHERE user_id=?',(r['id'],)).fetchone()
                v.update(profile_id=a['profile_id'] if a else (p['profile'] if p else {'admin':'technical','collector':'clerk','supervisor':'cabinet'}[r['role']]),cabinets=json.loads(p['cabinets']) if p else [],jurisdictions=json.loads(p['jurisdictions']) if p else [])
                v['sessions']=c.execute('SELECT COUNT(*) n FROM sessions WHERE user_id=? AND expires_at>=?',(r['id'],int(time.time()))).fetchone()['n'];users.append(v)
            return {'users':users,'profiles':[dict(r) for r in c.execute('SELECT * FROM admin_profiles ORDER BY label').fetchall()],**appearance(c)}
    @app.post('/superadmin/profiles')
    def create_profile(x:ProfileIn,u=Depends(owner)):
        if x.base_profile not in BASES:raise HTTPException(422,'Profil de sécurité inconnu.')
        ident=uuid.uuid4().hex
        with db(write=True) as c:
            lock(c,u)
            if any(r['label'].casefold()==x.label.casefold() for r in c.execute('SELECT label FROM admin_profiles').fetchall()):raise HTTPException(409,'Ce libellé existe déjà.')
            c.execute('INSERT INTO admin_profiles VALUES (?,?,?,?)',(ident,x.label,x.base_profile,utcnow()));audit(c,u['id'],'create','admin_profile',ident,x.model_dump())
        return {'id':ident}
    def apply(c,uid,x,u):
        p=c.execute('SELECT * FROM admin_profiles WHERE id=?',(x.profile_id,)).fetchone()
        if not p:raise HTTPException(422,'Profil inconnu.')
        role=BASES[p['base_profile']]
        if role=='admin' and (x.cabinets or x.jurisdictions):raise HTTPException(422,'Le profil technique dispose d’un périmètre global ; ne pas saisir de restrictions inopérantes.')
        if x.super_admin and (role!='admin' or x.cabinets or x.jurisdictions):raise HTTPException(422,'Un super administrateur doit avoir un profil technique global.')
        if p['base_profile'] in ('cabinet','clerk') and not (x.cabinets or x.jurisdictions):raise HTTPException(422,'Précisez un cabinet ou une juridiction.')
        if any(not v.strip() or len(v)>100 for v in x.cabinets+x.jurisdictions):raise HTTPException(422,'Périmètre invalide.')
        if uid==u['id'] and (not x.active or not x.super_admin or role!='admin'):raise HTTPException(409,'Votre propre accès super administrateur doit rester actif.')
        if is_super(c,uid) and (not x.active or not x.super_admin or role!='admin'):
            count=c.execute("SELECT COUNT(*) n FROM super_administrators a JOIN users u ON u.id=a.user_id WHERE u.active=1 AND u.role='admin'").fetchone()['n']
            if count<=1:raise HTTPException(409,'Le dernier super administrateur actif est protégé.')
        c.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,int(x.active),uid));c.execute('DELETE FROM super_administrators WHERE user_id=?',(uid,))
        if x.super_admin:c.execute('INSERT INTO super_administrators VALUES (?)',(uid,))
        c.execute('DELETE FROM user_data_profiles WHERE user_id=?',(uid,));c.execute('INSERT INTO user_data_profiles VALUES (?,?,?,?)',(uid,p['base_profile'],json.dumps(x.cabinets),json.dumps(x.jurisdictions)))
        c.execute('DELETE FROM admin_profile_assignments WHERE user_id=?',(uid,));c.execute('INSERT INTO admin_profile_assignments VALUES (?,?)',(uid,x.profile_id));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
        audit(c,u['id'],'configure','user',uid,{**x.model_dump(exclude={'password'}),'role':role})
    @app.post('/superadmin/users')
    def create_account(x:NewAccount,u=Depends(owner)):
        with db(write=True) as c:
            lock(c,u)
            if c.execute('SELECT id FROM users WHERE username=?',(x.username,)).fetchone():raise HTTPException(409,'Identifiant déjà utilisé.')
            uid=c.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(x.username,pw_hash(x.password),'collector',utcnow())).lastrowid;apply(c,uid,x,u)
        return {'id':uid,'status':'created'}
    @app.put('/superadmin/users/{uid}')
    def update_account(uid:int,x:Account,u=Depends(owner)):
        with db(write=True) as c:
            lock(c,u)
            if not c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():raise HTTPException(404,'Compte introuvable.')
            apply(c,uid,x,u)
        return {'status':'updated','sessions_revoked':True}
    @app.post('/superadmin/users/{uid}/revoke-sessions')
    def revoke(uid:int,x:Reason,u=Depends(owner)):
        with db(write=True) as c:
            lock(c,u)
            if not c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():raise HTTPException(404,'Compte introuvable.')
            c.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(c,u['id'],'revoke_sessions','user',uid,x.model_dump())
        return {'status':'revoked'}
    @app.post('/superadmin/users/{uid}/password')
    def reset(uid:int,x:ResetPassword,u=Depends(owner)):
        with db(write=True) as c:
            lock(c,u)
            if not c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():raise HTTPException(404,'Compte introuvable.')
            c.execute('UPDATE users SET password_hash=? WHERE id=?',(pw_hash(x.password),uid));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(c,u['id'],'reset_password','user',uid,{'reason':x.reason})
        return {'status':'reset','sessions_revoked':True}
    def save(c,settings,expected,reason,u):
        if settings['accent'] not in ('forest','blue','slate') or settings['density'] not in ('comfortable','compact'):raise HTTPException(422,'Style non autorisé.')
        payload=json.dumps(settings,ensure_ascii=False);old=appearance(c)
        cur=c.execute('UPDATE site_configuration SET version=version+1,payload=? WHERE id=1 AND version=?',(payload,expected))
        if cur.rowcount!=1:raise HTTPException(409,'Réglages modifiés ailleurs. Rechargez la page.')
        if not c.execute('SELECT id FROM site_configuration_history WHERE version=?',(old['version'],)).fetchone():c.execute('INSERT INTO site_configuration_history VALUES (?,?,?,?,?,?)',(uuid.uuid4().hex,old['version'],json.dumps(old['settings']),'État précédent',u['id'],utcnow()))
        ident=uuid.uuid4().hex;c.execute('INSERT INTO site_configuration_history VALUES (?,?,?,?,?,?)',(ident,expected+1,payload,reason,u['id'],utcnow()));audit(c,u['id'],'configure','site',ident,{'version':expected+1,'reason':reason,'settings':settings})
        return {'version':expected+1,'settings':settings}
    @app.put('/superadmin/configuration')
    def configure(x:Configuration,u=Depends(owner)):
        with db(write=True) as c:lock(c,u);return save(c,x.settings.model_dump(),x.expected_version,x.reason,u)
    @app.get('/superadmin/configuration/history')
    def history(u=Depends(owner)):
        with db() as c:return {'items':[{**dict(r),'payload':json.loads(r['payload'])} for r in c.execute('SELECT h.*,u.username FROM site_configuration_history h JOIN users u ON u.id=h.created_by ORDER BY h.version DESC').fetchall()]}
    @app.post('/superadmin/configuration/{ident}/restore')
    def restore(ident:str,x:RestoreConfiguration,u=Depends(owner)):
        with db(write=True) as c:
            lock(c,u);r=c.execute('SELECT payload FROM site_configuration_history WHERE id=?',(ident,)).fetchone()
            if not r:raise HTTPException(404,'Version introuvable.')
            return save(c,json.loads(r['payload']),x.expected_version,x.reason,u)
