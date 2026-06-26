IF OBJECT_ID('dbo.fact_intern_document_status', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_intern_document_status', 'file_id') IS NULL
        ALTER TABLE dbo.fact_intern_document_status ADD file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_intern_document_status', 'source_file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_intern_document_status SET file_id = COALESCE(file_id, source_file_id) WHERE file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_intern_lifecycle_events', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_intern_lifecycle_events', 'file_id') IS NULL
        ALTER TABLE dbo.fact_intern_lifecycle_events ADD file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_intern_lifecycle_events', 'source_file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_intern_lifecycle_events SET file_id = COALESCE(file_id, source_file_id) WHERE file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_file_classification', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_file_classification', 'file_id') IS NULL
        ALTER TABLE dbo.fact_file_classification ADD file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_file_classification', 'source_file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_file_classification SET file_id = COALESCE(file_id, source_file_id) WHERE file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_detected_columns', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_detected_columns', 'file_id') IS NULL
        ALTER TABLE dbo.fact_detected_columns ADD file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_detected_columns', 'source_file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_detected_columns SET file_id = COALESCE(file_id, source_file_id) WHERE file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_communication_package_files', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_communication_package_files', 'file_id') IS NULL
        ALTER TABLE dbo.fact_communication_package_files ADD file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_communication_package_files', 'source_file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_communication_package_files SET file_id = COALESCE(file_id, source_file_id) WHERE file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_intern_missing_items', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_intern_missing_items', 'source_file_id') IS NULL
        ALTER TABLE dbo.fact_intern_missing_items ADD source_file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_intern_missing_items', 'file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_intern_missing_items SET source_file_id = COALESCE(source_file_id, file_id) WHERE source_file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_hires', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_hires', 'source_file_id') IS NULL
        ALTER TABLE dbo.fact_hires ADD source_file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_hires', 'file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_hires SET source_file_id = COALESCE(source_file_id, file_id) WHERE source_file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_pipeline_runs', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_pipeline_runs', 'source_file_id') IS NULL
        ALTER TABLE dbo.fact_pipeline_runs ADD source_file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_pipeline_runs', 'error_report_file_id') IS NULL
        ALTER TABLE dbo.fact_pipeline_runs ADD error_report_file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_pipeline_runs', 'communication_id') IS NULL
        ALTER TABLE dbo.fact_pipeline_runs ADD communication_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_pipeline_runs', 'file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_pipeline_runs SET source_file_id = COALESCE(source_file_id, file_id) WHERE source_file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_processed_blobs', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_processed_blobs', 'source_file_id') IS NULL
        ALTER TABLE dbo.fact_processed_blobs ADD source_file_id NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.fact_processed_blobs', 'file_id') IS NOT NULL
        EXEC('UPDATE dbo.fact_processed_blobs SET source_file_id = COALESCE(source_file_id, file_id) WHERE source_file_id IS NULL');
END;
GO

