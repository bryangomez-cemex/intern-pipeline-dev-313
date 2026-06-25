# Intern System Pipeline Technical Manual

Version: 2026-06-24  
Environment documented: Azure dev/staging resources used for the CEMEX intern automation pipeline  
Repository: `/Users/bryangomezcemex/intern-system-pipeline`

## 1. Purpose

This system automates HR intern intake, onboarding document handling, current intern database updates, requisition matching, data validation, and Power BI reporting.

The intended business flow is:

1. HR or an automated mailbox receives an email with files.
2. Attachments are uploaded to Azure Blob Storage under `raw-uploads`.
3. Azure Function detects the blob and runs the Python pipeline.
4. The pipeline classifies the file, extracts data, validates rows, enriches org fields, and updates Azure SQL.
5. Azure SQL views expose clean reporting tables for Power BI.
6. Power BI Service refreshes and shows HR dashboards.

Short architecture:

```text
Email / Gmail intake / future Outlook Graph
    -> Azure Blob Storage raw-uploads
    -> Azure Function blob trigger
    -> Python pipeline
    -> Azure SQL operational tables
    -> Azure SQL reporting views
    -> Power BI Service
```

## 2. Current Stack

### Cloud

- Azure Resource Group: `rg-intern-system-dev`
- Azure Function App: `mex-intern-pipeline-func-win`
- Azure SQL Server: `rg-intern-system-dev`
- Azure SQL Database: configured through app settings / `.env`
- Azure Blob Storage containers:
  - `raw-uploads`
  - `error-reports`
  - `archive`
  - processed/failed blob paths are used by the pipeline
- Azure AI Document Intelligence:
  - Function App settings confirmed:
    - `DOC_INTEL_ENDPOINT`
    - `DOC_INTEL_KEY`
  - Values exist in Azure Function app settings. Do not print or commit the values.

### Runtime

- Python
- Azure Functions Python model
- Azure SDK for Blob/Identity
- `pyodbc` for Azure SQL
- `pandas` / `openpyxl` for Excel
- `pypdf` for PDFs with text layers
- Azure AI Document Intelligence REST call for scanned PDFs/images
- Power BI Service for reports

### Local Development

- Workspace: `/Users/bryangomezcemex/intern-system-pipeline`
- Python virtual environment: `.venv`
- Local config: `.env` is ignored by git and must never be committed.
- Git branch at time of manual: `main`

## 3. Repository Layout

```text
azure_function_app/
  function_app.py
  host.json
  requirements.txt
  local.settings.example.json
  scripts/
    pipeline_service.py
    azure_clients.py
    app_config.py
    flexible_file_classifier.py
    lifecycle_requirements.py
    matching_engine.py
    document_pipeline.py
    onboarding_pipeline.py
    requisition_parser.py

scripts/
  pipeline_service.py
  azure_clients.py
  app_config.py
  flexible_file_classifier.py
  lifecycle_requirements.py
  matching_engine.py
  document_pipeline.py
  onboarding_pipeline.py
  requisition_parser.py
  intake_gmail_attachments.py
  sync_function_modules.py
  smoke_e2e_pipeline.py
  deployment_readiness_e2e.py
  check_function_readiness.py
  sql/
    create_full_mvp_pipeline.sql
    seed_pipeline_validation_rules.sql
    2026-06_package1_document_requirements.sql
    2026-06_resolve_stale_missing_items.sql
    add_corporate_column_aliases.sql
    create_matching_engine_v1.sql
    create_business_powerbi_views.sql
    2026-06_schema_simplification.sql
    2026-06_powerbi_no_dax_views.sql

docs/
  technical_manual.md
  email_alert_recommendations.md
  power_bi_dashboard.md
  power_bi_no_dax_5_pages.md
  schema_simplification.md
  lifecycle_requirements.md
  full_automation_deployment_guide.md
```

