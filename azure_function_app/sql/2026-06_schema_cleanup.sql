/*
Schema cleanup (2026-06).

Drops unused matching-engine tables (0 rows, the matching engine is not used by the
deployed pipeline) and ~20 legacy/compatibility views that no vw_powerbi_* view (or
the pipeline) references — the Power BI dashboard uses only vw_powerbi_* views.

REVERSIBLE: the views can be recreated from create_business_powerbi_views.sql,
create_matching_engine_v1.sql, and the 2026-06_*.sql migrations.

ONE-TIME cleanup — intentionally NOT part of SQL_SETUP_ORDER.
*/

-- ── Legacy / compatibility views (nothing depends on them) ───────────────────
DROP VIEW IF EXISTS dbo.vw_full_mvp_communication_packages;
DROP VIEW IF EXISTS dbo.vw_full_mvp_detected_columns;
DROP VIEW IF EXISTS dbo.vw_full_mvp_document_status;
DROP VIEW IF EXISTS dbo.vw_full_mvp_file_classification;
DROP VIEW IF EXISTS dbo.vw_full_mvp_interns_current;
DROP VIEW IF EXISTS dbo.vw_full_mvp_lifecycle_events;
DROP VIEW IF EXISTS dbo.vw_full_mvp_package_files;
DROP VIEW IF EXISTS dbo.vw_full_mvp_pipeline_runs;
DROP VIEW IF EXISTS dbo.vw_full_mvp_pipeline_summary;
DROP VIEW IF EXISTS dbo.vw_full_mvp_validation_errors;
DROP VIEW IF EXISTS dbo.vw_canonical_document_types;
DROP VIEW IF EXISTS dbo.vw_canonical_interns_current;
DROP VIEW IF EXISTS dbo.vw_canonical_org_assignments;
DROP VIEW IF EXISTS dbo.vw_canonical_pipeline_runs;
DROP VIEW IF EXISTS dbo.vw_canonical_requisitions;
DROP VIEW IF EXISTS dbo.vw_matching_engine_conflicts;
DROP VIEW IF EXISTS dbo.vw_matching_engine_review_queue;
DROP VIEW IF EXISTS dbo.vw_pipeline_files;
DROP VIEW IF EXISTS dbo.vw_pipeline_summary;
DROP VIEW IF EXISTS dbo.vw_requisitions_status;
DROP VIEW IF EXISTS dbo.vw_validation_errors;
DROP VIEW IF EXISTS dbo.vw_schema_consolidation_recommendations;
GO

-- ── Unused matching-engine tables (0 rows, not written by the pipeline) ───────
DROP TABLE IF EXISTS dbo.fact_match_conflicts;
DROP TABLE IF EXISTS dbo.fact_match_candidates;
DROP TABLE IF EXISTS dbo.fact_entity_matches;
GO
