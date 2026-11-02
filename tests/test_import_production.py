"""Import boundaries and the complete 1,500-case test lifecycle."""
import csv
import io

import pytest
from fastapi.testclient import TestClient
from app.main import app, db
from app.ppef_import import preview

FIELDS = ['rp_number', 'rp_year', 'date_rp', 'provenance', 'transnational',
          'category', 'ri_number', 'person_physical_count', 'person_legal_count']


def csv_bytes(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def case(number=1):
    return dict(zip(FIELDS, [f'TEST-SYNTH-{number:05d}', 2026, '2026-01-15',
                            'Unité fictive', 'Non', 'Qualification fictive',
                            f'RI-TEST-{number}', 1, 0]))


@pytest.mark.parametrize('field,value', [
    ('rp_number', 'R' * 101), ('rp_year', 1899),
    ('category', 'C' * 251), ('provenance', 'P' * 251),
    ('person_physical_count', 2147483648), ('person_legal_count', -1),
])
def test_invalid_headers_block_confirmation(field, value):
    row = case()
    row[field] = value
    if field == 'rp_year':
        row['date_rp'] = '1899-01-15'
    with TestClient(app) as client:
        headers = login(client)
        response = client.post('/registry/imports/preview', headers=headers,
                               files={'file': ('test.csv', csv_bytes([row]))})
        assert response.status_code == 200
        result = response.json()
        assert result['error_count'] == 1 and not result['can_confirm']
        assert client.post(f"/registry/imports/{result['preview_id']}/confirm",
                           headers=headers).status_code == 422
        assert client.get('/cases', headers=headers).json()['total'] == 0


def login(client):
    credentials = {'username': 'import_production_test',
                   'password': 'Synthetic-Production-Test-2026!'}
    assert client.post('/auth/bootstrap', json=credentials).status_code == 200
    return {'Authorization': 'Bearer ' + client.post('/auth/login', json=credentials).json()['access_token']}


def test_malformed_csv_and_limits_are_validation_errors():
    with pytest.raises(ValueError, match='CSV illisible'):
        preview('test.csv', b'rp_number,date_rp\n"unterminated,2026-01-15')
    with pytest.raises(ValueError, match='10 000'):
        preview('test.csv', b'rp_number,date_rp\n' + b'TEST,2026-01-15\n' * 10001)
    with pytest.raises(ValueError, match='256'):
        preview('test.csv', (','.join(['x'] * 257) + '\n').encode())


def test_1500_cases_import_repeat_reverse_restore():
    content = csv_bytes([case(i) for i in range(1500)])
    with TestClient(app) as client:
        headers = login(client)
        response = client.post('/registry/imports/preview', headers=headers,
                               files={'file': ('synthetic.csv', content)})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['can_confirm'] and result['valid_rows'] == 1500
        assert client.get('/cases', headers=headers).json()['total'] == 0
        response = client.post(f"/registry/imports/{result['preview_id']}/confirm", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()['imported_rows'] == 1500
        batch = response.json()['batch_id']
        with db() as con:
            assert con.execute('SELECT COUNT(*) n FROM registry_source_rows WHERE batch_id=?', (batch,)).fetchone()['n'] == 1500
            assert con.execute("SELECT COUNT(*) n FROM cases WHERE status='draft'").fetchone()['n'] == 1500
        assert client.get(f'/registry/imports/{batch}/source', headers=headers).content == content
        repeated = client.post('/registry/imports/preview', headers=headers,
                               files={'file': ('synthetic.csv', content)}).json()
        assert repeated['error_count'] == 1500 and not repeated['can_confirm']
        assert client.post(f"/registry/imports/{repeated['preview_id']}/confirm", headers=headers).status_code == 422
        state = client.get(f'/registry/batches/{batch}/reversal-preview', headers=headers).json()
        assert state['can_reverse']
        response = client.post(f'/registry/batches/{batch}/reverse', headers=headers,
                               json={'reason': 'Annulation du test synthétique', 'fingerprint': state['fingerprint']})
        assert response.status_code == 200, response.text
        assert client.get('/cases', headers=headers).json()['total'] == 0
        response = client.post(f'/registry/batches/{batch}/restore', headers=headers,
                               json={'reason': 'Restauration du test synthétique'})
        assert response.status_code == 200, response.text
        assert client.get('/cases', headers=headers).json()['total'] == 1500
