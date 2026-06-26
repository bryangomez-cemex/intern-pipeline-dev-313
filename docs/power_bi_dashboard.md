# Power BI Dashboard

Power BI users are HR managers and VPs. Load the business views below; avoid technical file/run/blob views unless auditing a pipeline issue.

Run these SQL scripts first:

```text
scripts/sql/create_business_powerbi_views.sql
scripts/sql/2026-06_schema_simplification.sql
scripts/sql/2026-06_powerbi_no_dax_views.sql
```

If building directly in Power BI Service without DAX/Desktop, use the 5-page setup in `docs/power_bi_no_dax_5_pages.md`.

## Business Views

- `vw_canonical_interns_current`
- `vw_canonical_intern_documents`
- `vw_canonical_document_types`
- `vw_canonical_org_assignments`
- `vw_canonical_requisitions`
- `vw_canonical_pipeline_runs`
- `vw_business_validation_exceptions`
- `vw_requisitions_status`
- `vw_communications_status`
- `vw_hr_actions_today`
- `vw_powerbi_vacantes`
- `vw_powerbi_interns_status`
- `vw_powerbi_costos_practicantes`
- `vw_powerbi_expired_active_contracts`
- `vw_powerbi_inactive_interns`
- `vw_powerbi_vp_capacity`

Legacy `vw_full_mvp_*` views still exist for compatibility and audit detail, but new Power BI reports should use the `vw_powerbi_*` and `vw_canonical_*` views above.

## Requested Pages

### Vacantes

Use `vw_powerbi_vacantes`.

Recommended visuals:

- KPI card: `COUNT(requisition_id)` labeled `Vacantes abiertas`.
- Table: `position_name`, `vp`, `manager`, `oi_hc`, `cc_hc`, `cia_hc`, `created_at`, `days_open`, `next_action`.
- Bar chart: `Vacantes abiertas por VP`.
- Optional bar chart: `Vacantes por manager`.

Behavior: a requisition disappears from this view when an intern exists with the same `requisition_id`.

### Costos

Use `vw_powerbi_costos_practicantes`.

Recommended visuals:

- Clustered column chart: Axis `vp`, Value `importe_total_sum`, label `Costo total`.
- Matrix: Rows `vp`, `ubicacion_hc`, `estado_ubicacion_hc`, `cia_hc`; Values `practicante_count`, `importe_total_sum`, `importe_total_avg`.
- Treemap: Group `vp`, Values `importe_total_sum`.
- Slicers: `vp`, `ubicacion_hc`, `estado_ubicacion_hc`, `cia_hc`.

Labels:

- `importe_total_sum`: `Importe total`
- `importe_total_avg`: `Importe promedio`
- `practicante_count`: `Practicantes`

### Inactivos

Use two tables:

- `vw_powerbi_expired_active_contracts`: practicantes activos con contrato vencido.
- `vw_powerbi_inactive_interns`: todos los practicantes con status inactivo/baja.

Recommended visuals:

- KPI card: count of `vw_powerbi_expired_active_contracts[intern_id]`, label `Activos vencidos`.
- KPI card: count of `vw_powerbi_inactive_interns[intern_id]`, label `Inactivos`.
- Table for expired active: `intern_name`, `employee_number`, `vp`, `manager`, `contract_end_date`, `days_until_contract_end`, `raw_status`.
- Table for inactive: `intern_name`, `employee_number`, `vp`, `manager`, `contract_end_date`, `raw_status`, `latest_status_event_date`.

### Max Per VP

Use `vw_powerbi_vp_capacity`.

Recommended visuals:

- Stacked bar chart:
  - Axis: `vp`
  - Values: `current_practicantes`, `remaining_practicantes`
  - Label: `Capacidad por VP`
- Gauge:
  - Value: `current_practicantes`
  - Target: `allowed_practicantes`
  - Filter by selected VP.
- Table/matrix:
  - `vp`, `allowed_practicantes`, `current_practicantes`, `remaining_practicantes`, `utilization_pct`, `capacity_status`
- Conditional formatting:
  - `Over capacity`: red
  - `Near full`: yellow
  - `Available`: green

Suggested labels:

- `allowed_practicantes`: `Máximo permitido`
- `current_practicantes`: `Actual`
- `remaining_practicantes`: `Disponibles`
- `utilization_pct`: `% usado`
- `capacity_status`: `Estado capacidad`

## Recommended Visuals

- Active/current interns by VP, area, manager, university, career, OI, and CC.
- Missing documents by VP, area, manager, intern, and document code using `vw_canonical_intern_documents`.
- Upcoming expirations using `is_expiring_soon` and `days_until_contract_end`.
- Lifecycle events by process type: altas, extendimientos, bajas, current sync, document refresh.
- Business exceptions by VP, area, manager, OI, CC, company, field, severity, and next action.
- Pending requisitions by VP, area, manager, status, OI, and CC.
- Communications/actions needed by recipient group and communication status.
- HR action queue from `vw_hr_actions_today`.

## Business Questions

- How many active interns do we have?
- Who is missing documents?
- Who is expiring soon?
- Which requisitions are pending?
- Which interns have OI/CC/manager/company/date/salary issues?
- Which VP or area has the most blocked cases?
- What actions does HR need to take today?

## Verification Queries

```sql
SELECT TOP 25 * FROM dbo.vw_canonical_interns_current ORDER BY intern_name;
SELECT TOP 25 * FROM dbo.vw_canonical_intern_documents ORDER BY intern_name, document_code;
SELECT TOP 25 * FROM dbo.vw_canonical_document_types ORDER BY document_code;
SELECT TOP 25 * FROM dbo.vw_canonical_org_assignments ORDER BY current_intern_rows DESC;
SELECT TOP 25 * FROM dbo.vw_canonical_requisitions ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_canonical_pipeline_runs ORDER BY started_at DESC;
SELECT TOP 25 * FROM dbo.vw_business_validation_exceptions ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_requisitions_status ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_communications_status ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_hr_actions_today ORDER BY action_created_at DESC;
SELECT TOP 25 * FROM dbo.vw_powerbi_vacantes ORDER BY days_open DESC;
SELECT TOP 25 * FROM dbo.vw_powerbi_costos_practicantes ORDER BY importe_total_sum DESC;
SELECT TOP 25 * FROM dbo.vw_powerbi_expired_active_contracts ORDER BY contract_end_date;
SELECT TOP 25 * FROM dbo.vw_powerbi_inactive_interns ORDER BY latest_status_event_date DESC;
SELECT TOP 25 * FROM dbo.vw_powerbi_vp_capacity ORDER BY remaining_practicantes ASC;
SELECT * FROM dbo.vw_schema_consolidation_recommendations ORDER BY drop_readiness, object_name;
```
