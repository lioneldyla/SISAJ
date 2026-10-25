"""Upgrade an independently created v0.3 database and compare its original rows."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from app.main import SCHEMA, pw_hash


def test_additive_startup_preserves_all_legacy_tables(tmp_path):
    path=tmp_path/'legacy.db'
    with sqlite3.connect(path) as c:
        c.executescript(SCHEMA)
        c.execute('INSERT INTO users VALUES(1,?,?,?,?,?)',('legacy_admin',pw_hash('Synthetic-Migration-2026!'),'admin',1,'2026-01-01'))
        c.execute('INSERT INTO cases(id,rp_number,rp_year,date_rp,provenance,transnational,category,status,version,created_by,updated_by,created_at,updated_at) VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?)',('SYNTH-LEGACY',2026,'2026-01-01','Fictif',0,'Source historique fictive','draft',7,1,1,'2026-01-01','2026-01-01'))
        c.execute("INSERT INTO indicator_definitions VALUES ('received_cases','Dossiers reçus','dossier distinct','date RP','draft-v0.2',0)")
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        before={table:c.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall() for table in tables}
    result=subprocess.run([sys.executable,'-c','import app.main'],cwd=Path(__file__).resolve().parent.parent,env={**os.environ,'DATABASE_URL':'','SISA_DEPLOYMENT':'local','SISA_DB_PATH':str(path),'SISA_BACKUP_DIR':str(tmp_path/'backups')},capture_output=True)
    assert result.returncode==0,result.stderr.decode()
    with sqlite3.connect(path) as c:
        assert {table:c.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall() for table in tables}==before
        assert c.execute('SELECT version FROM schema_migrations').fetchall()==[('004-legal-additive',)]
        assert c.execute('SELECT COUNT(*) FROM case_people').fetchone()[0]==0
