import os, tempfile
from pathlib import Path
# Refuse ambient production bindings before importing application modules.
from urllib.parse import urlsplit
if os.environ.get('SISA_TEST_POSTGRES') != '1':
    os.environ['DATABASE_URL'] = ''
else:
    target = urlsplit(os.environ.get('DATABASE_URL', ''))
    if target.hostname != '127.0.0.1' or target.port != 55432 or target.path != '/sisa_test':
        raise RuntimeError('Only the isolated loopback sisa_test database is permitted.')
os.environ['SISA_DEPLOYMENT'] = 'local'
os.environ['SISA_BOOTSTRAP_KEY'] = ''
os.environ['SISA_SECURE_COOKIE'] = '0'
_tmp = tempfile.TemporaryDirectory(prefix='sisa-tests-')
os.environ['SISA_DB_PATH'] = str(Path(_tmp.name) / 'test.db')
os.environ['SISA_BACKUP_DIR'] = str(Path(_tmp.name) / 'backups')
import pytest
@pytest.fixture(autouse=True)
def reset_test_database():
    from app.main import DB_PATH, db, SCHEMA, DATABASE_URL
    if DATABASE_URL:
        if not DATABASE_URL.rstrip('/').endswith('/sisa_test'):
            raise RuntimeError('Les tests PostgreSQL exigent une base dédiée nommée sisa_test.')
        with db() as c:
            c.execute('TRUNCATE users,sessions,cases,case_events,import_batches,audit_log,indicator_definitions,import_previews,login_attempts RESTART IDENTITY CASCADE')
    elif DB_PATH.exists(): DB_PATH.unlink()
    for suffix in ('-wal','-shm'):
        Path(str(DB_PATH)+suffix).unlink(missing_ok=True)
    with db() as c:
        c.executescript(SCHEMA)
        from app.legal import SCHEMA as LEGAL_SCHEMA
        c.executescript(LEGAL_SCHEMA)
        from app.registry import SCHEMA as REGISTRY_SCHEMA
        c.executescript(REGISTRY_SCHEMA)
        from app.transfer import SCHEMA as TRANSFER_SCHEMA
        c.executescript(TRANSFER_SCHEMA)
        from app.access import SCHEMA as ACCESS_SCHEMA
        c.executescript(ACCESS_SCHEMA)
        c.execute('DELETE FROM user_data_profiles')
        c.execute('DELETE FROM transfer_archives')
        c.execute('DELETE FROM reference_documents')
        c.execute('DELETE FROM jurisdictions')
        c.execute("INSERT OR IGNORE INTO indicator_definitions VALUES ('received_cases','Dossiers reçus','dossier distinct','date RP','draft-v0.2',0)")
