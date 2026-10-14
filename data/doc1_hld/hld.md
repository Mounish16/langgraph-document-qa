# DOC 1 — High Level Design (HLD): Aircraft Data Management Platform (ADMP)

## Document Information

| Field | Value |
|-------|-------|
| Document Name | Aircraft Data Management Platform — High Level Design |
| Service | ADMP (Aircraft Data Management Platform) |
| Author | Design Office |
| Contributors | Data Engineering, Flight Operations, Security Architecture |
| Issue Date | 2026-07-07 |
| Version | 1.0 |
| Classification | Illustrative sample |

## Document History

| Version | Date | Summary of change | Reference ID |
|---------|------|-------------------|--------------|
| 1.0 | 2026-07-07 | Initial draft | HLD-ADMP-001 |

---

## 1. Design ownership

### 1.1 Ownership Matrix

| Role | Responsibility | Named individual |
|------|----------------|------------------|
| Design owner (Essential) | Owns this design document, versioning, syndication and handover to delivery, operations and governance. | TBD |
| Project manager | Delivery schedule and budget. | TBD |
| Service owner (Essential) | Monitors service introduction of the ADMP. | TBD |
| Service operations manager (Essential) | Monitors operational readiness and run-state. | TBD |
| Design mentor (Essential) | Design Advisory Group representative. | TBD |
| Business | Ensures fleet-operations requirements are matched to the solution. | TBD |
| Applications and data | Owns the Aircraft Data Model and data architecture. | TBD |
| Technology | Ensures platform technology aligns with architectural principles. | TBD |

---

## 2. Context

### 2.1 Summary

The **Aircraft Data Management Platform (ADMP)** is a new, centralised platform that
ingests, validates, stores, catalogs and serves aircraft-generated data across the
fleet. Today, aircraft data arrives through fragmented channels — ACARS messages via
the airline's ground network, Quick Access Recorder (QAR) files pulled during turn-
arounds, and ADS-B position streams — and is landed in disconnected stores owned by
different teams (engineering, flight operations, safety). There is no single, governed
source of truth, retrieval is slow and manual, and cross-fleet analytics are difficult.

The ADMP replaces this fragmented landscape with a single ingestion-to-serving pipeline.
It normalises every source into one canonical **Aircraft Data Model (ADM)**, persists
raw and curated data in a governed data lake, maintains a searchable catalog keyed by
tail number, flight and parameter, and exposes the data through a query API, dashboards
and an alerting service. The affected business areas are Engineering & Maintenance,
Flight Operations, and Safety/Compliance.

Expected outcomes: a governed single source of truth for aircraft data; sub-second
retrieval by tail/flight/parameter; near-real-time threshold alerting for exceedances;
and a foundation for fleet-wide predictive-maintenance analytics. This is being done to
reduce manual data handling, improve safety-event turnaround, and unlock analytics that
the current siloed stores cannot support. At a high level it is delivered as a set of
containerised, horizontally-scalable microservices on the private cloud.

### 2.2 Service categorisation

Business criticality: **High**. The platform underpins safety-relevant maintenance and
operations reporting. A prolonged outage delays exceedance investigations and fleet
analytics but does not directly ground aircraft (data is buffered at source and can be
re-ingested), so it is business-critical rather than flight-critical.

---

## 3. Links to documentation

- Business case: BC-ADMP-2026 (Design Office repository).
- Project initiation document: PID-ADMP-2026.
- Technical Requirements: DOC 2 — Technical Requirements (this design set).
- Low Level Designs: DOC 3.1 (Ingestion & Validation), 3.2 (Data Lake Storage), 3.3
  (Query & Analytics API), and planned 3.4 (Alerting & Monitoring).

---

## 4. Drivers and objectives

### 4.1 Drivers

- **Service improvement:** eliminate manual, per-team data pulls and reconciliation.
- **Safety & compliance:** faster, auditable access to flight data for exceedance and
  incident investigation.