The files under `azure_function_app/scripts/` are synced copies used for deployment. The source-of-truth development files are under `scripts/`. Run `scripts/sync_function_modules.py` before deploying the Function App.

## 4. Azure Function

### Function Trigger

File: `azure_function_app/function_app.py`

The Function uses a Blob Trigger:

```text
path = raw-uploads/{name}
connection = AZURE_STORAGE_CONNECTION_STRING
source = EVENT_GRID
```

The handler:

1. Receives a blob event.
2. Strips the `raw-uploads/` container prefix from the blob name.
3. Ignores archive/processed/failed/error-report paths.
4. Calls:

```python
process_blob_by_name(
    source_container="raw-uploads",
    source_blob_name=blob_name,
    run_type="blob_trigger",
)
```

### Required Function App Settings

Never commit real values.

```text
AZURE_STORAGE_CONNECTION_STRING
RAW_UPLOADS_CONTAINER=raw-uploads
ERROR_REPORTS_CONTAINER=error-reports
ARCHIVE_CONTAINER=archive
AZURE_SQL_SERVER
AZURE_SQL_DATABASE
AZURE_SQL_AUTH_MODE=managed_identity
EMAIL_MODE=simulation
DEV_EMAIL_OVERRIDE
DOC_INTEL_ENDPOINT
DOC_INTEL_KEY
AzureWebJobsFeatureFlags=EnableWorkerIndexing
```

Optional/future email settings:

```text
GRAPH_TENANT_ID
GRAPH_CLIENT_ID
GRAPH_CLIENT_SECRET
GRAPH_SENDER_USER
EMAIL_MODE=graph_draft or graph_send
```

Keep `EMAIL_MODE=simulation` until real recipient approval is complete.

## 5. Blob Storage Contract

### Input Container

All source files enter through:

```text
raw-uploads
```

Recommended blob name patterns:

```text
current_interns/YYYY/MM/file.xlsx
requisitions/YYYY/MM/file.docx
candidate_docs/YYYY/MM/file.pdf
unknown/YYYY/MM/file.xlsx
```

The pipeline can classify files even when the folder is not perfect, but descriptive names improve auditability.

### Ignored Paths

The Function ignores blobs starting with:

```text
archive/
processed/
failed/
error-reports/
.
```

### Archive / Failed Behavior

When processing succeeds, the pipeline records run metadata and archives/moves the source according to the current pipeline behavior.

When processing fails, it records the failed run and stores error information in SQL and/or error-report paths.

## 6. Main Pipeline Behavior

File: `scripts/pipeline_service.py`

Primary entrypoints:

```python
process_blob_by_name(source_container, source_blob_name, run_type="manual")
process_next_blob(run_type="manual")
run_pipeline_for_uploaded_file(source_container, source_blob_name, run_type="blob_trigger")
```

High-level sequence:

1. Open SQL and Blob clients.
2. Check if blob was already processed.
3. Download blob to local temp/work area.
4. Classify file with `flexible_file_classifier.py`.
5. Extract tabular/document content.
6. Normalize columns through canonical aliases.
7. Validate rows.
8. Match to interns/requisitions.
9. Enrich org hierarchy fields.
10. Upsert interns/requisitions/doc facts.
11. Log lifecycle events, validations, missing items, and pipeline run summary.
12. Move/archive blob and update processed blob record.

## 7. File Classification

File: `scripts/flexible_file_classifier.py`

The classifier maps files to business process types. Important outputs:

- `file_profile_id`
- `technical_profile`
- `business_pipeline_type`
- `process_type`
- `needs_review`

Common process mappings:

```text
accepted_hires_excel      -> PROC_NEW_HIRE
requisition_excel/docx    -> PROC_REQUISITION
current_interns_excel/csv -> PROC_CURRENT_SYNC
generic_pdf/image         -> PROC_DOCUMENT_REFRESH or unknown
invalid executable        -> invalid_file / needs review
```

The classifier uses:

- File extension
- File name
- Sheet names
- Detected columns
- Known corporate aliases
- Content signals

