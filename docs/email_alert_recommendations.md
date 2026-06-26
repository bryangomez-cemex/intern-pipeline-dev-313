# Email Alert Recommendations

This is the recommended alert catalog. Do not enable all alerts at once; pick the ones HR and operations actually want to receive.

## Priority 1: Production-Critical

### Pipeline Failed

- Trigger: Azure Function throws an exception while processing a blob.
- Recipients: system owner, HR operations owner.
- Source: Azure Function logs plus `fact_pipeline_runs.status = 'Failed'`.
- Suggested frequency: immediate.
- Email subject: `[Intern System] Pipeline failed: {file_name}`
- Include: blob name, run id, error message, failed timestamp, suggested next action.

### File Moved To Failed

- Trigger: file is archived under `failed/` or run status is failed.
- Recipients: system owner, intake owner.
- Source: Blob path and `fact_pipeline_runs`.
- Suggested frequency: immediate.
- Include: file name, original sender when available, reason, retry instructions.

### Bad Rows Detected

- Trigger: `bad_rows > 0` in `fact_pipeline_runs`.
- Recipients: HR data owner, system owner.
- Source: `fact_pipeline_runs`.
- Suggested threshold: immediate if `bad_rows >= 1`, or daily summary if HR prefers fewer emails.
- Include: run id, good rows, bad rows, total rows, error report link/path.

### Missing Requisition ID

- Trigger: incoming onboarding/requisition-related file cannot match or extract `requisition_id`.
- Recipients: HR intake owner.
- Source: validation exceptions or pipeline missing items.
- Suggested frequency: immediate.
- Include: file name, sender email when available, candidate/intern name when available, next action.

## Priority 2: HR Operational

### Contract Expired But Still Active

- Trigger: `vw_powerbi_expired_active_contracts` has rows.
- Recipients: HR operations, optionally VP owner.
- Suggested frequency: daily morning summary.
- Include: intern name, employee number, VP, manager, contract end date, days overdue.

### Baja De Practicante

- Trigger: a current intern sync changes an intern from active/`ST002`/`Activo` to inactive/`Inactivo`/`Baja`.
- Recipients: HR operations.
- Suggested frequency: immediate.
- Source: `fact_intern_lifecycle_events.event_type = 'baja_requested'` and `fact_communications.communication_type = 'Baja De Practicante'`.
- Email subject: `Baja De Practicante - {Nombre completo}`
- Include: personal data, university/career/semester, CEMEX ID, institutional email, VP, project, manager, AIRH, UDN, company, OI, CC, salary, start date, end date, final status.
- Current implementation: creates a prepared HR communication automatically when the transition is detected; real delivery depends on the configured email sender job/settings.

### Contract Ending In 30 Days

- Trigger: active intern has `days_until_contract_end BETWEEN 0 AND 30`.
- Recipients: HR operations.
- Suggested frequency: weekly or daily summary.
- Include: intern name, VP, manager, end date, next action.

### VP Over Capacity

- Trigger: `vw_powerbi_vp_capacity.capacity_status = 'Over capacity'`.
- Recipients: HR leadership, capacity owner.
- Suggested frequency: daily or weekly summary.
- Include: VP, allowed, current, overage.

### Near Capacity

- Trigger: `capacity_status = 'Near full'`.
- Recipients: HR leadership.
- Suggested frequency: weekly summary.
- Include: VP, remaining slots, current count, allowed count.

### New Vacante Opened

- Trigger: new row in `vw_powerbi_vacantes`.
- Recipients: HR requisition owner.
- Suggested frequency: immediate or daily summary.
- Include: requisition id, position, VP, manager, days open.

### Vacante Older Than N Days

- Trigger: `vw_powerbi_vacantes.days_open >= 7` or another HR threshold.
- Recipients: HR requisition owner, manager owner.
- Suggested frequency: daily summary.
- Include: requisition id, days open, VP, manager, next action.

## Priority 3: Document And Data Quality

### Missing Paquete 1 Documents

- Trigger: open missing document item for Paquete 1.
- Recipients: HR onboarding owner.
- Suggested frequency: daily summary.
- Include: intern/candidate, missing document, VP, manager, file/source.
- Current Paquete 1 required documents: `ALTA`, `CURP`, `CONSTANCIA_ESTUDIOS`, `IDENTIFICACION`, `COMPROBANTE_DOMICILIO`.

### Document Needs Review

- Trigger: `vw_powerbi_document_status.validation_status IN ('Needs Review', 'Validation Failed')`.
- Recipients: HR onboarding owner.
- Suggested frequency: immediate for failed validation, daily for needs review.
- Include: document type, candidate/intern, validation status, notes.

### Scanned Document OCR Failed

- Trigger: PDF/image has no text extraction result after Document Intelligence fallback.
- Recipients: HR onboarding owner, system owner if frequent.
- Suggested frequency: immediate.
- Include: file name, detected document type, candidate/intern match if available.

### Business Validation Exceptions

- Trigger: `vw_business_validation_exceptions` has new rows.
- Recipients: HR data owner.
- Suggested frequency: daily summary.
- Include: field, severity, count, top affected interns.

### Org Matching Conflict

- Trigger: relationship logic cannot choose a unique CIA/VP/CC/OI candidate.
- Recipients: HR data owner.
- Suggested frequency: daily summary or immediate if blocking.
- Include: intern/candidate, JefeInmediato, OI, CC, competing values.

## Priority 4: Platform Health

### No Files Processed Recently

- Trigger: no successful `fact_pipeline_runs` in the last N hours/days.
- Recipients: system owner.
- Suggested threshold: no runs in 24 hours during business days.
- Include: last successful run timestamp and last failed run timestamp.

### Function App Not Running

- Trigger: Azure Function App state is not running or health check fails.
- Recipients: system owner.
- Suggested frequency: immediate.
- Source: Azure Monitor.

### Storage Authentication Failure

- Trigger: blob access failure from Function or intake script.
- Recipients: system owner.
- Suggested frequency: immediate.

### SQL Authentication Or Connectivity Failure

- Trigger: SQL connection failure from Function or local scheduled job.
- Recipients: system owner.
- Suggested frequency: immediate.

### Power BI Refresh Failed

- Trigger: Power BI dataset refresh failure.
- Recipients: report owner, system owner.
- Suggested frequency: immediate.
- Source: Power BI Service refresh notifications.

## Recommended First Alerts To Enable

Start with these:

1. Pipeline Failed.
2. File Moved To Failed.
3. Bad Rows Detected.
4. Missing Requisition ID.
5. Contract Expired But Still Active.
6. Contract Ending In 30 Days.
7. Power BI Refresh Failed.

Add document alerts after the first real onboarding packet test.
