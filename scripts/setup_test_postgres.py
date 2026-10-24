"""Create/reuse an isolated local synthetic PostgreSQL 16 test container.
Never prints passwords. Stores ephemeral test connection metadata in /tmp, mode 0600.
"""
import json
from pathlib import Path
import secrets
import subprocess
import time
from urllib.parse import urlsplit

path=Path('/tmp/sisa-postgres-test.json')
inspect=subprocess.run(['docker','inspect','sisa-postgres-test'],capture_output=True)
if path.exists():
    url=json.loads(path.read_text())['url']
    parts=urlsplit(url)
    assert parts.hostname=='127.0.0.1' and parts.path=='/sisa_test' and parts.port==55432
    password=parts.password
else:
    if inspect.returncode==0: raise RuntimeError('Existing container has no matching test configuration; refusing to replace it.')
    password=secrets.token_urlsafe(32)
    url='postgresql://sisa:'+password+'@127.0.0.1:55432/sisa_test'
if inspect.returncode:
    result=subprocess.run(['docker','run','-d','--name','sisa-postgres-test','--memory','512m','--cpus','2',
       '-e','POSTGRES_USER=sisa','-e','POSTGRES_DB=sisa_test','-e','POSTGRES_PASSWORD='+password,
       '-p','127.0.0.1:55432:5432','postgres:16-alpine'],capture_output=True)
    if result.returncode: raise RuntimeError('Could not start isolated PostgreSQL test container.')
else:
    subprocess.run(['docker','start','sisa-postgres-test'],check=True,stdout=subprocess.DEVNULL)
path.write_text(json.dumps({'url':url}));path.chmod(0o600)
for _ in range(100):
    result=subprocess.run(['docker','exec','sisa-postgres-test','pg_isready','-U','sisa','-d','sisa_test'],capture_output=True)
    if result.returncode==0:
        print('Isolated synthetic PostgreSQL ready on loopback; credentials stored only in a restricted /tmp file.')
        break
    time.sleep(.2)
else: raise RuntimeError('PostgreSQL startup timeout')