## 8. Column Alias And Normalization

SQL config:

```text
dim_canonical_fields
dim_column_aliases
```

Script:

```text
scripts/sql/add_corporate_column_aliases.sql
```

Examples:

```text
NUMERO              -> employee_number
NOMBRE              -> full_name
VICEPRESIDENCIA     -> vp_hc
UBICACION           -> location
EDOUBICACION        -> location_state
CIA                 -> company_code
CIASTR              -> company
CC                  -> cc_hc
ORDENINTERNA        -> oi_hc
EMAIL               -> email
ImporteTotal        -> salary
RAZON SOCIAL HC     -> company
UBICACIÓN HC        -> location
ESTADO UBICACIÓN HC -> location_state
```

## 9. Intern Matching

File: `scripts/matching_engine.py`

Stable identifiers are strongest:

- Employee number
- CEMEX employee number
- Email
- CURP
- RFC
- NSS

Match confidence categories:

- `HIGH`: strong identifier match; no review needed.
- `MEDIUM`: secondary evidence; review recommended.
- `LOW`: no reliable match.
- `CONFLICT`: multiple possible matches or conflicting identifiers.

## 10. Requisition Matching

Primary key:

```text
requisition_id
```

The system also uses file/email/body metadata when available, but `requisition_id` is the main reliable key.

Requisitions are stored in:

```text
dim_requisitions
```

Power BI vacantes logic:

```text
vw_powerbi_vacantes
```

A requisition disappears from open vacancies when an intern exists with the same `requisition_id`.

## 11. CEMEX Org Relationship Logic

Practical hierarchy:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

`JefeInmediato` is not the official hierarchy, but it is a strong matching signal.

Strong relationships implemented:

```text
JefeInmediato -> VP HC
JefeInmediato -> CC HC
JefeInmediato -> OI HC
JefeInmediato -> CIA HC
OI HC          -> VP HC
OI HC          -> CC HC
CC HC          -> VP HC
CC HC          -> CIA HC
```

Important functions:

```python
clean_org_value
org_key
org_value_variants
manager_key
best_unique_candidate
query_dim_intern_relation
query_manager_assignment_relation
suggest_org_field
enrich_org_fields
upsert_manager_assignment_from_row
```

Operational table:

```text
dim_manager_assignments
```

Reporting view:

```text
vw_canonical_org_assignments
```

Current data quality status after cleanup:

```text
Missing VP HC: 0
Missing CIA HC: 0
Missing CC HC: 0
Missing OI HC: 0
Missing manager: 0
Duplicate employee numbers: 0
```

## 11.1 Baja Automation

The current-intern sync detects when an existing intern changes from active to inactive/baja.

Active status values:

```text
Activo
active
ST002
```

Inactive/baja status values:

```text
Baja
Inactivo
inactive
ST003
ST004
```

When the transition is:

```text
active -> inactive/baja
```

the pipeline:

1. Updates `dim_interns.status_id` with the incoming status from the sync file.
2. Inserts a lifecycle event:

```text
fact_intern_lifecycle_events.event_type = baja_requested
fact_intern_lifecycle_events.event_status = Prepared
fact_intern_lifecycle_events.process_type_id = PROC_BAJA
```

3. Creates an HR communication:

```text
fact_communications.communication_type = Baja De Practicante
fact_communications.recipient_group = HR
fact_communications.status = Prepared
```

Email subject format:

```text
Baja De Practicante - {NOMBRE COMPLETO}
```

Email body includes:

```text
Fecha de nacimiento
Correo personal
Universidad
Carrera
Semestre
Fecha de graduacion
CEMEX-ID
Correo institucional CEMEX
Vicepresidencia
Nombre del proyecto
Jefe directo
AIRH
Ubicacion UDN
Compania
OI
CC
Sueldo
Fecha de ingreso
Fecha fin
Estado de practicante
Nombre completo
```