- **Consolidation:** replace three siloed stores with one governed platform.
- **Security:** bring aircraft data handling in line with aviation cybersecurity
  expectations (DO-326A / ED-202A airworthiness security process).
- **Cost:** reduce duplicated storage and bespoke integration maintenance.

### 4.2 Requirements

The full functional and non-functional requirement set is maintained in **DOC 2 —
Technical Requirements**. In summary the platform must ingest multiple aircraft data
sources, validate and normalise them, store raw and curated data under defined retention,
serve them via a secured API and dashboards, and raise alerts on parameter exceedances.

### 4.3 Objectives

| ID | Objective statement | Success criteria |
|----|---------------------|------------------|
| OBJ-1 | Ingest ACARS, QAR and ADS-B sources into one canonical model. | All three sources land in the Curated Zone in ADM form during acceptance testing. |
| OBJ-2 | Provide governed retrieval of aircraft data. | Query API returns correct records for a tail + time window with p95 latency < 500 ms at target load. |
| OBJ-3 | Detect parameter exceedances promptly. | Threshold breach raises an alert within 60 seconds of ingestion. |
| OBJ-4 | Retain data to policy. | Raw data retrievable for 7 years; hot access for 90 days. |
| OBJ-5 | Secure all access. | 100% of API and ingestion endpoints authenticated; unauthorised requests rejected. |

### 4.4 Impact of no action

Without the ADMP, aircraft data remains siloed and manually handled. Exceedance
investigations continue to take days; cross-fleet predictive analytics remain infeasible;
storage and integration costs keep growing; and audit responses stay slow and error-prone.

---

## 5. Assumptions

| Assumption | Assessment / impact on this design |
|-----------|-------------------------------------|
| Fleet grows ~10% year on year. | Ingestion and storage are horizontally scalable; capacity plan sized for 5-year growth. |
| Data centre operates in a split (dual-site) model. | Services and storage deployed symmetrically across both sites; broker replicates cross-site. |
| Aircraft data volume per flight continues to increase. | Data lake uses columnar, partitioned storage to keep query cost bounded as volume grows. |
| Source systems (ACARS gateway, QAR tooling) remain available. | Ingestion Gateway buffers and supports replay so short source outages do not lose data. |

---

## 6. Constraints

1. Must integrate with the existing ACARS ground gateway (ARINC 620) and QAR download
   tooling (ARINC 767) without changing on-aircraft equipment.
2. Must use the approved private-cloud container platform and managed object storage.
3. Aircraft/flight data is treated as sensitive; handling must satisfy the corporate data-
   protection and aviation cybersecurity policies.
4. Delivery is phased; the alerting capability (LLD 3.4) follows the core ingest/store/
   serve capability.
5. Identity must federate with the corporate OIDC identity provider — no local user store.

---

## 7. Dependencies

- ACARS ground network / message gateway (upstream data source).
- QAR download and de-encryption tooling (upstream data source).
- ADS-B feed provider (upstream data source).
- Corporate OIDC identity provider (authentication).
- Private-cloud container platform, object storage and message broker (infrastructure).

### 7.1 Those dependent on this design

- Fleet analytics / predictive-maintenance initiatives.
- Safety & compliance reporting.
- Engineering dashboards.

---

## 8. Current state

### 8.1 Logical/architectural summary

Three independent pipelines exist. ACARS messages are written to an operations database
by the flight-ops team. QAR files are copied to an engineering file share and parsed with
desktop tooling. ADS-B data is consumed only transiently. There is no shared model, no
catalog, and no common access control; each store enforces its own (often ad hoc) rules.

### 8.2 Logical/architectural diagrams

```
[ACARS gateway] --> [Ops DB]            (flight operations)
[QAR files]     --> [Engineering share] (manual parsing)
[ADS-B feed]    --> (transient, not retained)
```

### 8.3 Technology summary

Relational ops database, Windows file share, desktop QAR parsers, spreadsheet-based
reporting. No streaming, no object storage, no unified catalog.

