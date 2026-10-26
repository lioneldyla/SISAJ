"""Control plane: grants, bounded profiles, revocations, audit and configuration rollback."""
import json
from fastapi.testclient import TestClient
from app.main import app,db
PASSWORD='Synthetic-Control-2026!'
def auth(c,name='owner_test'):
    return {'Authorization':'Bearer '+c.post('/auth/login',json={'username':name,'password':PASSWORD}).json()['access_token']}
def setup(c):
    assert c.post('/auth/bootstrap',json={'username':'owner_test','password':PASSWORD}).status_code==200
    h=auth(c);assert c.get('/auth/me',headers=h).json()['super_admin'] is True
    return h
def account(**kw):
    return {'profile_id':'technical','reason':'Test des habilitations','active':True,'super_admin':False,**kw}
def create(c,h,name='tech_test',**kw):
    return c.post('/superadmin/users',headers=h,json={**account(**kw),'username':name,'password':PASSWORD})
def test_owner_and_nonowner_authorization():
    with TestClient(app) as c:
        h=setup(c);r=create(c,h);assert r.status_code==200
        tech=auth(c,'tech_test')
        assert c.get('/superadmin',headers=tech).status_code==403
        assert c.post('/superadmin/profiles',headers=tech,json={'label':'Intrusion','base_profile':'technical'}).status_code==403
        assert c.put('/users/1/data-profile',headers=tech,json={'profile':'technical'}).status_code==403
        assert c.get('/superadmin',headers=h).status_code==200
        assert c.get('/auth/me',headers=tech).json()['super_admin'] is False
        assert c.get('/superadmin',headers={ 'Authorization':'Bearer unknown'}).status_code==401

def test_profile_scope_revocation_and_password_redaction():
    with TestClient(app) as c:
        h=setup(c)
        p=c.post('/superadmin/profiles',headers=h,json={'label':'Greffe cabinet test','base_profile':'clerk'}).json()['id']
        assert create(c,h,'agent_test',profile_id=p).status_code==422
        r=create(c,h,'agent_test',profile_id=p,cabinets=['Cabinet A']);assert r.status_code==200
        uid=r.json()['id'];agent=auth(c,'agent_test')
        assert c.get('/auth/me',headers=agent).json()['profile_label']=='Greffe cabinet test'
        assert c.get('/audit',headers=agent).status_code==403
        assert c.put('/superadmin/users/'+str(uid),headers=h,json=account(profile_id=p,cabinets=['Cabinet B'])).status_code==200
        assert c.get('/auth/me',headers=agent).status_code==401
        agent=auth(c,'agent_test')
        assert c.post(f'/superadmin/users/{uid}/password',headers=h,json={'password':'Different-Synthetic-2026!','reason':'Test de réinitialisation'}).status_code==200
        assert c.get('/auth/me',headers=agent).status_code==401
        with db() as con:
            audit=' '.join(r['detail_json'] for r in con.execute('SELECT detail_json FROM audit_log').fetchall())
        assert PASSWORD not in audit and 'Different-Synthetic' not in audit

def test_owner_protection_and_delegation():
    with TestClient(app) as c:
        h=setup(c)
        for change in ({'active':False},{'super_admin':False}):
            assert c.put('/superadmin/users/1',headers=h,json=account(**{'super_admin':True,**change})).status_code==409
        assert c.put('/superadmin/users/1',headers=h,json=account(profile_id='direction',super_admin=True)).status_code==422
        assert create(c,h,'invalid_owner',profile_id='direction',super_admin=True).status_code==422
        r=create(c,h,'second_owner',super_admin=True);assert r.status_code==200
        second=auth(c,'second_owner')
        assert c.get('/superadmin',headers=second).status_code==200
        assert c.put('/superadmin/users/1',headers=second,json=account()).status_code==200
        assert c.get('/superadmin',headers=h).status_code==401
        h=auth(c)
        assert c.get('/superadmin',headers=h).status_code==403

def test_configuration_conflict_history_restore_and_whitelist():
    with TestClient(app) as c:
        h=setup(c);initial=c.get('/superadmin',headers=h).json()
        settings={**initial['settings'],'site_name':'Test <script>text</script>','accent':'blue','density':'compact'}
        body={'settings':settings,'expected_version':1,'reason':'Test présentation versionnée'}
        assert c.put('/superadmin/configuration',headers=h,json=body).status_code==200
        assert c.put('/superadmin/configuration',headers=h,json=body).status_code==409
        assert c.get('/platform/config').json()['appearance']==settings
        history=c.get('/superadmin/configuration/history',headers=h).json()['items']
        assert len(history)==2
        old=next(r for r in history if r['version']==1)
        assert c.post('/superadmin/configuration/'+old['id']+'/restore',headers=h,json={'expected_version':2,'reason':'Retour à la présentation initiale'}).status_code==200
        assert c.get('/platform/config').json()['appearance']==initial['settings']
        assert c.put('/superadmin/configuration',headers=h,json={**body,'expected_version':3,'settings':{**settings,'accent':'url(https://bad.invalid)'}}).status_code==422
        assert c.put('/superadmin/configuration',headers=h,json={**body,'expected_version':3,'settings':{**settings,'javascript':'alert(1)'}}).status_code==422
        assert len(c.get('/superadmin/configuration/history',headers=h).json()['items'])==3

def test_reset_and_revoke_require_owner_and_reason():
    with TestClient(app) as c:
        h=setup(c);uid=create(c,h).json()['id'];tech=auth(c,'tech_test')
        assert c.post(f'/superadmin/users/{uid}/revoke-sessions',headers=tech,json={'reason':'Test refus accès'}).status_code==403
        assert c.post(f'/superadmin/users/{uid}/revoke-sessions',headers=h,json={'reason':'x'}).status_code==422
        assert c.post(f'/superadmin/users/{uid}/revoke-sessions',headers=h,json={'reason':'Test fermeture des sessions'}).status_code==200
        assert c.get('/auth/me',headers=tech).status_code==401