The communication is prepared automatically. Real delivery still follows the configured communication sender safety controls.

## 12. Document Handling

Files:

```text
scripts/document_pipeline.py
azure_function_app/scripts/document_pipeline.py
```

The document pipeline:

1. Classifies document type by filename.
2. Extracts text from PDFs/docx when possible.
3. Uses Document Intelligence OCR fallback for scanned PDFs/images.
4. Matches document to candidate/intern.
5. Tracks received/missing/review status in SQL.

### Document Intelligence

Function App app settings confirmed:

```text
DOC_INTEL_ENDPOINT exists
DOC_INTEL_KEY exists
```

OCR method:

```text
prebuilt-read
api-version=2023-07-31
```

Behavior:

- If PDF has a text layer, local PDF extraction is used.
- If PDF has little/no text or file is image, Document Intelligence is called.
- If Document Intelligence is not configured or fails, OCR returns empty text and the pipeline continues best-effort.

### Paquete 1

Current required Paquete 1 documents:

```text
ALTA
CURP
CONSTANCIA_ESTUDIOS
IDENTIFICACION
COMPROBANTE_DOMICILIO
```

Not required:

```text
Professional photo
```

Emergency contact:

```text
Captured from email/body text or alta data, not as a separate document.
```

Config script:

```text
scripts/sql/2026-06_package1_document_requirements.sql
```

Legacy document requirements resolved/deactivated:

```text
CV
NDA
ID_INE
SCHOOL_PROOF
OFFER_LETTER
CERTIFICADO
ACTA_NACIMIENTO as required applicant doc
```

## 13. SQL Database Layers

The database uses operational tables plus reporting views.

### Operational Tables

Core dimensions:

```text
dim_interns
dim_requisitions
dim_manager_assignments
dim_required_document_types
dim_lifecycle_processes
dim_canonical_fields
dim_column_aliases
dim_validation_rules
dim_recipient_groups
dim_communication_templates
```

Core facts:

```text
fact_pipeline_runs
fact_processed_blobs
fact_files
fact_validations
fact_hires
fact_intern_document_status
fact_intern_documents
fact_intern_missing_items
fact_intern_lifecycle_events
fact_intern_beneficiaries
fact_communications
fact_communication_packages
fact_communication_package_files
fact_file_classification
fact_detected_columns
```

Do not drop operational tables during normal reporting cleanup.

### Canonical Views

```text
vw_canonical_interns_current
vw_canonical_intern_documents
vw_canonical_document_types
vw_canonical_org_assignments
vw_canonical_requisitions
vw_canonical_pipeline_runs
vw_schema_consolidation_recommendations
```

### Power BI Business Views

```text
vw_powerbi_vacantes
vw_powerbi_interns_status
vw_powerbi_costos_practicantes
vw_powerbi_expired_active_contracts
vw_powerbi_inactive_interns
vw_powerbi_vp_capacity
```

### Power BI No-DAX Views

These are designed for Power BI Service without Power BI Desktop/DAX:

```text
vw_powerbi_dashboard_kpis
vw_powerbi_vp_summary
vw_powerbi_location_summary
vw_powerbi_contract_risk
vw_powerbi_document_status
vw_powerbi_document_summary
vw_powerbi_hr_action_queue
```

### Legacy Compatibility Views

These remain for compatibility and audit detail:

```text
vw_full_mvp_interns_current
vw_full_mvp_document_status
vw_full_mvp_missing_items
vw_full_mvp_lifecycle_events
vw_full_mvp_pipeline_runs
vw_full_mvp_pipeline_summary
vw_full_mvp_file_classification
vw_full_mvp_detected_columns
vw_full_mvp_communication_packages
vw_full_mvp_package_files
vw_full_mvp_validation_errors
```

New reporting should prefer `vw_powerbi_*` and `vw_canonical_*`.

## 14. SQL Migration Order

Run SQL in this order for a new or refreshed environment:

