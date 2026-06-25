/*
Schema simplification layer.

This script is intentionally non-destructive. It creates canonical views that
Power BI and ad-hoc analysis should use first, while keeping operational tables
and legacy compatibility views in place for the automation pipeline.
*/

CREATE OR ALTER VIEW dbo.vw_canonical_interns_current AS
SELECT
    intern_id,
    employee_number,
    cemex_employee_number,
    intern_name,
    position_name,
    manager,
    vp,
    ubicacion_hc,
    estado_ubicacion_hc,
    cia_hc,
    oi_hc,
    cc_hc,
    start_date,
    contract_end_date,
    raw_status,
    normalized_status,
    is_active,
    is_inactive,
    is_contract_expired,
    days_until_contract_end,
    importe_total,
    latest_status_event_date
FROM dbo.vw_powerbi_interns_status;
GO

CREATE OR ALTER VIEW dbo.vw_canonical_document_types AS
SELECT
    required_document_type_id AS document_type_id,
    document_code,
    document_name,
    description,
    allowed_file_extensions,
    required_for_coparmex,
    required_for_hr,
    required_for_applicant,
    is_active,
    created_at
FROM dbo.dim_required_document_types;
GO

CREATE OR ALTER VIEW dbo.vw_canonical_intern_documents AS
SELECT
    'fact_intern_document_status' AS source_table,
    ids.intern_document_status_id AS canonical_document_id,
    ids.intern_id,
    i.nombre_completo AS intern_name,
    ids.process_type_id,
    CAST(NULL AS NVARCHAR(30)) AS stage,
    COALESCE(rdt.document_code, ids.document_type_id) AS document_code,
    COALESCE(rdt.document_name, ids.document_type_id) AS document_name,
    ids.file_id,
    CAST(NULL AS NVARCHAR(300)) AS file_name,
    CAST(NULL AS NVARCHAR(400)) AS blob_path,
    ids.status,
    ids.validation_status,
    ids.is_required,
    ids.is_missing,
    ids.is_expired,
    ids.expires_at,
    ids.reviewed_at,
    ids.notes,
    ids.created_at,
    ids.updated_at
FROM dbo.fact_intern_document_status ids
LEFT JOIN dbo.dim_interns i
    ON ids.intern_id = i.intern_id
LEFT JOIN dbo.dim_required_document_types rdt
    ON ids.document_type_id = rdt.required_document_type_id
    OR ids.document_type_id = rdt.document_code
UNION ALL
SELECT
    'fact_intern_documents' AS source_table,
    d.document_id AS canonical_document_id,
    d.intern_id,
    i.nombre_completo AS intern_name,
    CAST(NULL AS NVARCHAR(50)) AS process_type_id,
    d.stage,
    d.document_type AS document_code,
    COALESCE(rdt.document_name, d.document_type) AS document_name,
    CAST(NULL AS NVARCHAR(50)) AS file_id,
    d.file_name,
    d.blob_path,
    d.status,
    CAST(NULL AS NVARCHAR(100)) AS validation_status,
    CAST(NULL AS BIT) AS is_required,
    CASE WHEN d.status IN ('missing', 'Missing') THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_missing,
    CAST(0 AS BIT) AS is_expired,
    CAST(NULL AS DATETIME2) AS expires_at,
    CAST(NULL AS DATETIME2) AS reviewed_at,
    d.notes,
    d.created_at,
    CAST(NULL AS DATETIME2) AS updated_at
FROM dbo.fact_intern_documents d
LEFT JOIN dbo.dim_interns i
    ON d.intern_id = i.intern_id
LEFT JOIN dbo.dim_required_document_types rdt
    ON d.document_type = rdt.document_code
    OR d.document_type = rdt.required_document_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_canonical_org_assignments AS
SELECT
    ma.jefe_key,
    ma.jefe_directo AS jefe_inmediato,
    ma.vp AS vp_hc,
    ma.compania AS cia_hc,
    ma.cc AS cc_hc,
    ma.oi AS oi_hc,
    ma.ubicacion_udn,
    ma.estado,
    ma.asesor_rh,
    COUNT(i.intern_id) AS current_intern_rows,
    ma.updated_at
FROM dbo.dim_manager_assignments ma
LEFT JOIN dbo.dim_interns i
    ON i.jefe_inmediato = ma.jefe_directo
    OR i.vp_hc = ma.vp
    OR i.cc_hc = ma.cc
    OR i.oi_hc = ma.oi
GROUP BY
    ma.jefe_key,
    ma.jefe_directo,
    ma.vp,
    ma.compania,
    ma.cc,
    ma.oi,
    ma.ubicacion_udn,
    ma.estado,
    ma.asesor_rh,
    ma.updated_at;
GO

