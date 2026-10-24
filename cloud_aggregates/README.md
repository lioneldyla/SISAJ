# SISA Cloud Aggregate Gateway

Separate FastAPI service that stores only approved aggregates. It is not the case-management application.

## Local checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```

The four contract tests do not require a live PostgreSQL database. To run the service locally, configure `DATABASE_URL` and `SISA_AGGREGATE_INGEST_KEY`, then run `uvicorn app.main:app --reload --port 8000` from this directory.

## Production boundary

- Requires PostgreSQL (`DATABASE_URL`, Neon is a candidate provider).
- Requires a long random ingestion secret (`SISA_AGGREGATE_INGEST_KEY`).
- Default public suppression threshold is 5.
- No case-level API, no people, no case numbers, no document upload.
- No synchronization is performed by this service itself.
- Do not enable public publication before institutional approval and security review.