```text
scripts/sql/fix_file_id_source_file_id_compatibility.sql
scripts/sql/create_full_mvp_pipeline.sql
scripts/sql/seed_pipeline_validation_rules.sql
scripts/sql/2026-06_package1_document_requirements.sql
scripts/sql/2026-06_resolve_stale_missing_items.sql
scripts/sql/add_corporate_column_aliases.sql
scripts/sql/create_matching_engine_v1.sql
scripts/sql/create_business_powerbi_views.sql
scripts/sql/2026-06_schema_simplification.sql
scripts/sql/2026-06_powerbi_no_dax_views.sql
scripts/sql/2026-06_onboarding_schema.sql
```

All current scripts are intended to be idempotent or safe to rerun. Avoid manual `DROP TABLE` operations unless a cutover plan exists.

## 15. Current Production-Like Data Status

After the latest cleanup:

```text
HC activos: 281
HC inactivos: 21
Terminan 0-30 dias: 53
Vencidos activos: 10
Vacantes abiertas: 0
Practicantes con docs faltantes: 0
Excepciones abiertas: 63
```

Remaining open exceptions:

```text
UPCOMING_EXPIRATION: 53
EXPIRED_ACTIVE_END_DATE: 10
```

These are legitimate contract-risk warnings, not stale data quality noise.

## 16. Power BI Configuration

Power BI is built in Power BI Service.

Recommended dataset mode:

```text
Import mode with scheduled refresh
```

Recommended refresh:

```text
Every 30 minutes, hourly, or daily depending on HR operational need.
```

Recommended pages:

1. Resumen Ejecutivo RH.
2. Vacantes y Capacidad.
3. Costos y Distribucion.
4. Vencimientos, Inactivos y Riesgo.
5. Documentos, Excepciones y Acciones RH.

Detailed setup:

```text
docs/power_bi_no_dax_5_pages.md
docs/power_bi_dashboard.md
```

## 17. Alerts

Alert recommendations are documented in:

```text
docs/email_alert_recommendations.md
```

Recommended first alerts:

1. Pipeline Failed.
2. File Moved To Failed.
3. Bad Rows Detected.
4. Missing Requisition ID.
5. Baja De Practicante.
6. Contract Expired But Still Active.
7. Contract Ending In 30 Days.
8. Power BI Refresh Failed.

Do not enable every alert at once. Start with production-critical alerts, then add HR operational alerts after real-world testing.

## 18. Email Intake

Current status:

- Gmail/dev intake exists.
- Outlook/Microsoft Graph path is prepared but not the current primary flow.
- Power Automate is no longer required as the main file intake mechanism.

Script:

```text
scripts/intake_gmail_attachments.py
```

Later real-life test plan:

1. Send current interns Excel.
2. Send requisition file.
3. Send candidate/onboarding packet.

This is intentionally deferred until after more real-life validation.

## 19. Security And Secrets

Never commit:

```text
.env
local.settings.json
real Azure connection strings
real SQL passwords
Document Intelligence key
Graph client secret
SMTP passwords
```

Use Azure Function App settings for deployed secrets.

Use managed identity for SQL from Azure Function:

```text
AZURE_SQL_AUTH_MODE=managed_identity
```

Local development can use:

```text
AZURE_SQL_AUTH_MODE=default
```

or another configured development mode.

## 20. Deployment Runbook

### Pre-Deploy Checks

From repo root:

```bash
.venv/bin/python scripts/check_function_readiness.py
.venv/bin/python scripts/smoke_e2e_pipeline.py
```

Optional Azure SQL view check:

```bash
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```

### Sync Function Modules

```bash
.venv/bin/python scripts/sync_function_modules.py
```

This copies updated modules from `scripts/` into `azure_function_app/scripts/`.

### Deploy Function

From `azure_function_app/`:

```bash
func azure functionapp publish mex-intern-pipeline-func-win --python
```

or deploy through VS Code Azure Functions extension.

### Restart Function