CREATE OR ALTER VIEW dbo.vw_canonical_requisitions AS
SELECT
    r.requisition_id,
    COALESCE(r.puesto, r.requisition_type) AS position_name,
    COALESCE(r.vp_hc, r.vp) AS vp_hc,
    r.area,
    COALESCE(r.manager, r.manager_name) AS manager,
    r.oi_hc,
    r.cc_hc,
    r.company AS cia_hc,
    r.requisition_status,
    r.requested_start_date,
    r.requested_end_date,
    r.created_at,
    r.updated_at,
    COUNT(i.intern_id) AS assigned_intern_count,
    CASE WHEN COUNT(i.intern_id) > 0 THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_filled
FROM dbo.dim_requisitions r
LEFT JOIN dbo.dim_interns i
    ON i.requisition_id = r.requisition_id
GROUP BY
    r.requisition_id,
    COALESCE(r.puesto, r.requisition_type),
    COALESCE(r.vp_hc, r.vp),
    r.area,
    COALESCE(r.manager, r.manager_name),
    r.oi_hc,
    r.cc_hc,
    r.company,
    r.requisition_status,
    r.requested_start_date,
    r.requested_end_date,
    r.created_at,
    r.updated_at;
GO

CREATE OR ALTER VIEW dbo.vw_canonical_pipeline_runs AS
SELECT
    pr.run_id,
    pr.run_type,
    pr.source_script,
    pr.status,
    pr.started_at,
    pr.finished_at,
    pr.source_container,
    pr.source_blob_name,
    pr.archived_blob_name,
    pr.source_file_id,
    pr.good_rows,
    pr.bad_rows,
    pr.total_rows,
    pr.error_message,
    pb.processed_at,
    pb.status AS processed_blob_status
FROM dbo.fact_pipeline_runs pr
LEFT JOIN dbo.fact_processed_blobs pb
    ON pr.run_id = pb.run_id;
GO

CREATE OR ALTER VIEW dbo.vw_schema_consolidation_recommendations AS
SELECT
    object_name,
    object_type,
    recommendation,
    canonical_replacement,
    drop_readiness,
    notes
FROM (VALUES
    ('vw_full_mvp_interns_current', 'view', 'Keep as compatibility alias only', 'vw_canonical_interns_current', 'Later', 'Existing docs and smoke tests used this name; Power BI should move to canonical/powerbi views.'),
    ('vw_full_mvp_document_status', 'view', 'Keep as compatibility alias only', 'vw_canonical_intern_documents', 'Later', 'Use the canonical document view for combined lifecycle and onboarding document status.'),
    ('vw_full_mvp_missing_items', 'view', 'Keep for operational HR action queue', 'vw_hr_actions_today', 'Later', 'Still useful as source detail behind HR actions.'),
    ('vw_full_mvp_lifecycle_events', 'view', 'Keep for audit detail only', 'vw_hr_actions_today', 'Later', 'Do not use for main Power BI pages unless auditing lifecycle events.'),
    ('dim_required_document_types', 'table', 'Keep as source table', 'vw_canonical_document_types', 'Do not drop', 'Pipeline joins directly to this table.'),
    ('fact_intern_document_status', 'table', 'Keep as lifecycle document fact', 'vw_canonical_intern_documents', 'Do not drop', 'Lifecycle requirements and packaging write/read this table.'),
    ('fact_intern_documents', 'table', 'Keep as onboarding document fact', 'vw_canonical_intern_documents', 'Do not drop', 'Onboarding document extraction writes this table.'),
    ('dim_manager_assignments', 'table', 'Keep as org matching memory', 'vw_canonical_org_assignments', 'Do not drop', 'Used to fill CIA/VP/CC/OI from JefeInmediato and related org fields.'),
    ('fact_pipeline_runs', 'table', 'Keep as run audit source', 'vw_canonical_pipeline_runs', 'Do not drop', 'Needed for Azure Function and load audit history.'),
    ('fact_processed_blobs', 'table', 'Keep as idempotency/audit source', 'vw_canonical_pipeline_runs', 'Do not drop', 'Prevents duplicate blob processing.'),
    ('dim_file_profiles', 'table', 'Keep only if file classifier remains active', 'vw_full_mvp_file_classification', 'Review after 30 days', 'Candidate for later cleanup if all intake uses metadata/content matching.'),
    ('fact_detected_columns', 'table', 'Keep as ingestion diagnostics', 'vw_full_mvp_detected_columns', 'Review after 30 days', 'Useful during new Excel layouts; can be archived later.'),
    ('dim_communication_templates', 'table', 'Keep if automated packages continue', 'vw_communications_status', 'Review after 30 days', 'Template table may become config if communications expand.'),
    ('dim_recipient_groups', 'table', 'Keep if automated packages continue', 'vw_communications_status', 'Review after 30 days', 'Recipient group config for package generation.')
) AS r(object_name, object_type, recommendation, canonical_replacement, drop_readiness, notes);
GO
