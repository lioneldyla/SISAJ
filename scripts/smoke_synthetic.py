"""Start both APIs on loopback, verify responses, then stop only these processes.
No external service or real judicial data is used. Run from the repository root.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent


def check_component(directory, extra_env, expected, protected_path, protected_status):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryFile(mode='w+') as log:
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
            cwd=directory, env={**os.environ, **extra_env}, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                        health = json.load(response)
                    break
                except (URLError, TimeoutError):
                    if proc.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    time.sleep(0.1)
            else:
                raise RuntimeError('Startup timeout')
            for key, value in expected.items():
                assert health[key] == value, health
            try:
                urlopen(f'http://127.0.0.1:{port}{protected_path}', timeout=5)
            except HTTPError as error:
                assert error.code == protected_status, error.code
            else:
                raise AssertionError('Expected protected or unavailable endpoint')
            print(directory.name, 'health verified;', protected_path, protected_status, 'verified')
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


with tempfile.TemporaryDirectory(prefix='sisa-smoke-synthetic-') as tmp:
    check_component(ROOT, {'DATABASE_URL': '', 'SISA_DEPLOYMENT': 'local', 'SISA_BOOTSTRAP_KEY': '', 'SISA_DB_PATH': str(Path(tmp)/'synthetic.db'),
                          'SISA_BACKUP_DIR': str(Path(tmp)/'backups')},
                    {'status': 'ok', 'cloud_sync': 'disabled', 'external_ai': 'disabled'}, '/cases', 401)
    # Deliberately no PostgreSQL or ingestion secret: fail closed, never connect externally.
    check_component(ROOT/'cloud_aggregates', {'DATABASE_URL': '', 'SISA_AGGREGATE_INGEST_KEY': ''},
                    {'status': 'ok', 'case_level_data': False}, '/aggregates/public', 503)