```bash
az functionapp restart \
  --resource-group rg-intern-system-dev \
  --name mex-intern-pipeline-func-win
```

## 21. SQL Maintenance Runbook

### Apply SQL Script Locally To Azure SQL

Use the existing Python/Azure SQL connection utilities. Scripts are separated by `GO`, so apply in batches.

Basic pattern:

```bash
.venv/bin/python -c "import re, sys; sys.path.insert(0,'scripts'); import azure_clients; sql=open('scripts/sql/<script>.sql', encoding='utf-8').read(); batches=[b.strip() for b in re.split(r'(?im)^\\s*GO\\s*$', sql) if b.strip()]; conn=azure_clients.get_sql_connection(); cur=conn.cursor(); [cur.execute(batch) for batch in batches]; conn.commit(); conn.close(); print(len(batches))"
```

If Azure SQL firewall blocks local access, create a temporary rule, apply changes, then delete it immediately.

### Temporary Firewall Rule

```bash
az sql server firewall-rule create \
  --resource-group rg-intern-system-dev \
  --server rg-intern-system-dev \
  --name codex-temp-maintenance \
  --start-ip-address <your-ip> \
  --end-ip-address <your-ip>
```

Delete it after work:

```bash
az sql server firewall-rule delete \
  --resource-group rg-intern-system-dev \
  --server rg-intern-system-dev \
  --name codex-temp-maintenance
```

## 22. Verification Queries

### Dashboard KPI Check

```sql
SELECT *
FROM dbo.vw_powerbi_dashboard_kpis;
```

### Remaining Exceptions

```sql
SELECT issue_field, issue_type, severity, COUNT(*) AS issue_count
FROM dbo.vw_business_validation_exceptions
GROUP BY issue_field, issue_type, severity
ORDER BY issue_count DESC;
```

### Org Completeness

```sql
SELECT
    SUM(CASE WHEN vp IS NULL OR LTRIM(RTRIM(vp)) = '' THEN 1 ELSE 0 END) AS missing_vp,
    SUM(CASE WHEN cia_hc IS NULL OR LTRIM(RTRIM(cia_hc)) = '' THEN 1 ELSE 0 END) AS missing_cia,
    SUM(CASE WHEN cc_hc IS NULL OR LTRIM(RTRIM(cc_hc)) = '' THEN 1 ELSE 0 END) AS missing_cc,
    SUM(CASE WHEN oi_hc IS NULL OR LTRIM(RTRIM(oi_hc)) = '' THEN 1 ELSE 0 END) AS missing_oi,
    SUM(CASE WHEN manager IS NULL OR LTRIM(RTRIM(manager)) = '' THEN 1 ELSE 0 END) AS missing_manager
FROM dbo.vw_powerbi_interns_status;
```

### Contract Risk

```sql
SELECT risk_bucket, COUNT(*) AS intern_count
FROM dbo.vw_powerbi_contract_risk
GROUP BY risk_bucket
ORDER BY risk_bucket;
```

### Active Paquete 1 Requirements

```sql
SELECT
    pr.process_type_id,
    rdt.document_code,
    rdt.document_name,
    pr.requirement_scope,
    pr.is_required
FROM dbo.fact_process_requirements pr
JOIN dbo.dim_required_document_types rdt
    ON pr.required_document_type_id = rdt.required_document_type_id
WHERE pr.process_type_id IN ('PROC_NEW_HIRE', 'PROC_ALTA')
  AND pr.requirement_scope = 'Applicant'
  AND pr.is_required = 1
ORDER BY pr.process_type_id, rdt.document_code;
```

## 23. Troubleshooting

### Function Does Not Trigger

Check:

- Blob landed under `raw-uploads`.
- Blob path does not start with ignored prefixes.
- Function App is running.
- `AzureWebJobsFeatureFlags=EnableWorkerIndexing` exists.
- Storage connection string is valid.
- Event Grid/blob trigger wiring is healthy.

### File Fails Processing

Check:

