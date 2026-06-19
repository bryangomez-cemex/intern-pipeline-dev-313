# Intern System Pipeline

Fake-data-first MVP for an automated intern/practicante lifecycle pipeline.

The pipeline supports:

- Requisitions: new positions, altas, extendimientos, bajas, OI/CC/manager/status changes.
- Accepted new hires: Excel/CSV intake, intern record creation/update, missing data/document detection, correction requests, HR/Coparmex/applicant package metadata.
- Current interns: Excel/CSV sync, active/inactive/baja detection, upcoming expiration alerts, missing/expired document checks, and Power BI-ready reporting.

Do not upload real personal data. Use fake intern names, fake emails, fake identifiers, and dev-only mailboxes.

## Architecture

Outlook, Power Automate, Power Apps, Gmail dev intake, or local upload drops files into Azure Blob `raw-uploads`.

Processing paths:

- Local/Gmail dev: `scripts/run_intake_pipeline.py`
- Manual: `scripts/process_blob_file.py`
- Azure automation: `azure_function_app/function_app.py`

All paths call `scripts/pipeline_service.py`, which writes Azure SQL records, creates error reports/packages, and archives source blobs.

## Required Azure Blob Containers

- `raw-uploads`
- `error-reports`
- `archive`

## Main Setup

Run this SQL script in Azure Query Editor:

```text
scripts/sql/create_full_mvp_pipeline.sql
```

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
DEV_EMAIL_OVERRIDE=dev-only@example.com
```

`EMAIL_MODE=simulation` is the safe default.

## Local Commands

Compile:

```bash
python -m py_compile scripts/process_blob_file.py scripts/pipeline_service.py scripts/run_intake_pipeline.py scripts/flexible_file_classifier.py scripts/lifecycle_requirements.py scripts/communication_packager.py scripts/graph_email_client.py scripts/send_prepared_communications.py scripts/send_real_dev_email_smtp.py
```

Local folder intake:

```bash
python scripts/run_intake_pipeline.py local
```

Gmail dev intake:

```bash
python scripts/run_intake_pipeline.py gmail
```

Manual processing:

```bash
python scripts/process_blob_file.py
```

Email simulation:

```bash
python scripts/send_prepared_communications.py
```

Real dev SMTP email, still redirected only to `DEV_EMAIL_OVERRIDE`:

```bash
python scripts/send_real_dev_email_smtp.py
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

## Power BI Views

Load these Azure SQL views:

- `vw_full_mvp_pipeline_summary`
- `vw_full_mvp_file_classification`
- `vw_full_mvp_detected_columns`
- `vw_full_mvp_missing_items`
- `vw_full_mvp_lifecycle_events`
- `vw_full_mvp_document_status`
- `vw_full_mvp_communication_packages`
- `vw_full_mvp_package_files`
- `vw_full_mvp_interns_current`
- `vw_full_mvp_validation_errors`
- `vw_full_mvp_pipeline_runs`
# intern-pipeline-dev-313
# intern-pipeline-dev-313
