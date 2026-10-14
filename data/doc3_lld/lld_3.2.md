# DOC 3.2 — Low Level Design: Data Lake Storage & Catalog

## 1. Scope

Detailed design of the storage tier of the ADMP: the Raw Zone and Curated Zone of the data
lake, the partitioning and lifecycle policy, and the Metadata & Catalog store that indexes
data and records lineage. Realises FR-4, FR-5, NFR-4, NFR-7 and acceptance criterion AC-5.
Conforms to the HLD "Data Lake" and "Metadata & Catalog Store" components.

## 2. Module structure

- `storage/raw/writer.py` — writes as-received objects to the Raw Zone (immutable).
- `storage/curated/writer.py` — consumes ADM records from the broker; writes columnar,
  partitioned files to the Curated Zone.
- `storage/curated/partition.py` — partition-key strategy and compaction.
- `storage/lifecycle.py` — hot→cold tiering and retention enforcement (NFR-4).
- `catalog/models.py` — `Aircraft`, `Flight`, `ParameterDefinition`, `DataPointIndex`.
- `catalog/lineage.py` — links each curated partition/record to its raw source object.
- `catalog/repository.py` — transactional catalog writes.

## 3. Interfaces

- `write_raw(bytes, source_meta) -> RawObjectRef`.
- `write_curated(records: list[ADMRecord]) -> CuratedBatchRef`.
- `register_lineage(curated_ref, raw_ref) -> None` (AC-5, NFR-7).
- `catalog.upsert_flight(...)`, `catalog.upsert_parameter(...)`.

## 4. Data model

Curated Zone stored as columnar files (e.g. Parquet) partitioned by
`tail_number / date / parameter_group`. Catalog (relational):

- `aircraft(tail_number PK, type, operator)`
- `flight(flight_id PK, tail_number FK, dep, arr, start_ts, end_ts)`
- `parameter_definition(parameter_id PK, name, unit, source, min, max)`
- `datapoint_index(flight_id FK, parameter_id FK, ts_range, curated_ref, raw_ref)`

## 5. Sequence

1. Curated writer consumes an ADM batch from the broker (produced by LLD 3.1).
2. Records are partitioned by `tail_number/date/parameter_group` and written as columnar
   files to the Curated Zone (FR-4).
3. `catalog.repository` upserts flight/parameter rows and inserts `datapoint_index` rows
   in one transaction (FR-5), including `raw_ref` for lineage (AC-5, NFR-7).
4. `lifecycle` moves partitions older than 90 days to the cold tier and enforces the
   7-year retention/expiry (NFR-4).

```
[broker] -> curated.writer -> partition -> Curated Zone (columnar)
                                   |
                                   +-> catalog.repository (flight, param, datapoint_index + raw_ref)
lifecycle: hot(90d) -> cold -> expire at 7y
```

## 6. Non-functional design notes

- **Retention (NFR-4):** lifecycle rules on object storage; catalog marks tier per
  partition; raw retained 7y, curated 7y, hot 90d.
- **Governance/lineage (NFR-7, AC-5):** every `datapoint_index` row carries `raw_ref`;
  Curated is fully reproducible from Raw.
- **Performance (NFR-1 support):** partitioning by tail/date bounds query scan; small
  files are compacted.
- **Security (NFR-3):** buckets encrypted (AES-256); access via RBAC-scoped credentials.

## 7. Requirements traceability

| Requirement | How addressed |
|-------------|---------------|
| FR-4 | Raw + Curated writers. |
| FR-5 | Catalog upserts flight/parameter/datapoint_index. |
| NFR-4 | Lifecycle tiering + retention. |
| NFR-7 / AC-5 | `raw_ref` lineage on every curated record. |
| NFR-1 (support) | Partitioning + compaction to bound query cost. |
| NFR-3 | Encryption at rest + RBAC-scoped access. |
