# Intern System Pipeline

Automated intern/practicante lifecycle pipeline for CEMEX HR.

The pipeline supports:

- Requisitions: new positions, altas, extendimientos, bajas, OI/CC/manager/status changes.
- Accepted new hires: Excel/CSV intake, intern record creation/update, missing data/document detection, correction requests, HR/Coparmex/applicant package metadata.
- Current interns: Excel/CSV sync, active/inactive/baja detection, upcoming expiration alerts, missing/expired document checks, and Power BI-ready reporting.

Live email uses the configured Gmail app account for intake and SMTP sending.

## Architecture

Gmail intake in Azure, Azure/manual upload, or local upload drops files into Azure Blob `raw-uploads`.

Processing paths:

- Local/dev intake: `scripts/run_intake_pipeline.py`
- Manual: `scripts/process_blob_file.py`
- Azure automation: `azure_function_app/function_app.py`

All paths call `scripts/pipeline_service.py`, which writes Azure SQL records, creates error reports/packages, and archives source blobs.

## Required Azure Blob Containers

- `raw-uploads`
- `error-reports`
- `archive`

## Main Setup

When configuring a new empty Azure SQL database for this existing project, run
these SQL scripts in this order:

```text
scripts/sql/00_create_core_legacy_tables.sql
scripts/sql/00_create_dim_interns.sql
scripts/sql/create_full_mvp_pipeline.sql
scripts/sql/fix_file_id_source_file_id_compatibility.sql
scripts/sql/seed_pipeline_validation_rules.sql
scripts/sql/2026-06_package1_document_requirements.sql
scripts/sql/2026-06_resolve_stale_missing_items.sql
scripts/sql/add_corporate_column_aliases.sql
scripts/sql/create_matching_engine_v1.sql
scripts/sql/create_business_powerbi_views.sql
scripts/sql/2026-06_onboarding_schema.sql
scripts/sql/2026-06_schema_simplification.sql
scripts/sql/2026-06_powerbi_no_dax_views.sql
```

For an older dev database that already has base tables, the compatibility script
can be run before or after `create_full_mvp_pipeline.sql`; for a new empty
database, run the two `00_*` scripts first.

Required local `.env` values:

```bash
AZURE_STORAGE_CONNECTION_STRING=...
RAW_UPLOADS_CONTAINER=raw-uploads
ERROR_REPORTS_CONTAINER=error-reports
ARCHIVE_CONTAINER=archive
AZURE_SQL_SERVER=...
AZURE_SQL_DATABASE=intern_system_dev
AZURE_SQL_AUTH_MODE=interactive
EMAIL_MODE=simulation
SEND_EMAILS=false
DEV_EMAIL_OVERRIDE=dev-only@example.com
DOC_INTEL_ENDPOINT=...
DOC_INTEL_KEY=...
```

`EMAIL_MODE=simulation` and `SEND_EMAILS=false` are the safe defaults.

## Local Commands

Use the project virtual environment when it exists:

```bash
source .venv/bin/activate
```

Install local dependencies:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Compile:

```bash
.venv/bin/python -m py_compile scripts/process_blob_file.py scripts/pipeline_service.py scripts/run_intake_pipeline.py scripts/flexible_file_classifier.py scripts/lifecycle_requirements.py scripts/matching_engine.py scripts/communication_packager.py scripts/graph_email_client.py scripts/send_prepared_communications.py scripts/send_real_dev_email_smtp.py scripts/check_function_readiness.py scripts/smoke_e2e_pipeline.py scripts/deployment_readiness_e2e.py scripts/onboarding_pipeline.py scripts/document_pipeline.py scripts/requisition_parser.py
```

Safe smoke test, no Blob/SQL writes and no real emails:

```bash
.venv/bin/python scripts/smoke_e2e_pipeline.py
```

Deployment readiness E2E, offline by default with no Blob/SQL writes and no real emails:

```bash
EMAIL_MODE=simulation .venv/bin/python scripts/deployment_readiness_e2e.py
```

Deployment readiness E2E against staging Azure, opt-in fake-data dry run only:

```bash
EMAIL_MODE=simulation SEND_EMAILS=false EMAIL_DRY_RUN=true .venv/bin/python scripts/deployment_readiness_e2e.py --live-azure --confirm-live-dry-run TEST
```

Optional read-only Azure SQL view check:

```bash
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```

Local folder intake:

```bash
python3 scripts/run_intake_pipeline.py local
```

Gmail local test intake:

```bash
python3 scripts/run_intake_pipeline.py gmail
```

Manual processing:

```bash
python3 scripts/process_blob_file.py
```

Email simulation:

```bash
python3 scripts/send_prepared_communications.py
```

Real dev SMTP email, still redirected only to `DEV_EMAIL_OVERRIDE`:

```bash
python3 scripts/send_real_dev_email_smtp.py
```

## Azure Function

The Function app lives in `azure_function_app/` and triggers on:

```text
raw-uploads/{name}
```

Local function test:

```bash
cd azure_function_app
cp local.settings.example.json local.settings.json
func start
```

Upload a fake test file to `raw-uploads` and verify Azure SQL rows in the Power BI views.

## Power BI Business Views

Load these Azure SQL views:

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
- `vw_powerbi_costos_practicantes`
- `vw_powerbi_expired_active_contracts`
- `vw_powerbi_inactive_interns`
- `vw_powerbi_vp_capacity`
- `vw_powerbi_dashboard_kpis`
- `vw_powerbi_vp_summary`
- `vw_powerbi_location_summary`
- `vw_powerbi_contract_risk`
- `vw_powerbi_document_status`
- `vw_powerbi_document_summary`
- `vw_powerbi_hr_action_queue`

The legacy `vw_full_mvp_*` views remain available for compatibility, but new reporting should prefer `vw_powerbi_*` for requested HR pages and `vw_canonical_*` for shared entities.

## Operations Docs

- Technical manual: `docs/technical_manual.md`
- Power BI Service setup without DAX/Desktop: `docs/power_bi_no_dax_5_pages.md`
- Email alert recommendations: `docs/email_alert_recommendations.md`
- Schema simplification notes: `docs/schema_simplification.md`

## Email (Gmail SMTP)

Email from step 5 onward uses **Gmail SMTP**, via `scripts/email_service.py`
(`send_email(...)`). `onboarding_pipeline.send_email` delegates to it. Config is
read only from environment variables — set these locally
(`.env`) and in the **Azure Function App → Settings → Environment variables / Application
settings**:

```
EMAIL_PROVIDER=smtp
EMAIL_SIMULATION_MODE=true      # safe default; false to send for real
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=...
SMTP_FROM_NAME=Programa de Practicantes CEMEX
TEST_EMAIL_TO=...
RH_RECIPIENT_EMAILS=bryan.gomez@ext.cemex.com,valeria.acunaam@cemex.com
```

`RH_RECIPIENT_EMAILS` are fixed internal recipients for HR notifications and
Coparmex-ready packages. RH reviews those emails and forwards them to Coparmex.
Practicantes usually use CEMEX emails, while new hires may still use personal
emails until their CEMEX account exists — `resolve_person_email()` picks the
correct field by person/process type.
Test locally with `python scripts/test_email_service.py`.
