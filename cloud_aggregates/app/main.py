"""SISA hosted aggregate gateway. Never stores case-level data."""
from __future__ import annotations
import hashlib, hmac, os
from datetime import date, datetime, timezone
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Query, Depends
from pydantic import BaseModel, Field, ConfigDict
import psycopg
from psycopg.rows import dict_row

APP_VERSION = "0.2.0-hosted-aggregate-gateway"
DATABASE_URL = os.getenv("DATABASE_URL", "")
INGEST_KEY = os.getenv("SISA_AGGREGATE_INGEST_KEY", "")
MIN_PUBLIC_VALUE = int(os.getenv("SISA_MIN_PUBLIC_VALUE", "5"))
@asynccontextmanager
async def lifespan(_app):
    if DATABASE_URL:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            conn.execute(DDL)
    yield

app = FastAPI(title="SISA — Passerelle d'agrégats autorisés", version=APP_VERSION,
              description="Ne stocke que des agrégats explicitement autorisés; aucun dossier individuel.", lifespan=lifespan)

DDL = """
CREATE TABLE IF NOT EXISTS approved_aggregates (
 id BIGSERIAL PRIMARY KEY,
 indicator_code TEXT NOT NULL CHECK(length(indicator_code) BETWEEN 1 AND 80),
 period_start DATE NOT NULL,
 period_end DATE NOT NULL,
 dimension_code TEXT NOT NULL CHECK(length(dimension_code) BETWEEN 1 AND 80),
 dimension_value TEXT NOT NULL CHECK(length(dimension_value) BETWEEN 1 AND 120),
 value NUMERIC(18,2) NOT NULL CHECK(value >= 0),
 unit TEXT NOT NULL CHECK(length(unit) BETWEEN 1 AND 40),
 method_version TEXT NOT NULL CHECK(length(method_version) BETWEEN 1 AND 80),
 approval_reference TEXT NOT NULL CHECK(length(approval_reference) BETWEEN 1 AND 120),
 approved_by TEXT NOT NULL CHECK(length(approved_by) BETWEEN 1 AND 120),
 approved_at TIMESTAMPTZ NOT NULL,
 publication_status TEXT NOT NULL CHECK(publication_status IN ('internal','public')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(period_start <= period_end),
 UNIQUE(indicator_code, period_start, period_end, dimension_code, dimension_value, method_version)
);
CREATE INDEX IF NOT EXISTS idx_aggregates_public_period ON approved_aggregates(publication_status, period_start, period_end);
"""

class AggregateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    indicator_code: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    period_start: date
    period_end: date
    dimension_code: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    dimension_value: str = Field(min_length=1, max_length=120)
    value: float = Field(ge=0, le=1_000_000_000_000)
    unit: str = Field(min_length=1, max_length=40)
    method_version: str = Field(min_length=1, max_length=80)
    approval_reference: str = Field(min_length=1, max_length=120)
    approved_by: str = Field(min_length=1, max_length=120)
    approved_at: datetime
    publication_status: Literal["internal", "public"] = "internal"

    def safe(self):
        d = self.model_dump()
        if d["period_start"] > d["period_end"]:
            raise HTTPException(422, "La période de début doit précéder la période de fin.")
        if d["approved_at"].tzinfo is None:
            raise HTTPException(422, "approved_at doit inclure un fuseau horaire.")
        if d["publication_status"] == "public" and d["value"] < MIN_PUBLIC_VALUE:
            raise HTTPException(422, f"Valeur supprimée de la publication publique : seuil minimal {MIN_PUBLIC_VALUE}.")
        # Limit text fields to avoid accidentally placing names or case identifiers in dimension values.
        for field in ("dimension_value", "approval_reference", "approved_by", "unit", "method_version"):
            if any(c in str(d[field]) for c in "\r\n\t"):
                raise HTTPException(422, f"Caractères de contrôle interdits dans {field}.")
        return d

def get_db():
    if not DATABASE_URL:
        raise HTTPException(503, "DATABASE_URL non configurée.")
    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5)
    except Exception as exc:
        raise HTTPException(503, "Base de données indisponible.") from exc
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def require_ingest_key(x_sisa_ingest_key: str | None = Header(default=None)):
    if not INGEST_KEY:
        raise HTTPException(503, "Clé d'ingestion non configurée.")
    if not x_sisa_ingest_key or not hmac.compare_digest(hashlib.sha256(x_sisa_ingest_key.encode()).digest(), hashlib.sha256(INGEST_KEY.encode()).digest()):
        raise HTTPException(401, "Clé d'ingestion invalide.")

@app.get("/health")
def health():
    return {"status": "ok", "app": "SISA", "version": APP_VERSION, "scope": "aggregates_only", "case_level_data": False}

@app.post("/aggregates", dependencies=[Depends(require_ingest_key)], status_code=201)
def ingest(payload: AggregateIn, conn=Depends(get_db)):
    d = payload.safe()
    query = """INSERT INTO approved_aggregates
    (indicator_code,period_start,period_end,dimension_code,dimension_value,value,unit,method_version,approval_reference,approved_by,approved_at,publication_status)
    VALUES (%(indicator_code)s,%(period_start)s,%(period_end)s,%(dimension_code)s,%(dimension_value)s,%(value)s,%(unit)s,%(method_version)s,%(approval_reference)s,%(approved_by)s,%(approved_at)s,%(publication_status)s)
    ON CONFLICT(indicator_code,period_start,period_end,dimension_code,dimension_value,method_version)
    DO UPDATE SET value=EXCLUDED.value, unit=EXCLUDED.unit, approval_reference=EXCLUDED.approval_reference,
    approved_by=EXCLUDED.approved_by, approved_at=EXCLUDED.approved_at, publication_status=EXCLUDED.publication_status
    RETURNING id, indicator_code, period_start, period_end, dimension_code, dimension_value, value, unit, method_version, publication_status, created_at"""
    with conn.cursor() as cur:
        cur.execute(query, d); row = cur.fetchone()
    return dict(row)

@app.get("/aggregates/public")
def public_aggregates(start: date | None = None, end: date | None = None,
                      indicator_code: str | None = Query(default=None, max_length=80), conn=Depends(get_db)):
    clauses = ["publication_status='public'", "value >= %s"]
    params: list = [MIN_PUBLIC_VALUE]
    if start: clauses.append("period_end >= %s"); params.append(start)
    if end: clauses.append("period_start <= %s"); params.append(end)
    if indicator_code: clauses.append("indicator_code = %s"); params.append(indicator_code)
    sql = "SELECT indicator_code,period_start,period_end,dimension_code,dimension_value,value,unit,method_version FROM approved_aggregates WHERE " + " AND ".join(clauses) + " ORDER BY period_start,indicator_code,dimension_code,dimension_value"
    with conn.cursor() as cur:
        cur.execute(sql, params); rows = cur.fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows], "warning": "Agrégats publics autorisés uniquement; les règles statistiques et la publication restent sous responsabilité humaine."}

@app.get("/admin/aggregates", dependencies=[Depends(require_ingest_key)])
def internal_aggregates(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id,indicator_code,period_start,period_end,dimension_code,dimension_value,value,unit,method_version,approval_reference,approved_by,approved_at,publication_status,created_at FROM approved_aggregates ORDER BY created_at DESC LIMIT 1000")
        rows = cur.fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}
