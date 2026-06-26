# Power BI Web Setup Sin DAX

Use these SQL views as the dataset. They are built so Power BI Service can use simple fields, implicit counts, and sums.

Run:

```text
scripts/sql/create_business_powerbi_views.sql
scripts/sql/2026-06_schema_simplification.sql
scripts/sql/2026-06_powerbi_no_dax_views.sql
```

## Global Slicers

Use these on most pages:

- `vp`
- `cia_hc`
- `ubicacion_hc`
- `estado_ubicacion_hc`
- `manager`
- `raw_status` or `risk_bucket`, depending on the page

Recommended setting: slicers as dropdowns, single-select off, search on.

vw_powerbi_dashboard_kpis
vw_powerbi_interns_status
vw_powerbi_vp_summary
vw_powerbi_location_summary
vw_powerbi_vacantes
vw_powerbi_costos_practicantes
vw_powerbi_contract_risk
vw_powerbi_inactive_interns
vw_powerbi_document_status
vw_powerbi_document_summary
vw_business_validation_exceptions
vw_powerbi_hr_action_queue









## Page 1: Resumen Ejecutivo RH

Purpose: one-screen health view for HR leadership.

Slicers:

- Source: `vw_powerbi_interns_status`
- Fields: `vp`, `cia_hc`, `ubicacion_hc`, `estado_ubicacion_hc`, `manager`, `raw_status`

Visuals:

- Card `HC Activos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `hc_activos`
  - Summarization: Sum
- Card `HC Inactivos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `hc_inactivos`
  - Summarization: Sum
- Card `Terminan 0-30 Dias`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `terminacion_30_dias`
  - Summarization: Sum
- Card `Vencidos Activos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `contratos_vencidos_activos`
  - Summarization: Sum
- Card `Vacantes Abiertas`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `vacantes_abiertas`
  - Summarization: Sum





- Bar chart `Practicantes por VP`
  - Source: `vw_powerbi_vp_summary`
  - Y-axis: `vp`
  - X-axis/Values: `hc_activos`
  - Sort: `hc_activos`, descending
  
- Bar chart `Practicantes por Ubicacion`
  - Source: `vw_powerbi_location_summary`
  - Y-axis: `ubicacion_hc`
  - X-axis/Values: `hc_activos`
  - Sort: `hc_activos`, descending


- Donut or stacked bar `Status`
  - Source: `vw_powerbi_interns_status`
  - Legend/Y-axis: `raw_status`
  - Values: `intern_id`
  - Summarization: Count distinct


- Table `Detalle General`
  - Source: `vw_powerbi_interns_status`
  - Columns: `intern_name`, `employee_number`, `cemex_employee_number`, `position_name`, `manager`, `vp`, `ubicacion_hc`, `contract_end_date`, `raw_status`
















## Page 2: Vacantes Y Capacidad

Purpose: show open requisitions and how much room each VP still has.

Slicers:

- Source: `vw_powerbi_vacantes`: `vp`, `cia_hc`, `manager`, `requisition_status`
- Source: `vw_powerbi_vp_summary`: `capacity_status`

Visuals:

- Card `Vacantes Abiertas`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `vacantes_abiertas`
  - Summarization: Sum
- Card `Espacios Disponibles`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `espacios_disponibles_vp`
  - Summarization: Sum
- Stacked bar `Capacidad por VP`
  - Source: `vw_powerbi_vp_summary`
  - Y-axis: `vp`
  - X-axis/Values: `current_practicantes`, `remaining_practicantes`
  - Sort: `remaining_practicantes`, ascending





- Table `Capacidad Detalle`
  - Source: `vw_powerbi_vp_summary`
  - Columns: `vp`, `allowed_practicantes`, `current_practicantes`, `remaining_practicantes`, `utilization_pct`, `capacity_status`

  - Conditional formatting on `capacity_status`: red for `Over capacity`, yellow for `Near full`, green for `Available`





- Bar chart `Vacantes por VP`
  - Source: `vw_powerbi_vacantes`
  - Y-axis: `vp`
  - X-axis/Values: `requisition_id`
  - Summarization: Count distinct



- Table `Vacantes Detalle`
  - Source: `vw_powerbi_vacantes`
  - Columns: `requisition_id`, `position_name`, `vp`, `manager`, `oi_hc`, `cc_hc`, `cia_hc`, `created_at`, `days_open`, `next_action`
  - Sort: `days_open`, descending




















## Page 3: Costos Y Distribucion

Purpose: cost control by VP, company, state, and location.

Slicers:

- Source: `vw_powerbi_costos_practicantes`
- Fields: `vp`, `cia_hc`, `ubicacion_hc`, `estado_ubicacion_hc`

Visuals:

- Card `Importe Total Activos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `importe_total_activos`
  - Summarization: Sum
  - Format: Currency
- Card `Importe Promedio`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `importe_promedio_activos`
  - Summarization: Average
  - Format: Currency


- Column chart `Costo por VP`
  - Source: `vw_powerbi_costos_practicantes`
  - X-axis: `vp`
  - Y-axis/Values: `importe_total_sum`
  - Sort: `importe_total_sum`, descending
  - Format: Currency


