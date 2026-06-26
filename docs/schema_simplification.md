# Schema Simplification

This database now has a safe reporting layer instead of asking Power BI to read every operational table directly.

## Keep As Canonical

Use these views first:

- `vw_powerbi_vacantes`
- `vw_powerbi_interns_status`
- `vw_powerbi_costos_practicantes`
- `vw_powerbi_expired_active_contracts`
- `vw_powerbi_inactive_interns`
- `vw_powerbi_vp_capacity`
- `vw_canonical_interns_current`
- `vw_canonical_intern_documents`
- `vw_canonical_document_types`
- `vw_canonical_org_assignments`
- `vw_canonical_requisitions`
- `vw_canonical_pipeline_runs`
- `vw_schema_consolidation_recommendations`

## Keep Operational Tables

Do not drop these yet. The automation still reads or writes them directly:

- `dim_interns`
- `dim_requisitions`
- `dim_required_document_types`
- `dim_manager_assignments`
- `fact_hires`
- `fact_intern_document_status`
- `fact_intern_documents`
- `fact_intern_missing_items`
- `fact_intern_lifecycle_events`
- `fact_pipeline_runs`
- `fact_processed_blobs`
- `fact_files`
- `fact_validations`
- `fact_communications`

## Combine By View, Not By Table Yet

- Document tracking is intentionally split:
  - `fact_intern_document_status` handles lifecycle-required document status.
  - `fact_intern_documents` handles onboarding document extraction and convenio flow.
  - `vw_canonical_intern_documents` combines both for reporting.
- Intern/current status is centralized in:
  - `vw_powerbi_interns_status` for Power BI metrics.
  - `vw_canonical_interns_current` for general reporting.
- Org matching is centralized in:
  - `dim_manager_assignments` as matching memory.
  - `vw_canonical_org_assignments` for reporting and review.

## Later Cleanup Candidates

Review these after 30 days of real email-triggered usage:

- `vw_full_mvp_*` views: keep only if a report still depends on them.
- `dim_file_profiles`: keep if classifier diagnostics are still useful.
- `fact_detected_columns`: keep during layout changes; archive later if stable.
- `dim_communication_templates` and `dim_recipient_groups`: keep if communication packaging expands.

Run this in Azure SQL for the live recommendation list:

```sql
SELECT *
FROM dbo.vw_schema_consolidation_recommendations
ORDER BY drop_readiness, object_name;
```
