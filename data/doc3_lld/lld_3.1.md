# DOC 3.1 — Low Level Design: Ingestion Gateway & Data Validation

## 1. Scope

Detailed design of the ingestion tier of the ADMP: the Ingestion Gateway that terminates
the ACARS, QAR and ADS-B interfaces, and the Stream Processing & Validation stage that
validates records and normalises them into the canonical Aircraft Data Model (ADM).
Realises requirements FR-1, FR-2, FR-3 and acceptance criterion AC-1, under NFR-1, NFR-3,
NFR-5 and NFR-6. Conforms to the HLD "Ingestion Gateway" and "Stream Processing" components.

## 2. Module structure

- `ingest/adapters/acars.py` — ARINC 620 adapter (IF-1); parses ACARS message blocks.
- `ingest/adapters/qar.py` — ARINC 767 upload adapter (IF-2); de-encrypts and unpacks QAR.
- `ingest/adapters/adsb.py` — ADS-B streaming consumer (IF-3).
- `ingest/validation/schema.py` — source-schema and ADM-schema validators (FR-2).
- `ingest/validation/rules.py` — business rules (range checks, required fields).
- `ingest/normalize/mapper.py` — source → ADM mapping, unit normalisation (FR-3).
- `ingest/publish/broker.py` — publishes normalised records to the broker; writes raw.
- `ingest/errors.py` — rejection handling and dead-letter routing.

## 3. Interfaces

- `ingest_record(raw: bytes, source: Source) -> IngestResult` — entry point per record.
- `validate(record: dict, source: Source) -> ValidatedRecord` — raises `ValidationError`.
- `normalize(record: ValidatedRecord) -> ADMRecord` — returns canonical ADM record.
- REST/stream endpoints: `POST /ingest/acars`, `POST /ingest/qar`, ADS-B stream subscriber.

## 4. Sequence

1. Adapter receives data on IF-1/IF-2/IF-3 and writes the as-received bytes to the **Raw
   Zone** immediately (satisfies FR-4 hand-off; preserves source of truth).
2. `validate()` checks the source schema, then the target ADM constraints and business
   rules. On failure the record is routed to the dead-letter store, logged with a reason,
   and NOT forwarded downstream (**AC-1**).
3. `normalize()` maps fields to the ADM, converts units, and resolves parameter ids.
4. `broker.publish()` emits the ADM record to the durable broker topic for the storage
   tier (LLD 3.2) to consume.

```
adapter -> raw-zone write -> validate --(fail)--> dead-letter + log   (AC-1)
                               |(pass)
                             normalize -> broker.publish -> [LLD 3.2]
```

## 5. Validation & error handling

Each validation failure yields `{code, field, message, source_object}`. Multiple failures
are aggregated per record. Dead-lettered records are retained for reprocessing. Adapters
are idempotent on a source-supplied message key so replays do not create duplicates.

## 6. Non-functional design notes

- **Performance (NFR-1):** adapters are stateless and horizontally scaled behind the API
  gateway; validation is CPU-bound and parallelised; target ≥ 50k records/s aggregate.
- **Security (NFR-3):** ingest endpoints require mTLS/OIDC; QAR payloads are de-encrypted
  in-memory; no payloads are written to logs.
- **Observability (NFR-5):** each record carries a correlation id from ingestion onward.
- **Scalability (NFR-6):** containerised; scales on broker lag and CPU.

## 7. Requirements traceability

| Requirement | How addressed |
|-------------|---------------|
| FR-1 | Three source adapters (ACARS/QAR/ADS-B). |
| FR-2 | `validate()` rejects invalid records before Curated Zone. |
| FR-3 | `normalize()` maps to ADM with unit normalisation. |
| IF-1/2/3 | Adapter endpoints/consumer. |
| AC-1 | Dead-letter + log on validation failure; not persisted to Curated. |
| NFR-1/3/5/6 | Stateless scaling, mTLS, correlation ids, containerised. |
