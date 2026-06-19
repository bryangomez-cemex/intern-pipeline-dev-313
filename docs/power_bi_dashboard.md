# Power BI Dashboard

Connect Power BI to Azure SQL and load the full MVP views.

## Views

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

## Recommended Visuals

- Pipeline runs by status, run type, and date.
- Files by detected profile, confidence, and needs-review flag.
- Detected source columns mapped to canonical fields.
- Missing items by process type, severity, status, and missing code.
- Current interns by VP, area, university, status, company, OI, and CC.
- Upcoming expirations from `vw_full_mvp_interns_current`.
- Inactive/baja counts from current intern status and lifecycle events.
- Document status by document type and intern.
- Validation errors by file, rule, severity, and process.
- Communication packages by recipient group and status.

## Verification Queries

```sql
SELECT TOP 25 * FROM dbo.vw_full_mvp_pipeline_runs ORDER BY started_at DESC;
SELECT TOP 25 * FROM dbo.vw_full_mvp_file_classification ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_full_mvp_missing_items ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_full_mvp_communication_packages ORDER BY created_at DESC;
```