IF OBJECT_ID('dbo.fact_validations', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_validations', 'intern_id') IS NULL
        ALTER TABLE dbo.fact_validations ADD intern_id NVARCHAR(50) NULL;
END;
GO

IF OBJECT_ID('dbo.fact_communications', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_communications', 'email_type') IS NULL ALTER TABLE dbo.fact_communications ADD email_type NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'sent_to') IS NULL ALTER TABLE dbo.fact_communications ADD sent_to NVARCHAR(255) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'status') IS NULL ALTER TABLE dbo.fact_communications ADD status NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'file_id') IS NULL ALTER TABLE dbo.fact_communications ADD file_id NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'email_template_id') IS NULL ALTER TABLE dbo.fact_communications ADD email_template_id NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'communication_type') IS NULL ALTER TABLE dbo.fact_communications ADD communication_type NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'recipient_group') IS NULL ALTER TABLE dbo.fact_communications ADD recipient_group NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'recipient_email') IS NULL ALTER TABLE dbo.fact_communications ADD recipient_email NVARCHAR(255) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'subject') IS NULL ALTER TABLE dbo.fact_communications ADD subject NVARCHAR(255) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'body') IS NULL ALTER TABLE dbo.fact_communications ADD body NVARCHAR(MAX) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'communication_status') IS NULL ALTER TABLE dbo.fact_communications ADD communication_status NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'error_message') IS NULL ALTER TABLE dbo.fact_communications ADD error_message NVARCHAR(MAX) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'sent_at') IS NULL ALTER TABLE dbo.fact_communications ADD sent_at DATETIME2 NULL;
    IF COL_LENGTH('dbo.fact_communications', 'last_attempt_at') IS NULL ALTER TABLE dbo.fact_communications ADD last_attempt_at DATETIME2 NULL;
    IF COL_LENGTH('dbo.fact_communications', 'provider_message_id') IS NULL ALTER TABLE dbo.fact_communications ADD provider_message_id NVARCHAR(255) NULL;
    IF COL_LENGTH('dbo.fact_communications', 'send_attempts') IS NULL ALTER TABLE dbo.fact_communications ADD send_attempts INT NOT NULL DEFAULT 0;

    EXEC('UPDATE dbo.fact_communications SET communication_status = COALESCE(communication_status, status) WHERE communication_status IS NULL');
END;
GO

CREATE OR ALTER VIEW dbo.vw_pipeline_files AS
WITH validation_summary AS (
    SELECT
        file_id,
        COUNT(*) AS validation_count,
        SUM(CASE WHEN validation_result IN ('Failed', 'Needs Review') OR severity IN ('Error', 'Warning') THEN 1 ELSE 0 END) AS validation_issue_count
    FROM dbo.fact_validations
    GROUP BY file_id
)
SELECT
    f.file_id,
    f.original_file_name,
    f.file_extension,
    f.blob_container,
    f.blob_path,
    f.file_status_id AS file_status_name,
    f.validation_status,
    f.error_message,
    f.created_at,
    COALESCE(vs.validation_count, 0) AS validation_count,
    COALESCE(vs.validation_issue_count, 0) AS validation_issue_count
FROM dbo.fact_files f
LEFT JOIN validation_summary vs
    ON f.file_id = vs.file_id;
GO

CREATE OR ALTER VIEW dbo.vw_validation_errors AS
SELECT
    v.validation_id,
    v.file_id,
    v.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    f.original_file_name,
    f.validation_status AS file_validation_status,
    v.validation_rule_id,
    v.field_name,
    v.validation_type,
    v.severity,
    v.validation_result,
    v.error_message,
    v.suggested_fix,
    v.created_at
FROM dbo.fact_validations v
LEFT JOIN dbo.fact_files f
    ON v.file_id = f.file_id
LEFT JOIN dbo.dim_interns i
    ON v.intern_id = i.intern_id
WHERE v.validation_result IN ('Failed', 'Needs Review')
   OR v.severity IN ('Error', 'Warning');
GO

CREATE OR ALTER VIEW dbo.vw_pipeline_summary AS
SELECT
    COUNT(*) AS total_files,
    SUM(CASE WHEN validation_status = 'Validation Passed' THEN 1 ELSE 0 END) AS files_passed,
    SUM(CASE WHEN validation_status IN ('Validation Failed', 'Needs Review') THEN 1 ELSE 0 END) AS files_failed_or_needs_review,
    SUM(CASE WHEN blob_container = 'raw-uploads' THEN 1 ELSE 0 END) AS files_still_in_raw_uploads,
    SUM(CASE WHEN blob_container = 'archive' AND blob_path LIKE 'processed/%' THEN 1 ELSE 0 END) AS files_archived_processed,
    SUM(CASE WHEN blob_container = 'archive' AND blob_path LIKE 'failed/%' THEN 1 ELSE 0 END) AS files_archived_failed,
    SUM(CASE WHEN blob_container = 'error-reports' THEN 1 ELSE 0 END) AS error_reports,
    MAX(created_at) AS latest_file_created_at
FROM dbo.fact_files;
GO

CREATE OR ALTER VIEW dbo.vw_communications_status AS
SELECT
    c.communication_id,
    c.email_type,
    c.sent_to,
    c.communication_type,
    c.recipient_group,
    c.recipient_email,
    c.subject,
    c.status AS communication_status,
    c.communication_status AS detailed_status,
    c.file_id,
    c.created_at,
    c.sent_at,
    c.last_attempt_at,
    c.send_attempts,
    c.error_message,
    CASE
        WHEN c.status = 'Prepared' THEN 'Send or simulate communication'
        WHEN c.status LIKE 'Failed%' THEN 'Review failed communication'
        ELSE 'No action'
    END AS next_action
FROM dbo.fact_communications c;
GO