### 8.5 External interfaces

Current interfaces: ACARS ground gateway, QAR tooling, and manual exports to spreadsheets
consumed by engineering and safety. None are governed or access-controlled centrally.

---

## 9. Current limitations

| ID | Limitation name | Summary and impact |
|----|-----------------|--------------------|
| LIM-1 | Siloed stores | No single source of truth; data reconciled manually. |
| LIM-2 | No canonical model | Each source has its own format; cross-source analytics are impractical. |
| LIM-3 | Slow retrieval | Finding a flight's parameters can take hours of manual work. |
| LIM-4 | No governed access control | Inconsistent, per-store permissions; weak audit trail. |
| LIM-5 | No alerting | Parameter exceedances are found only during scheduled reviews. |
| LIM-6 | Limited retention | ADS-B not retained; QAR retention inconsistent. |

---

## 10. Target state logical

### 10.1 Brief options / alternatives

Three options were considered: (a) extend the existing ops database; (b) buy a packaged
flight-data-monitoring product; (c) build a governed data platform. Option (a) does not
solve siloing or streaming. Option (b) is costly and inflexible for bespoke analytics.
**Option (c), a purpose-built platform on the private cloud, was chosen** for governance,
scalability and analytics extensibility.

### 10.2 Changes to logical design

The target introduces a single ingestion-to-serving pipeline with these major logical
components:

- **Ingestion Gateway** — terminates the ACARS, QAR and ADS-B interfaces, buffers and
  hands records to processing. (Detailed in LLD 3.1.)
- **Stream Processing & Validation** — validates against schema, normalises to the ADM,
  enriches with reference data. (LLD 3.1.)
- **Message Broker** — durable, cross-site event backbone between stages.
- **Data Lake** — Raw Zone (as-received) and Curated Zone (ADM, columnar, partitioned).
  (Detailed in LLD 3.2.)
- **Metadata & Catalog Store** — relational catalog of tails, flights, parameters and
  data lineage. (LLD 3.2.)
- **Query & Analytics API** — secured retrieval and export of curated data. (LLD 3.3.)
- **Alerting & Monitoring Service** — evaluates parameter thresholds and raises alerts.
  (Planned LLD 3.4.)
- **Dashboards / UI** — fleet monitoring views over the API.
- **Identity & Access (RBAC)** — OIDC-federated authentication and role-based
  authorisation across all services.

```
                         +------------------ Identity & Access (OIDC, RBAC) ------------------+
                         |                                                                    |
[ACARS] [QAR] [ADS-B] -> [Ingestion Gateway] -> [Stream Processing/Validation] -> [Broker] ->  |
                                                                                    |          |
                                              +-------------------------------------+          |
                                              v                                                |
                                     [Data Lake: Raw + Curated]  <->  [Metadata & Catalog]     |
                                              |                                                |
                                              +--> [Query & Analytics API] --> [Dashboards]    |
                                              +--> [Alerting & Monitoring] --> [Notifications] -+
```

### 10.3 Known limitations

- 1-year view: alerting (LLD 3.4) delivered in a later phase; initial release covers
  ingest, store and serve.
- 5-year view: predictive-analytics workloads may require a dedicated compute tier
  separate from the serving API.

### 10.4 Residual risk and limitations

Dependency on upstream source availability remains; mitigated by buffering and replay.
Very large historical queries may need asynchronous export rather than synchronous API.

### 10.6 Physical solution summary

Containerised microservices on the private-cloud Kubernetes platform, deployed
symmetrically across two data-centre sites. Managed object storage backs the data lake;
a managed relational service backs the catalog; a partitioned, replicated message broker
provides the event backbone. All ingress terminates at an authenticated API gateway.

### 10.8 Interfaces

