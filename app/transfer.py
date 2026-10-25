"""Technical document deposit and reversible cancellation of untouched PPEF drafts."""
import base64
import hashlib
import io
import json
import uuid
import time
from pathlib import PurePath
from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

SCHEMA = '''
CREATE TABLE IF NOT EXISTS transfer_archives(batch_id TEXT PRIMARY KEY REFERENCES registry_batches(id), payload TEXT NOT NULL, reversed_at TEXT NOT NULL, reversed_by INTEGER NOT NULL REFERENCES users(id), reason TEXT NOT NULL, restored_at TEXT);
CREATE TABLE IF NOT EXISTS reference_documents(id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT UNIQUE NOT NULL, original_base64 TEXT NOT NULL, purpose TEXT NOT NULL, uploaded_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
'''

class Reason(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)

class Reverse(Reason):
    fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')

def install(app, db, audit, utcnow, user_from_token, require_roles):
    with db() as c:
        c.executescript(SCHEMA)

    def snapshot(c, bid, lock=False):
        from .main import DATABASE_URL
        tail = ' FOR UPDATE' if lock and DATABASE_URL else ''
        batch = c.execute('SELECT id FROM registry_batches WHERE id=?'+tail,(bid,)).fetchone()
        if not batch: raise HTTPException(404, 'Lot PPEF introuvable')
        archived = c.execute('SELECT restored_at FROM transfer_archives WHERE batch_id=?',(bid,)).fetchone()
        if archived and not archived['restored_at']: raise HTTPException(409, 'Lot déjà annulé')
        cases = [dict(r) for r in c.execute('SELECT * FROM cases WHERE source_batch=? ORDER BY id'+tail,(bid,)).fetchall()]
        blocked=[];records=[];sources=[]
        for case in cases:
            cid=case['id']
            if case['status']!='draft' or case['version']!=2: blocked.append({'id':cid,'reason':'Dossier modifié ou engagé dans le circuit'})
            for table in ('case_events','case_profiles','case_people','case_offences','case_decisions','case_measures'):
                if c.execute(f'SELECT case_id FROM {table} WHERE case_id=?',(cid,)).fetchone(): blocked.append({'id':cid,'reason':'Données complémentaires présentes'});break
            records.extend(dict(r) for r in c.execute('SELECT * FROM registry_records WHERE case_id=?',(cid,)).fetchall())
            sources.extend(dict(r) for r in c.execute('SELECT * FROM registry_source_rows WHERE case_id=? ORDER BY id',(cid,)).fetchall())
        data={'cases':cases,'records':records,'sources':sources}
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        return data,blocked,digest

    @app.get('/registry/batches')
    def batches(u=Depends(require_roles('admin','supervisor'))):
        with db() as c:
            rows=c.execute('SELECT b.id,b.filename,b.created_at,b.sha256,a.reversed_at,a.restored_at FROM registry_batches b LEFT JOIN transfer_archives a ON a.batch_id=b.id ORDER BY b.created_at DESC LIMIT 100').fetchall()
            items=[]
            for row in rows:
                item=dict(row)
                meta=c.execute('SELECT i.row_count,i.imported_count,u.username FROM import_batches i JOIN users u ON u.id=i.imported_by WHERE i.id=?',(item['id'],)).fetchone()
                if meta:item.update(dict(meta))
                records=c.execute('SELECT r.payload FROM registry_records r JOIN cases c ON c.id=r.case_id WHERE c.source_batch=?',(item['id'],)).fetchall()
                item['people_created']=sum(len(json.loads(r['payload'])['people']) for r in records)
                item['decisions_created']=sum(len(json.loads(r['payload'])['decisions']) for r in records)
                item['rejected_rows']=0;item['duplicate_rows_grouped']=max(0,item.get('row_count',0)-item.get('imported_count',0))
                items.append(item)
            return {'items':items}

    @app.get('/registry/imports/previews/{pid}/report')
    def preview_report(pid:str,u=Depends(require_roles('admin','supervisor','collector'))):
        with db() as c:
            row=c.execute('SELECT * FROM registry_previews WHERE id=?',(pid,)).fetchone()
            if not row or row['created_at']<int(time.time())-1800:raise HTTPException(404,'Contrôle absent ou expiré')
            if row['user_id']!=u['id']:raise HTTPException(403,'Contrôle créé par un autre utilisateur')
            r=json.loads(row['payload'])['result']
            report={k:r[k] for k in ('source_sheet','total_rows','dossier_count','coverage','errors','warnings','file_sha256')}
        return StreamingResponse(io.BytesIO(json.dumps(report,ensure_ascii=False).encode()),media_type='application/json',headers={'Content-Disposition':'attachment; filename="rapport_controle_import.json"'})

    @app.get('/registry/batches/{bid}/reversal-preview')
    def reversal_preview(bid:str,u=Depends(require_roles('admin','supervisor'))):
        with db() as c:
            data,blocked,digest=snapshot(c,bid)
        return {'batch_id':bid,'dossiers':len(data['cases']),'people':sum(len(json.loads(r['payload'])['people']) for r in data['records']),'decisions':sum(len(json.loads(r['payload'])['decisions']) for r in data['records']),'items':[{'id':x['id'],'rp_number':x['rp_number'],'status':x['status'],'version':x['version']} for x in data['cases']],'blocked':blocked,'can_reverse':bool(data['cases']) and not blocked,'fingerprint':digest}

    @app.get('/registry/batches/{bid}/report')
    def batch_report(bid:str,u=Depends(require_roles('admin','supervisor'))):
        with db(write=True) as c:
            b=c.execute('SELECT id,filename,created_at,sha256,manifest FROM registry_batches WHERE id=?',(bid,)).fetchone()
            if not b:raise HTTPException(404,'Lot introuvable')
            info=dict(b);info['manifest']=json.loads(info['manifest'])
            info['cases']=[dict(r) for r in c.execute('SELECT id,rp_number,status,version FROM cases WHERE source_batch=? ORDER BY id',(bid,)).fetchall()]
            info['corrections']=[dict(r) for r in c.execute("SELECT a.created_at,a.action,a.entity_id,a.detail_json FROM audit_log a JOIN cases c ON a.entity_id=CAST(c.id AS TEXT) WHERE c.source_batch=? AND a.entity_type IN ('case','register') ORDER BY a.created_at",(bid,)).fetchall()]
            info['errors']=[];info['note']='Lot confirmé sans erreur bloquante ; avertissements source et historique conservés. Les contrôles avant confirmation restent affichés dans la prévisualisation.'
            audit(c,u['id'],'export','batch_report',bid,{})
        return StreamingResponse(io.BytesIO(json.dumps(info,ensure_ascii=False).encode()),media_type='application/json',headers={'Content-Disposition':'attachment; filename="rapport_lot.json"'})

    @app.post('/registry/batches/{bid}/reverse')
    def reverse(bid:str,x:Reverse,u=Depends(require_roles('admin'))):
        with db(write=True) as c:
            data,blocked,digest=snapshot(c,bid,True)
            if blocked or not data['cases']: raise HTTPException(409,'Annulation bloquée : seuls les brouillons PPEF intacts peuvent être retirés')
            if digest!=x.fingerprint: raise HTTPException(409,'Lot modifié ; refaire le contrôle')
            now=utcnow();payload=json.dumps(data,ensure_ascii=False)
            previous=c.execute('SELECT batch_id FROM transfer_archives WHERE batch_id=?',(bid,)).fetchone()
            if previous:c.execute('UPDATE transfer_archives SET payload=?,reversed_at=?,reversed_by=?,reason=?,restored_at=NULL WHERE batch_id=?',(payload,now,u['id'],x.reason,bid))
            else:c.execute('INSERT INTO transfer_archives VALUES (?,?,?,?,?,NULL)',(bid,payload,now,u['id'],x.reason))
            for case in data['cases']:
                cid=case['id']
                c.execute('DELETE FROM registry_source_rows WHERE case_id=?',(cid,))
                c.execute('DELETE FROM registry_records WHERE case_id=?',(cid,))
                c.execute('DELETE FROM cases WHERE id=?',(cid,))
            audit(c,u['id'],'reverse','registry_batch',bid,{'reason':x.reason,'dossiers':len(data['cases']),'fingerprint':digest})
        return {'status':'reversed','dossiers':len(data['cases']),'recoverable':True}

    @app.post('/registry/batches/{bid}/restore')
    def restore(bid:str,x:Reason,u=Depends(require_roles('admin'))):
        from .main import DATABASE_URL
        with db(write=True) as c:
            # Same batch-first lock order as reverse; serialize reimports against restore.
            batch=c.execute('SELECT id FROM registry_batches WHERE id=?'+(' FOR UPDATE' if DATABASE_URL else ''),(bid,)).fetchone()
            if not batch:raise HTTPException(404,'Lot introuvable')
            if DATABASE_URL:c.execute('SELECT pg_advisory_xact_lock(731026)')
            row=c.execute('SELECT * FROM transfer_archives WHERE batch_id=?',(bid,)).fetchone()
            if not row or row['restored_at']:raise HTTPException(409,'Aucun lot annulé à rétablir')
            data=json.loads(row['payload'])
            for case in data['cases']:
                if c.execute('SELECT id FROM cases WHERE id=? OR (LOWER(rp_number)=? AND rp_year=?)',(case['id'],case['rp_number'].lower(),case['rp_year'])).fetchone():raise HTTPException(409,'Identifiant ou RP réutilisé ; aucun écrasement autorisé')
            for table,key in [('cases','cases'),('registry_records','records'),('registry_source_rows','sources')]:
                for record in data[key]:
                    fields=list(record)
                    c.execute(f'INSERT INTO {table} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})',tuple(record.values()))
            c.execute('UPDATE transfer_archives SET restored_at=? WHERE batch_id=?',(utcnow(),bid))
            audit(c,u['id'],'restore','registry_batch',bid,{'reason':x.reason,'dossiers':len(data['cases'])})
        return {'status':'restored','dossiers':len(data['cases'])}

    @app.post('/registry/documents')
    async def deposit(file:UploadFile=File(...),purpose:str=Form(...),u=Depends(require_roles('admin','supervisor'))):
        if purpose not in ('reference','technical_test'):raise HTTPException(422,'Usage : reference ou technical_test')
        content=await file.read(15*1024*1024+1)
        if not content or len(content)>15*1024*1024:raise HTTPException(422,'Document vide ou supérieur à 15 Mo')
        name=PurePath((file.filename or 'document').replace('\\','/')).name[:200]
        sha=hashlib.sha256(content).hexdigest()
        with db(write=True) as c:
            old=c.execute('SELECT id FROM reference_documents WHERE sha256=?',(sha,)).fetchone()
            if old:return {'id':old['id'],'status':'already_present','creates_cases':False}
            did=str(uuid.uuid4())
            c.execute('INSERT INTO reference_documents VALUES (?,?,?,?,?,?,?)',(did,name,sha,base64.b64encode(content).decode(),purpose,u['id'],utcnow()))
            audit(c,u['id'],'deposit','reference_document',did,{'sha256':sha,'purpose':purpose,'filename':name})
        return {'id':did,'status':'stored','creates_cases':False}

    @app.get('/registry/documents')
    def documents(u=Depends(require_roles('admin','supervisor'))):
        with db() as c:return {'items':[dict(r) for r in c.execute('SELECT id,filename,sha256,purpose,created_at FROM reference_documents ORDER BY created_at DESC LIMIT 200').fetchall()]}

    @app.get('/registry/documents/{did}/source')
    def document(did:str,u=Depends(require_roles('admin','supervisor'))):
        with db(write=True) as c:
            row=c.execute('SELECT * FROM reference_documents WHERE id=?',(did,)).fetchone()
            if not row:raise HTTPException(404,'Document introuvable')
            content=base64.b64decode(row['original_base64'])
            if hashlib.sha256(content).hexdigest()!=row['sha256']:raise HTTPException(409,'Intégrité du document non vérifiée')
            audit(c,u['id'],'export','reference_document',did,{})
        return StreamingResponse(io.BytesIO(content),media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="document_source.bin"','X-Content-Type-Options':'nosniff'})
