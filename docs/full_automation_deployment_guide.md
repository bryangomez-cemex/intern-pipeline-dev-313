# Full Automation Deployment Guide

Use fake data only until corporate email approvals are complete.

## Azure Storage

Create or keep these containers:

- `raw-uploads`
- `error-reports`
- `archive`

Email intake, local scripts, Gmail dev intake, and manual Azure uploads should only place source files in `raw-uploads`.

## Azure SQL

Fresh Azure SQL database setup order:

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

The `00_*` scripts are required for a brand-new database because the historical
pipeline assumed some base tables already existed. The deployed setup helper and
temporary Azure Container Instance setup path use this fresh-database order.

Power BI should read the `vw_powerbi_*` and `vw_canonical_*` views, not raw operational tables. Legacy `vw_full_mvp_*` views remain available only for compatibility and deep audit detail.

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
- `SEND_EMAILS=false`
- `DEV_EMAIL_OVERRIDE`
- `DOC_INTEL_ENDPOINT`
- `DOC_INTEL_KEY`
- `AzureWebJobsFeatureFlags=EnableWorkerIndexing`

The Blob Trigger calls the same `pipeline_service.py` used by local/manual scripts.

## Email / Upload Intake

Power Automate is not part of the current operating path. The intake side only
needs to create blobs in `raw-uploads`. The blob name should be descriptive
enough for classification, for example:

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