- `fact_pipeline_runs` for failed run.
- `fact_processed_blobs` for blob status.
- `fact_validations` for row-level issues.
- `error-reports` container/path.
- Azure Function logs.

### Power BI Shows Old Data

Check:

- Dataset refresh status in Power BI Service.
- SQL views return current data.
- Power BI connection points to correct Azure SQL database.
- Import mode refresh schedule is enabled.

### Missing Docs Looks Too High

Check:

- `vw_powerbi_dashboard_kpis.practicantes_con_docs_faltantes`.
- `vw_powerbi_document_status` filtered by `is_missing = 1`.
- Paquete 1 config in `fact_process_requirements`.
- Make sure legacy missing document rows are resolved by `2026-06_package1_document_requirements.sql`.

### Org Fields Missing

Check:

- `dim_manager_assignments`.
- `vw_canonical_org_assignments`.
- Current intern row has at least one strong signal: `JefeInmediato`, `OI HC`, `CC HC`, `VP HC`, `CIA HC`.

### OCR Does Not Work

Check:

- Function App settings `DOC_INTEL_ENDPOINT` and `DOC_INTEL_KEY`.
- Document Intelligence resource is active.
- File extension is supported.
- PDF/image is readable.
- Azure Function has outbound network access.

## 24. Known Deferred Work

These are intentionally deferred until after real-life testing:

- Three-email end-to-end test:
  - DB update file.
  - Requisition file.
  - Candidate/onboarding packet.
- Final production cutover.
- Deleting legacy tables/views.
- Enabling all email alerts.
- Real recipient email sending.
- Row-level security in Power BI, if HR requires VP-based data separation.

## 25. Git Workflow

Recommended branch naming:

```text
codex/<short-feature-name>
```

Before commit:

```bash
.venv/bin/python scripts/smoke_e2e_pipeline.py
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
git status --short
git diff --stat
```

Commit message style:

```text
Implement intern pipeline automation and Power BI reporting
```

Do not commit `.env`, local settings with secrets, generated temp files, or real exported HR files unless explicitly approved.

## 26. Operational Ownership

Suggested owners:

- HR data owner:
  - Reviews Power BI dashboard and data issues.
  - Decides alert thresholds.
  - Confirms business labels and status meanings.
- System owner:
  - Maintains Azure Function, SQL scripts, secrets, and deployments.
  - Reviews failed pipeline runs.
  - Applies schema/config migrations.
- Power BI owner:
  - Maintains report layout, refresh, permissions.
  - Coordinates workspace/app access.

## 27. Quick Commands

Run smoke test:

```bash
.venv/bin/python scripts/smoke_e2e_pipeline.py
```

Run smoke with SQL view check:

```bash
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```

Check Function readiness:

```bash
.venv/bin/python scripts/check_function_readiness.py
```

Sync Function modules:

```bash
.venv/bin/python scripts/sync_function_modules.py
```

List Function App settings names only:

```bash
az functionapp config appsettings list \
  --resource-group rg-intern-system-dev \
  --name mex-intern-pipeline-func-win \
  --query "[].name" \
  --output table
```

Restart Function:

```bash
az functionapp restart \
  --resource-group rg-intern-system-dev \
  --name mex-intern-pipeline-func-win
```

Send a one-time report of active interns with expired contracts:

```bash
.venv/bin/python scripts/send_expired_active_contracts_email.py
```

The command above is a dry run. To actually send through configured SMTP:

```bash
.venv/bin/python scripts/send_expired_active_contracts_email.py --send
```

## 28. Final Current State

As of this manual:

- Power BI reporting views are created.
- Power BI no-DAX views are created.
- Document Intelligence settings are present on the real Function App.
- Paquete 1 document configuration is aligned.
- Legacy missing-document noise was resolved.
- Current data has complete org fields.
- Remaining exceptions are contract-risk warnings only.
- Email real-life three-file testing is deferred.
- Final cutover is deferred until after real-life testing.
