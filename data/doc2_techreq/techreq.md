# DOC 2 — Technical Requirements: Aircraft Data Management Platform (ADMP)

## Document Information

| Field | Value |
|-------|-------|
| Document Name | ADMP — Technical Requirements |
| Service | ADMP |
| Version | 1.0 |
| Issue Date | 2026-07-07 |
| Parent design | DOC 1 — HLD (HLD-ADMP-001) |
| Classification | Illustrative sample |

## 1. Purpose and scope

This document specifies the technical requirements for the Aircraft Data Management
Platform. Requirements are traceable to the HLD components and are the acceptance basis
for the Low Level Designs (DOC 3.x). Keywords SHALL / SHOULD / MAY follow RFC 2119.

Sources in scope: ACARS messages (ARINC 620), Quick Access Recorder files (ARINC 767),
and ADS-B position streams. Canonical form: the **Aircraft Data Model (ADM)**.

---

## 2. Functional Requirements

### Ingestion & validation

- **FR-1** — The Ingestion Gateway SHALL accept aircraft data from three source
  interfaces: ACARS (ARINC 620), QAR file upload (ARINC 767), and an ADS-B stream.
  *(HLD: Ingestion Gateway. Realised in LLD 3.1.)*
- **FR-2** — The system SHALL validate every incoming record against the source schema
  and the target ADM schema, and SHALL reject records that fail validation without
  persisting them to the Curated Zone. *(LLD 3.1.)*
- **FR-3** — The system SHALL normalise each valid record into the canonical ADM,
  including unit normalisation and parameter-name mapping. *(LLD 3.1.)*
- **FR-4** — The system SHALL persist all as-received data to the Raw Zone and all
  normalised data to the Curated Zone of the data lake. *(HLD: Data Lake. LLD 3.2.)*
- **FR-5** — The system SHALL maintain a metadata catalog keyed by aircraft tail number,
  flight identifier, parameter definition and ingestion lineage. *(LLD 3.2.)*

### Serving & analytics

- **FR-6** — The Query & Analytics API SHALL allow retrieval of curated data filtered by
  tail number, flight identifier, parameter and time window. *(HLD: Query API. LLD 3.3.)*
- **FR-7** — The platform SHALL provide fleet-monitoring dashboards built over the Query
  API. *(HLD: Dashboards.)*
- **FR-8** — The Alerting & Monitoring Service SHALL evaluate configured parameter
  thresholds against ingested data and raise alerts on exceedance. *(HLD: Alerting.
  Realised in planned LLD 3.4.)*
- **FR-9** — The Query & Analytics API SHALL support asynchronous export of large result
  sets to object storage. *(LLD 3.3.)*

---

## 3. Non-Functional Requirements

- **NFR-1 (Performance)** — The platform SHALL sustain ingestion of at least 50,000
  records/second at peak, and the Query API SHALL return p95 responses in < 500 ms at
  500 requests/second for bounded queries. *(Affects LLD 3.1, 3.2, 3.3.)*
- **NFR-2 (Availability)** — The platform SHALL provide 99.9% monthly availability for
  ingestion and serving, deployed symmetrically across two sites. *(HLD §11.)*
- **NFR-3 (Security)** — All service-to-service and client traffic SHALL be authenticated
  and encrypted in transit (mTLS or OIDC-signed tokens); all data at rest SHALL be
  encrypted (AES-256). Access SHALL be role-based (RBAC) and every access SHALL be
  audit-logged. The design SHALL align with DO-326A / ED-202A airworthiness security
  process. *(All LLDs.)*
- **NFR-4 (Retention)** — Raw data SHALL be retained for 7 years, with hot access for the
  first 90 days and cold-tier thereafter; curated data SHALL be retained for 7 years.
  *(LLD 3.2.)*
- **NFR-5 (Observability)** — Every request and pipeline stage SHALL emit a correlation
  (trace) id, structured logs, and metrics. No PII or sensitive payloads SHALL appear in
  logs. *(All LLDs.)*
- **NFR-6 (Scalability)** — All services SHALL be stateless and horizontally scalable and
  SHALL be container-deployable. *(All LLDs.)*
- **NFR-7 (Data governance & lineage)** — The catalog SHALL record the lineage of each
  curated record back to its raw source object. *(LLD 3.2.)*

---

## 4. Interfaces

- **IF-1** — ACARS ingestion endpoint (ARINC 620 message format).
- **IF-2** — QAR file upload endpoint (ARINC 767 container; de-encryption required).
- **IF-3** — ADS-B streaming consumer.
- **IF-4** — Query & Analytics REST API (JSON over HTTPS).
- **IF-5** — Alert notification sink (webhook, email and message-queue targets).
- **IF-6** — OIDC identity provider integration for authentication.

---

## 5. Data model (canonical ADM, summary)

| Entity | Key fields |
|--------|-----------|
| Aircraft | tail_number (PK), type, operator |
| Flight | flight_id (PK), tail_number (FK), departure, arrival, start/end time |
| ParameterDefinition | parameter_id (PK), name, unit, source, valid range |
| DataPoint | flight_id (FK), parameter_id (FK), timestamp, value, source_object (lineage) |

---

## 6. Acceptance Criteria

- **AC-1** — A malformed or schema-invalid record is rejected, logged with a reason, and
  is NOT present in the Curated Zone. *(Verifies FR-2; LLD 3.1.)*
- **AC-2** — An API request without a valid token receives HTTP 401 and no data. *(Verifies
  NFR-3, IF-4; LLD 3.3.)*
- **AC-3** — A parameter value exceeding its configured threshold raises an alert within
  60 seconds of ingestion. *(Verifies FR-8; LLD 3.4.)*
- **AC-4** — A query for a given tail number and time window returns exactly the matching
  curated records, ordered by timestamp. *(Verifies FR-6; LLD 3.3.)*
- **AC-5** — Every curated record can be traced in the catalog to the raw source object it
  came from. *(Verifies NFR-7; LLD 3.2.)*

---

## 7. Requirements-to-LLD traceability (summary)

| LLD | Requirements covered |
|-----|----------------------|
| 3.1 Ingestion & Validation | FR-1, FR-2, FR-3, IF-1, IF-2, IF-3, AC-1, NFR-1, NFR-3, NFR-5, NFR-6 |
| 3.2 Data Lake Storage | FR-4, FR-5, NFR-4, NFR-7, AC-5, data model |
| 3.3 Query & Analytics API | FR-6, FR-9, IF-4, AC-2, AC-4, NFR-1, NFR-3 |
| 3.4 Alerting & Monitoring (planned) | FR-8, IF-5, AC-3, NFR-5 |
