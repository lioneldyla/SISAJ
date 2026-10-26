"""Operator deployment job. Never auto-installs a scheduler and never overwrites a target DB.
Requires PostgreSQL clients matching the source major version; credentials only via env.
"""
import argparse,hashlib,json,os,secrets,subprocess,tempfile
from datetime import datetime,timezone
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from secure_backup import pack

def environment(info):
 env=os.environ.copy()
 for k in ('host','port','user','password','dbname','sslmode','sslrootcert','channel_binding'):
  if k in info:env[{'dbname':'PGDATABASE'}.get(k,'PG'+k.replace('_','').upper())]=info[k]
 return env

def run(folder):
 source=os.environ['SOURCE_DATABASE_URL'];target=os.environ['RESTORE_SERVER_URL'];phrase=os.environ['SISA_BACKUP_PASSPHRASE']
 src=conninfo_to_dict(source);dst=conninfo_to_dict(target)
 if src['host']==dst['host']:raise ValueError('Le serveur de restauration doit être distinct de la source.')
 stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S');name='sisaj_restore_'+stamp+'_'+secrets.token_hex(3)
 folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700)
 counts={};sequences=[]
 with tempfile.TemporaryDirectory(prefix='sisaj-backup-') as tmp,psycopg.connect(source) as s:
  s.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  snapshot=s.execute('SELECT pg_export_snapshot()').fetchone()[0]
  dump=Path(tmp)/'source.dump'
  r=subprocess.run(['pg_dump','--format=custom','--no-owner','--snapshot='+snapshot,'--file='+str(dump)],env=environment(src),capture_output=True)
  if r.returncode:raise RuntimeError('Export PostgreSQL refusé ; détails de connexion masqués.')
  tables=[v[0] for v in s.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
  if not {'users','cases','registry_records'}.issubset(tables):raise ValueError('Schéma source non reconnu.')
  with psycopg.connect(target,autocommit=True) as admin:admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
  restore={**dst,'dbname':name}
  r=subprocess.run(['pg_restore','--no-owner','--no-acl','--single-transaction','--exit-on-error','--dbname='+name,str(dump)],env=environment(restore),capture_output=True)
  if r.returncode:raise RuntimeError('Restauration échouée ; cible isolée conservée pour diagnostic.')
  with psycopg.connect(**restore) as check:
   restored=[v[0] for v in check.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
   if restored!=tables:raise ValueError('Tables restaurées différentes de la source.')
   for t in tables:
    query=sql.SQL('SELECT * FROM {}').format(sql.Identifier(t));canonical=lambda rows:sorted(json.dumps(v,default=str,ensure_ascii=False) for v in rows)
    original=s.execute(query).fetchall();copied=check.execute(query).fetchall()
    if canonical(original)!=canonical(copied):raise ValueError('Comparaison complète des données échouée.')
    counts[t]=len(original)
   for (seq,) in s.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename"):
    query=sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(seq))
    if s.execute(query).fetchone()!=check.execute(query).fetchone():raise ValueError('Séquence différente après restauration.')
    sequences.append(seq)
  encrypted=folder/('sisaj_'+stamp+'.sisaenc');digest=pack(dump,encrypted,phrase)
  receipt={'verified':True,'source_read_only':True,'target_database':name,'tables':counts,'sequences_verified':True,'committed_restore_verified':True,'archive_sha256':digest,'encrypted_archive_sha256':hashlib.sha256(encrypted.read_bytes()).hexdigest(),'created_at':datetime.now(timezone.utc).isoformat(),'retention_note':'Aucune purge automatique ; conservation à approuver.'}
  with (folder/('sisaj_'+stamp+'.receipt.json')).open('x') as f:json.dump(receipt,f,indent=2)
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(run(a.output)))
 except Exception:raise SystemExit('Sauvegarde NON validée. Consulter le diagnostic local sécurisé ; aucune cible existante écrasée.')
