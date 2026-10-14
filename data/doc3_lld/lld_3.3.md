# DOC 3.3 — Low Level Design: Query & Analytics API

## 1. Scope

Detailed design of the serving tier of the ADMP: the Query & Analytics API that retrieves
curated aircraft data and supports large asynchronous exports. Realises FR-6, FR-9, IF-4
and acceptance criteria AC-2 and AC-4, under NFR-1 and NFR-3. Conforms to the HLD
"Query & Analytics API" component and feeds the "Dashboards".

## 2. Module structure

- `api/app.py` — REST application (JSON over HTTPS), OIDC token middleware.
- `api/auth.py` — token validation and RBAC enforcement (NFR-3, AC-2).
- `api/query/service.py` — resolves filters via the catalog, reads curated partitions.
- `api/query/planner.py` — chooses partitions from `datapoint_index` to bound scans.
- `api/export/jobs.py` — asynchronous export to object storage (FR-9).
- `api/schemas.py` — request/response models.

## 3. Interfaces (IF-4)

- `GET /flights?tail={tail}&from={ts}&to={ts}` — list flights for a tail + window.
- `GET /data?tail={tail}&flight={id}&parameter={pid}&from={ts}&to={ts}` — data points.
- `POST /exports` — start an async export; returns `export_id`.
- `GET /exports/{export_id}` — export status + signed download URL when ready.
- All endpoints require a valid OIDC bearer token; missing/invalid → **401** (AC-2).

## 4. Sequence

1. `auth` validates the OIDC token and resolves roles; unauthorised requests get 401 with
   no data (**AC-2**, NFR-3).
2. `query.service` uses the catalog (`datapoint_index`) via `planner` to select only the
   partitions covering the requested tail/flight/parameter/time window.
3. Matching curated partitions are read and results returned ordered by timestamp
   (**AC-4**, FR-6).
4. For large result sets, `export/jobs` runs the read asynchronously and writes the output
   to object storage, returning a signed URL (FR-9).

```
client(+token) -> auth (401 if invalid, AC-2)
                    |ok
                  planner -> select partitions (datapoint_index)
                    |
                  read curated -> ordered results (AC-4, FR-6)
large query -> export job -> object storage -> signed URL (FR-9)
```

## 5. Error handling

- 401 unauthenticated / 403 unauthorised (RBAC); 400 invalid query params; 404 unknown
  tail/flight; 413/async path for oversized synchronous queries (redirected to export).

## 6. Non-functional design notes

- **Performance (NFR-1):** partition pruning via the catalog keeps p95 < 500 ms for
  bounded queries; stateless API scales horizontally behind the gateway.
- **Security (NFR-3):** OIDC-authenticated, RBAC-authorised, TLS everywhere; every access
  audit-logged with a correlation id (NFR-5).

## 7. Requirements traceability

| Requirement | How addressed |
|-------------|---------------|
| FR-6 | Filtered retrieval by tail/flight/parameter/time. |
| FR-9 | Async export to object storage. |
| IF-4 | REST endpoints (JSON/HTTPS). |
| AC-2 | 401 on missing/invalid token, no data. |
| AC-4 | Correct, timestamp-ordered results for tail + window. |
| NFR-1 | Partition pruning + stateless scaling. |
| NFR-3 | OIDC + RBAC + TLS + audit. |
