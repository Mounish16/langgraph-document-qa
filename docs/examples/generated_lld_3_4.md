# LLD 3.4 (generated)

*Generate LLD3.4 based on LLD3.1,LLD3.2and LLD3.3*

# DOC 3.4 — Low Level Design: Alerting & Monitoring Service

## 1. Scope

Detailed design of the alerting and monitoring service of the ADMP: the Alerting &
Monitoring Service that evaluates configured parameter thresholds against ingested data
and raises alerts on exceedance. Realises FR-8, IF-5 and acceptance criterion AC-3.
Conforms to the HLD "Alerting & Monitoring" component.

## 2. Module structure

- `alerting/evaluator.py` — evaluates threshold breaches against historical data (FR-8).
- `alerting/notifier.py` — sends alerts via email, webhook or message queue (IF-5).
- `alerting/repository.py` — transactional alert writes to the catalog.
- `catalog/models.py` — `Alert`, `ThresholdDefinition`, `ParameterExceedance`.
- `catalog/lineage.py` — links each alert to its raw source object.

## 3. Interfaces

- `evaluate_alerts(alert_config: dict, records: list[ADMRecord]) -> AlertList`.
- `send_notification(notification: Notification) -> None`.
- `upsert_alert(alert: Alert) -> None`.

## 4. Data model

Catalog (relational):

- `alert(alert_id PK, flight_id FK, parameter_id FK, threshold_definition_id FK, ts_range, raw_ref)`
- `threshold_definition(threshold_id PK, name, unit, source, min, max)`
- `parameter_exceedance(parameter_id FK, alert_id FK, ts_range, value, source_object (lineage))`

## 5. Sequence

1. Evaluator receives a batch of records from the broker and evaluates each against
   configured thresholds.
2. On breach, Notifier sends an alert via email/webhook/message queue to the relevant
   recipient(s).
3. Repository upserts the alert into the catalog with lineage back to its raw source.

```
[broker] -> evaluator -> notifier (email/webhook/queue) -> [recipient]
                         |
                         +-> repository -> catalog (alert, threshold_definition, parameter_exceedance)
```

## 6. Non-functional design notes

- **Performance (NFR-1 support):** uses a sliding window of historical data to bound
  evaluation cost.
- **Security (NFR-3):** alerts are sent via secure channels; recipient credentials are
  managed by the corporate identity provider.
- **Observability (NFR-5):** each alert carries a correlation id from ingestion onward.

## 7. Requirements traceability

| Requirement | How addressed |
|-------------|---------------|
| FR-8 | Evaluator evaluates threshold breaches against historical data. |
| IF-5 | Notifier sends alerts via email/webhook/message queue. |
| AC-3 | Threshold breach raises an alert within 60 seconds of ingestion. |

## Requirements coverage

| Requirement | How addressed |
|-------------|---------------|
| FR-8 | Evaluator evaluates threshold breaches against historical data. |
| IF-5 | Notifier sends alerts via email/webhook/message queue. |
| AC-3 | Threshold breach raises an alert within 60 seconds of ingestion. |

## Assumptions

* The Alerting & Monitoring Service is deployed symmetrically across two sites.
* The catalog store uses point-in-time backups with daily fulls and continuous transaction-log backup, retained 35 days.
* The evaluator uses a sliding window of historical data to bound evaluation cost.
* The notifier sends alerts via secure channels; recipient credentials are managed by the corporate identity provider.
