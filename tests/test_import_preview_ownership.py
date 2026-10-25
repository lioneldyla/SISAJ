"""Synthetic regression tests: denied confirmation must never destroy an owner's preview."""
import json
import time

import pytest
from fastapi.testclient import TestClient
from app.main import app, DB_PATH

client = TestClient(app)
PASSWORD = 'Synthetic-Test-Password-2026!'


def headers(username):
    response = client.post('/auth/login', json={'username': username, 'password': PASSWORD})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def preview():
    assert client.post('/auth/bootstrap',headers={'X-SISA-Bootstrap-Key':'Synthetic-Bootstrap-Only-2026!'}, json={'username': 'owner', 'password': PASSWORD}).status_code == 200
    owner = headers('owner')
    assert client.post('/users', headers=owner, json={
        'username': 'other', 'password': PASSWORD, 'role': 'collector'
    }).status_code == 200
    content = b'rp_number,rp_year,date_rp,provenance,transnational,category\nRP-SYNTH,2026,2026-01-01,OPJ fictif,Non,Test fictif\n'
    response = client.post('/imports/preview', headers=owner, files={'file': ('synthetic.csv', content, 'text/csv')})
    assert response.status_code == 200
    assert response.json()['can_confirm'] is True
    pid = response.json()['preview_id']
    return owner, headers('other'), pid, DB_PATH.parent / f'preview_{pid}.json'


@pytest.mark.parametrize('expired', [False, True])
def test_denied_confirmation_preserves_preview(expired):
    owner, other, pid, path = preview()
    if expired:
        payload = json.loads(path.read_text())
        payload['created'] = time.time() - 1801
        path.write_text(json.dumps(payload))
    original = path.read_bytes()
    try:
        response = client.post(f'/imports/{pid}/confirm', headers=other)
        assert response.status_code == 403
        assert path.exists(), 'Denied caller deleted another user\'s preview'
        assert path.read_bytes() == original
        assert client.get('/cases', headers=owner).json()['total'] == 0
        if not expired:
            accepted = client.post(f'/imports/{pid}/confirm', headers=owner)
            assert accepted.status_code == 200
            assert accepted.json()['imported_rows'] == 1
            assert not path.exists()
            assert client.post(f'/imports/{pid}/confirm', headers=owner).status_code == 404
    finally:
        path.unlink(missing_ok=True)


def test_owner_expired_preview_is_removed_without_import():
    owner, _, pid, path = preview()
    payload = json.loads(path.read_text())
    payload['created'] = time.time() - 1801
    path.write_text(json.dumps(payload))
    try:
        assert client.post(f'/imports/{pid}/confirm', headers=owner).status_code == 403
        assert not path.exists()
        assert client.get('/cases', headers=owner).json()['total'] == 0
    finally:
        path.unlink(missing_ok=True)