- Matrix `Costo Detalle`
  - Source: `vw_powerbi_costos_practicantes`
  - Rows: `vp`, `ubicacion_hc`, `estado_ubicacion_hc`, `cia_hc`
  - Values: `practicante_count`, `importe_total_sum`, `importe_total_avg`


- Treemap `Costo Relativo`
  - Source: `vw_powerbi_costos_practicantes`
  - Category/Group: `vp`
  - Values: `importe_total_sum`


- Bar chart `HC por Estado`
  - Source: `vw_powerbi_location_summary`
  - Y-axis: `estado_ubicacion_hc`
  - X-axis/Values: `hc_activos`
  - Sort: `hc_activos`, descending















## Page 4: Vencimientos, Inactivos Y Riesgo

Purpose: avoid active interns with expired contracts and plan renewals/bajas.

Slicers:

- Source: `vw_powerbi_contract_risk`
- Fields: `vp`, `cia_hc`, `ubicacion_hc`, `manager`, `risk_bucket`, `raw_status`

Visuals:

- Card `Terminan 0-30 Dias`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `terminacion_30_dias`
  - Summarization: Sum
- Card `Vencidos Activos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `contratos_vencidos_activos`
  - Summarization: Sum
- Card `Inactivos`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `hc_inactivos`
  - Summarization: Sum



- Bar chart `Riesgo de Contrato`
  - Source: `vw_powerbi_contract_risk`
  - Y-axis: `risk_bucket`
  - X-axis/Values: `intern_id`
  - Summarization: Count distinct
  - Sort: `risk_bucket`, ascending

- Bar chart `Riesgo por VP`
  - Source: `vw_powerbi_contract_risk`
  - Y-axis: `vp`
  - X-axis/Values: `intern_id`
  - Legend: `risk_bucket`
  - Summarization: Count distinct



- Table `Accion Requerida`
  - Source: `vw_powerbi_contract_risk`
  - Columns: `intern_name`, `employee_number`, `vp`, `manager`, `contract_end_date`, `days_until_contract_end`, `risk_bucket`, `next_action`
  - Visual filter: `risk_bucket` is not `06 Sin riesgo cercano`
  - Sort: `days_until_contract_end`, ascending

- Table `Inactivos`
  - Source: `vw_powerbi_inactive_interns`
  - Columns: `intern_name`, `employee_number`, `vp`, `manager`, `contract_end_date`, `raw_status`, `latest_status_event_date`















## Page 5: Documentos, Excepciones Y Acciones RH

Purpose: operational work queue for missing docs, validation issues, and HR follow-up.

Slicers:

- Source: `vw_powerbi_document_status`: `vp`, `cia_hc`, `ubicacion_hc`, `manager`, `document_status_label`, `document_name`
- Source: `vw_business_validation_exceptions`: `severity`, `issue_field`, `issue_status`
- Source: `vw_powerbi_hr_action_queue`: `action_category`, `severity`, `next_action`

Visuals:

- Card `Practicantes con Docs Faltantes`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `practicantes_con_docs_faltantes`
  - Summarization: Sum
- Card `Excepciones Abiertas`
  - Source: `vw_powerbi_dashboard_kpis`
  - Field: `excepciones_abiertas`
  - Summarization: Sum



- Bar chart `Docs Faltantes por Documento`
  - Source: `vw_powerbi_document_summary`
  - Y-axis: `document_name`
  - X-axis/Values: `missing_rows`
  - Visual filter: `missing_rows` is greater than 0
  - Sort: `missing_rows`, descending

- Bar chart `Excepciones por Campo`
  - Source: `vw_business_validation_exceptions`
  - Y-axis: `issue_field`
  - X-axis/Values: `issue_field`
  - Summarization: Count
  - Sort: Count, descending





- Table `Documentos Detalle`
  - Source: `vw_powerbi_document_status`
  - Columns: `intern_name`, `employee_number`, `vp`, `manager`, `document_name`, `document_status_label`, `validation_status`, `severity`, `next_action`, `created_at`
  - Visual filter: `document_status_label` is not `Recibido`

  
- Table `Excepciones Detalle`
  - Source: `vw_business_validation_exceptions`
  - Columns: `intern_name`, `employee_number`, `vp`, `manager`, `issue_field`, `severity`, `issue_status`, `issue_description`, `suggested_fix`, `next_action`


- Table `Cola RH`
  - Source: `vw_powerbi_hr_action_queue`
  - Columns: `action_category`, `intern_name`, `vp`, `manager`, `severity`, `action_description`, `next_action`, `action_created_at`
  - Sort: `action_created_at`, descending










## Visual Cleanup

- Use horizontal bar charts for VP, manager, location, and document names because labels are long.
- Avoid donut charts unless there are at least two meaningful categories.
- Use table visuals for work queues, not matrices.
- Keep all KPI cards on top of the page.
- Use the same slicer order on every page: VP, CIA, Location, State, Manager, Status/Risk.
- Rename fields in the visual headers to Spanish labels, for example `hc_activos` to `HC Activos`.
