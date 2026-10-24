"""Run applicable API tests against the isolated synthetic PostgreSQL database.
The test fixture truncates only the dedicated sisa_test database between tests.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
url=json.loads(Path('/tmp/sisa-postgres-test.json').read_text())['url']
assert urlsplit(url).hostname=='127.0.0.1' and urlsplit(url).path=='/sisa_test'
root=Path(__file__).resolve().parent.parent
result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_platform.py','tests/test_app.py','-k','not backup'],
    cwd=root,env={**os.environ,'DATABASE_URL':url,'SISA_TEST_POSTGRES':'1','SISA_DEPLOYMENT':'local','SISA_BOOTSTRAP_KEY':''})
raise SystemExit(result.returncode)
