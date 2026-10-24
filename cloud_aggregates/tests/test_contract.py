import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SISA_AGGREGATE_INGEST_KEY','test-key')
# The contract tests do not need a live PostgreSQL driver or database.
try:
    import psycopg  # noqa: F401
except ImportError:
    fake = types.ModuleType('psycopg')
    fake.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('DB not used in contract tests'))
    rows = types.ModuleType('psycopg.rows'); rows.dict_row = object()
    sys.modules['psycopg'] = fake; sys.modules['psycopg.rows'] = rows
from app.main import AggregateIn
from fastapi import HTTPException
from datetime import date, datetime, timezone
import pytest

def payload(**overrides):
    d=dict(indicator_code='received_cases',period_start=date(2026,1,1),period_end=date(2026,12,31),dimension_code='year',dimension_value='2026',value=12,unit='dossier',method_version='draft-v1',approval_reference='DEC-TEST-001',approved_by='responsable_test',approved_at=datetime.now(timezone.utc),publication_status='internal')
    d.update(overrides); return d

def test_unknown_fields_rejected():
    with pytest.raises(Exception): AggregateIn(**payload(case_name='Jean'))

def test_period_order_rejected():
    x=AggregateIn(**payload(period_start=date(2027,1,1)))
    with pytest.raises(HTTPException): x.safe()

def test_public_small_value_suppressed(monkeypatch):
    monkeypatch.setattr('app.main.MIN_PUBLIC_VALUE',5)
    x=AggregateIn(**payload(value=4,publication_status='public'))
    with pytest.raises(HTTPException): x.safe()

def test_internal_aggregate_valid():
    assert AggregateIn(**payload()).safe()['indicator_code']=='received_cases'