| Interface | Work required | Effort | Owner |
|-----------|---------------|--------|-------|
| ACARS (ARINC 620) ingest | New gateway adapter | M | Data Eng |
| QAR (ARINC 767) upload | New upload + de-encrypt adapter | M | Data Eng |
| ADS-B stream | New streaming consumer | S | Data Eng |
| Query REST API | New public-facing API | L | Platform |
| Alert notifications | New webhook/email/queue sink | S | Platform |
| OIDC identity provider | Federation configuration | S | Security |

---

## 11. Service continuity capability

### 11.1 Criticality

High. Impact of a day's outage: exceedance investigations and analytics delayed; source
data buffered and re-ingested on recovery, so no permanent data loss. Impact of total
loss: loss of the governed source of truth until restored from the secondary site/backups.

### 11.2 Backup requirements and solution

Raw Zone object storage is versioned and cross-site replicated. Catalog store uses
point-in-time backups with daily fulls and continuous transaction-log backup, retained 35
days. Curated Zone is reproducible from Raw via re-processing. Recovery: promote secondary
site; restore catalog to last consistent point; replay broker/raw as needed.

### 11.3 Anticipated failure states

| Failure mode | Required function | High-level process |
|--------------|-------------------|--------------------|
| Loss of single site (planned) | Continue ingest & serve | Traffic shifts to secondary; symmetric deployment absorbs load. |
| Loss of single site (unplanned) | Continue with minimal loss | Broker/raw replicated; secondary promoted; in-flight records replayed. |
| Partial/complete data loss | Restore data | Re-process Curated from Raw; restore catalog from backup. |
| Component update | No data loss | Rolling deploys; broker buffers during restarts. |

### 11.4 Single points of failure

The catalog store is the primary stateful dependency; mitigated by HA replica and cross-
site backups. Ingestion Gateway is stateless and horizontally redundant.

### 11.5 Symmetry

Primary and secondary sites are symmetric (active/active for stateless services;
active/standby for the catalog primary).

---

## 12. Update methodology, frequency, cost

Services updated via CI/CD rolling deployments (typically fortnightly). Data model and
schema changes are versioned and backward-compatible for one major version. Ownership:
Platform team for services; Data Eng for the ADM. Costs are operational (pipeline compute)
and storage-tiering (hot-to-cold lifecycle).

## 13. Benefits (high level)

Single governed source of truth; sub-second retrieval; near-real-time exceedance alerts;
7-year auditable retention; and an analytics-ready foundation for the fleet.

## 14. Residual risks

| Risk | Type | Summary |
|------|------|---------|
| Upstream source outage | Operational | Mitigated by buffering + replay. |
| Data volume growth | Capacity | Mitigated by partitioning + storage tiering. |
| Schema drift from sources | Data | Mitigated by schema validation + versioned ADM. |

## 15. High level costs of solution (excluding project costs)

- **15.1 Capital:** container platform capacity, object-storage baseline, broker cluster.
- **15.2 Capital-generated operating:** storage growth, support/maintenance, licensing.
- **15.3 Operating:** hosting, cross-site replication bandwidth, backup storage.

## 16. High level support structure

- **16.1 Service governance:** Service owner, Service operations manager, Business owner
  (Engineering).
- **16.2 Operational support:** Platform on-call for services; Data Eng for pipeline and
  model; Security for access and audit.

## 17. Decommissioning targets

| Element | Replaced by | Decommission activity | Timescale |
|---------|-------------|-----------------------|-----------|
| Engineering QAR file share | Data Lake + Catalog | Migrate & retire share | +6 months |
| Ad hoc spreadsheet exports | Query API / dashboards | Retire manual process | +3 months |

## 18. Block scheduling, lifecycle

Phase 1: ingest, store, serve (LLD 3.1–3.3). Phase 2: alerting (LLD 3.4). Phase 3:
analytics compute tier.

## 19. Potential future improvements

Predictive-maintenance models; self-service analytics workspace; streaming anomaly
detection; expansion to additional data sources (engine OEM feeds).

## 20. Design review log and schedule

Reviewed at Design Advisory Group gate before each phase; changes referenced against
HLD-ADMP-nnn and fed into CAB for release.
