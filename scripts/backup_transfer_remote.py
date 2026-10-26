"""Run inside the existing Render service; target URL on stdin, never logged.
Creates a NEW database on the existing backup server. Source is read-only.
No remote source URL is accepted: source is the service DATABASE_URL.
"""
import ast,base64,hashlib,io,json,os,re,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

target=sys.stdin.readline().strip();source=os.environ['DATABASE_URL']
srcinfo=conninfo_to_dict(source);dstinfo=conninfo_to_dict(target)
assert 'dpg-dbeqoeom7kps73eovnqg-a' in dstinfo['host'],'Unexpected backup server'
assert srcinfo['host']!=dstinfo['host'],'Backup must use another server'
name='sisa_pre_transfer_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
with psycopg.connect(target,autocommit=True) as admin:
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
dstinfo['dbname']=name
schema=[]
for path in ('app/main.py','app/legal.py','app/registry.py','app/transfer.py','app/access.py','app/compliance.py','app/superadmin.py','app/followup.py','app/qualification.py'):
    if not Path(path).exists():continue
    tree=ast.parse(Path(path).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCHEMA' for t in n.targets))
    schema.append(re.sub(r'\bid INTEGER PRIMARY KEY\b','id SERIAL PRIMARY KEY',ast.literal_eval(node.value)))
archive=Path('/tmp')/(name+'.zip');proof={'source_read_only':True,'target_database':name,'tables':{},'verified':False}
def table_bytes(c,table):
    buf=io.BytesIO()
    with c.cursor().copy(sql.SQL('COPY {} TO STDOUT (FORMAT BINARY)').format(sql.Identifier(table))) as stream:
        for chunk in stream:buf.write(chunk)
    return buf.getvalue()
def canonical(c,table):
    rows=c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall()
    return sorted(json.dumps(r,default=str,ensure_ascii=False) for r in rows)
with psycopg.connect(source) as src,psycopg.connect(**dstinfo) as dst,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    src.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
    tables=[r[0] for r in src.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
    assert {'cases','users','registry_records'}<=set(tables),'Unexpected source schema'
    ddl='\n'.join(schema);z.writestr('schema.sql',ddl)
    for script in schema:
        for statement in script.split(';'):
            if statement.strip() and not statement.strip().startswith('PRAGMA '):dst.execute(statement)
    restored_tables=[r[0] for r in dst.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
    assert tables==restored_tables,'Backup schema does not match the deployed tables'
    pending=set(tables);order=[]
    # Child tables follow parents; constraints remain enforced during restoration.
    while pending:
        ready=[]
        for t in sorted(pending):
            parents={r[0] for r in src.execute("SELECT ccu.table_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name=ccu.constraint_name AND tc.constraint_schema=ccu.constraint_schema WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public' AND tc.table_name=%s",(t,)).fetchall()}
            if not parents.intersection(pending):ready.append(t)
        assert ready,'Foreign key cycle requires reviewed backup plan'
        for t in ready:pending.remove(t);order.append(t)
    for t in order:
        data=table_bytes(src,t);z.writestr(t+'.copy',data)
        with dst.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier(t))) as stream:stream.write(data)
        assert canonical(src,t)==canonical(dst,t),t
        proof['tables'][t]=len(canonical(src,t))
    sequences=src.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename").fetchall();seq=[]
    for (n,) in sequences:
        val,called=src.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(n))).fetchone()
        dst.execute('SELECT setval(%s,%s,%s)',(n,val,called));seq.append((n,val,called))
    z.writestr('sequences.json',json.dumps(seq));dst.commit()
    with psycopg.connect(**dstinfo) as check:
        for t in tables:assert canonical(src,t)==canonical(check,t),t
        for n,val,called in seq:assert check.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(n))).fetchone()==(val,called)
proof.update(verified=True,sequences_verified=True,committed_restore_verified=True,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
Path('/tmp/sisa_transfer_backup_proof.json').write_text(json.dumps(proof,indent=2))
print('SISA_TRANSFER_BACKUP_VERIFIED',json.dumps(proof))
