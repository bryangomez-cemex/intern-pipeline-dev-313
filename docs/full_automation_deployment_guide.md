# Full Automation Deployment Guide

Use fake data only until corporate approvals are complete.

## Azure Storage

Create or keep these containers:

- `raw-uploads`
- `error-reports`
- `archive`

Power Automate, Power Apps, local scripts, and Gmail dev intake should only place source files in `raw-uploads`.

## Azure SQL

Run in Azure Query Editor:

```text
scripts/sql/create_full_mvp_pipeline.sql
```

Power BI should read the `vw_full_mvp_*` views, not raw operational tables.

## Azure Function

Deploy `azure_function_app/`.

Required app settings:

- `AZURE_STORAGE_CONNECTION_STRING`
- `RAW_UPLOADS_CONTAINER=raw-uploads`
- `ERROR_REPORTS_CONTAINER=error-reports`
- `ARCHIVE_CONTAINER=archive`
- `AZURE_SQL_SERVER`
- `AZURE_SQL_DATABASE`
- `AZURE_SQL_AUTH_MODE=managed_identity` for deployed Function, or `interactive` for local dev
- `EMAIL_MODE=simulation`
- `DEV_EMAIL_OVERRIDE`

The Blob Trigger calls the same `pipeline_service.py` used by local/manual scripts.

## Power Automate / Power Apps

The platform side only needs to create blobs in `raw-uploads`. The blob name should be descriptive enough for classification, for example:

- `accepted_hires/fake_accepted_hires_2026_06.xlsx`
- `current_interns/fake_current_interns_2026_06.csv`
- `documents/fake_cv_INT-001.pdf`

## Microsoft Graph Email

Graph is disabled by default.

Optional env vars for later:

- `GRAPH_TENANT_ID`
- `GRAPH_CLIENT_ID`
- `GRAPH_CLIENT_SECRET`
- `GRAPH_SENDER_USER`
- `EMAIL_MODE=graph_draft` or `graph_send`

Do not use `graph_send` until real recipients and approvals are ready.
