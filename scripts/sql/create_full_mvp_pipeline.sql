IF OBJECT_ID('dbo.dim_lifecycle_processes', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_lifecycle_processes (
        process_type_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        process_type_name NVARCHAR(100) NOT NULL,
        description NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.dim_required_document_types', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_required_document_types (
        required_document_type_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        document_code NVARCHAR(100) NOT NULL,
        document_name NVARCHAR(255) NOT NULL,
        description NVARCHAR(MAX) NULL,
        allowed_file_extensions NVARCHAR(255) NULL,
        required_for_coparmex BIT NOT NULL DEFAULT 0,
        required_for_hr BIT NOT NULL DEFAULT 0,
        required_for_applicant BIT NOT NULL DEFAULT 0,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_process_requirements', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_process_requirements (
        requirement_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        process_type_id NVARCHAR(50) NOT NULL,
        required_document_type_id NVARCHAR(50) NOT NULL,
        is_required BIT NOT NULL DEFAULT 1,
        requirement_scope NVARCHAR(100) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_intern_missing_items', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_intern_missing_items (
        missing_item_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        intern_id NVARCHAR(50) NULL,
        process_type_id NVARCHAR(50) NULL,
        missing_type NVARCHAR(50) NOT NULL,
        missing_code NVARCHAR(100) NOT NULL,
        missing_description NVARCHAR(MAX) NOT NULL,
        severity NVARCHAR(50) NOT NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'Open',
        source_file_id NVARCHAR(50) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        resolved_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.fact_intern_lifecycle_events', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_intern_lifecycle_events (
        lifecycle_event_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        run_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        intern_id NVARCHAR(50) NULL,
        process_type_id NVARCHAR(50) NULL,
        event_type NVARCHAR(100) NOT NULL,
        event_status NVARCHAR(100) NOT NULL,
        event_date DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        source_row_number INT NULL,
        old_status NVARCHAR(100) NULL,
        new_status NVARCHAR(100) NULL,
        message NVARCHAR(MAX) NULL,
        needs_review BIT NOT NULL DEFAULT 0,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_intern_document_status', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_intern_document_status (
        intern_document_status_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        intern_id NVARCHAR(50) NULL,
        process_type_id NVARCHAR(50) NULL,
        document_type_id NVARCHAR(50) NOT NULL,
        file_id NVARCHAR(50) NULL,
        status NVARCHAR(50) NOT NULL,
        validation_status NVARCHAR(100) NULL,
        is_required BIT NOT NULL DEFAULT 0,
        is_missing BIT NOT NULL DEFAULT 0,
        is_expired BIT NOT NULL DEFAULT 0,
        expires_at DATETIME2 NULL,
        reviewed_at DATETIME2 NULL,
        notes NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.dim_canonical_fields', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_canonical_fields (
        canonical_field_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        canonical_field_name NVARCHAR(255) NOT NULL,
        field_group NVARCHAR(100) NULL,
        data_type NVARCHAR(50) NULL,
        description NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.dim_column_aliases', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_column_aliases (
        column_alias_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        canonical_field_id NVARCHAR(50) NOT NULL,
        alias_name NVARCHAR(255) NOT NULL,
        normalized_alias_name NVARCHAR(255) NOT NULL,
        source_profile NVARCHAR(255) NULL,
        confidence DECIMAL(5, 4) NOT NULL DEFAULT 1.0,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.dim_file_profiles', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_file_profiles (
        file_profile_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        profile_name NVARCHAR(255) NOT NULL,
        process_type_id NVARCHAR(50) NULL,
        expected_extension NVARCHAR(20) NULL,
        row_processable BIT NOT NULL DEFAULT 0,
        description NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_file_classification', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_file_classification (
        classification_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        run_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        source_container NVARCHAR(255) NOT NULL,
        source_blob_name NVARCHAR(1000) NOT NULL,
        file_name NVARCHAR(1000) NULL,
        file_extension NVARCHAR(20) NULL,
        mime_type NVARCHAR(255) NULL,
        sheet_names NVARCHAR(MAX) NULL,
        detected_column_count INT NULL,
        detected_file_profile_id NVARCHAR(50) NULL,
        detected_document_type_id NVARCHAR(50) NULL,
        detected_process_type_id NVARCHAR(50) NULL,
        classification_confidence DECIMAL(5, 4) NULL,
        classification_reason NVARCHAR(MAX) NULL,
        needs_review BIT NOT NULL DEFAULT 0,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_detected_columns', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_detected_columns (
        detected_column_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        run_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        source_container NVARCHAR(255) NULL,
        source_blob_name NVARCHAR(1000) NULL,
        sheet_name NVARCHAR(255) NULL,
        ordinal_position INT NULL,
        source_column_name NVARCHAR(255) NOT NULL,
        normalized_column_name NVARCHAR(255) NULL,
        canonical_field_id NVARCHAR(50) NULL,
        canonical_field_name NVARCHAR(255) NULL,
        source_profile NVARCHAR(255) NULL,
        mapping_confidence DECIMAL(5, 4) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_pipeline_runs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_pipeline_runs (
        run_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        run_type NVARCHAR(50) NULL,
        source_script NVARCHAR(255) NULL,
        started_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        finished_at DATETIME2 NULL,
        status NVARCHAR(50) NOT NULL,
        source_container NVARCHAR(255) NULL,
        source_blob_name NVARCHAR(1000) NULL,
        archived_blob_name NVARCHAR(1000) NULL,
        source_file_id NVARCHAR(50) NULL,
        error_report_file_id NVARCHAR(50) NULL,
        communication_id NVARCHAR(50) NULL,
        good_rows INT NULL,
        bad_rows INT NULL,
        total_rows INT NULL,
        error_message NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_processed_blobs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_processed_blobs (
        processed_blob_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        source_container NVARCHAR(255) NOT NULL,
        source_blob_name NVARCHAR(1000) NOT NULL,
        source_blob_size_bytes BIGINT NULL,
        source_blob_last_modified DATETIME2 NULL,
        source_blob_etag NVARCHAR(255) NULL,
        source_file_id NVARCHAR(50) NULL,
        run_id NVARCHAR(50) NULL,
        processed_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        archived_blob_name NVARCHAR(1000) NULL,
        status NVARCHAR(50) NOT NULL
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_fact_processed_blobs_source' AND object_id = OBJECT_ID('dbo.fact_processed_blobs'))
BEGIN
    CREATE UNIQUE INDEX UX_fact_processed_blobs_source
    ON dbo.fact_processed_blobs (source_container, source_blob_name);
END;
GO

IF OBJECT_ID('dbo.dim_recipient_groups', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_recipient_groups (
        recipient_group_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        recipient_group_name NVARCHAR(100) NOT NULL,
        description NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.dim_communication_templates', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_communication_templates (
        template_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        template_name NVARCHAR(100) NOT NULL,
        recipient_group_id NVARCHAR(50) NULL,
        subject_template NVARCHAR(255) NULL,
        body_template NVARCHAR(MAX) NULL,
        is_active BIT NOT NULL DEFAULT 1,a
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_communication_packages', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_communication_packages (
        package_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        communication_id NVARCHAR(50) NULL,
        intern_id NVARCHAR(50) NULL,
        process_type_id NVARCHAR(50) NULL,
        recipient_group_id NVARCHAR(50) NOT NULL,
        package_status NVARCHAR(50) NOT NULL DEFAULT 'Prepared',
        summary_text NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        sent_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.fact_communication_package_files', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_communication_package_files (
        package_file_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        package_id NVARCHAR(50) NOT NULL,
        file_id NVARCHAR(50) NULL,
        blob_container NVARCHAR(255) NULL,
        blob_path NVARCHAR(1000) NULL,
        document_code NVARCHAR(100) NULL,
        recipient_group_id NVARCHAR(50) NULL,
        include_reason NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

MERGE dbo.dim_lifecycle_processes AS target
USING (VALUES
    ('PROC_ALTA', 'Alta', 'New intern alta process.'),
    ('PROC_EXTENSION', 'Extendimiento', 'Intern contract/convenio extension process.'),
    ('PROC_BAJA', 'Baja', 'Intern termination or inactive process.'),
    ('PROC_NEW_HIRE', 'Accepted new hire', 'Accepted hires intake and package validation.'),
    ('PROC_CURRENT_SYNC', 'Current intern sync', 'Current intern import/sync and lifecycle validation.'),
    ('PROC_DOCUMENT_REFRESH', 'Document refresh', 'Missing or expired document refresh.'),
    ('PROC_CONTRACT_ALERT', 'Contract alert', 'Upcoming contract/convenio expiration alert.'),
    ('PROC_REQUISITION', 'Requisition', 'Requisition, position, OI/CC/manager/status change.'),
    ('PROC_UNKNOWN', 'Unknown', 'Unknown or needs-review lifecycle process.')
) AS source (process_type_id, process_type_name, description)
ON target.process_type_id = source.process_type_id
WHEN NOT MATCHED THEN
    INSERT (process_type_id, process_type_name, description)
    VALUES (source.process_type_id, source.process_type_name, source.description);
GO

MERGE dbo.dim_required_document_types AS target
USING (VALUES
    ('RDT_CV', 'CV', 'CV', 'pdf,docx,jpg,jpeg,png', 0, 1, 1),
    ('RDT_ID_INE', 'ID_INE', 'ID / INE', 'pdf,jpg,jpeg,png', 0, 1, 1),
    ('RDT_NDA', 'NDA', 'NDA', 'pdf', 0, 1, 1),
    ('RDT_CONVENIO', 'CONVENIO', 'Convenio', 'pdf', 1, 1, 0),
    ('RDT_CERTIFICADO', 'CERTIFICADO', 'Certificado', 'pdf,jpg,jpeg,png', 0, 1, 1),
    ('RDT_ACTA_NACIMIENTO', 'ACTA_NACIMIENTO', 'Acta de nacimiento', 'pdf,jpg,jpeg,png', 0, 1, 1),
    ('RDT_OFFER_LETTER', 'OFFER_LETTER', 'Offer letter', 'pdf', 0, 1, 1),
    ('RDT_SCHOOL_PROOF', 'SCHOOL_PROOF', 'School proof / plan de estudios', 'pdf,jpg,jpeg,png', 1, 1, 1),
    ('RDT_MS_FORMS_RESPONSE', 'MS_FORMS_RESPONSE', 'MS Forms response', 'xlsx,csv,pdf', 0, 1, 0),
    ('RDT_ACCEPTED_HIRES_FILE', 'ACCEPTED_HIRES_FILE', 'Accepted hires file', 'xlsx,csv', 0, 1, 0),
    ('RDT_REQUISITION_FILE', 'REQUISITION_FILE', 'Requisition file', 'xlsx,csv,pdf', 0, 1, 0),
    ('RDT_CURRENT_INTERNS_FILE', 'CURRENT_INTERNS_FILE', 'Current interns file', 'xlsx,csv', 0, 1, 0),
    ('RDT_BAJA_SUPPORT_FILE', 'BAJA_SUPPORT_FILE', 'Baja support file', 'pdf,xlsx,csv,jpg,jpeg,png', 0, 1, 0)
) AS source (required_document_type_id, document_code, document_name, allowed_file_extensions, required_for_coparmex, required_for_hr, required_for_applicant)
ON target.required_document_type_id = source.required_document_type_id
WHEN NOT MATCHED THEN
    INSERT (required_document_type_id, document_code, document_name, allowed_file_extensions, required_for_coparmex, required_for_hr, required_for_applicant)
    VALUES (source.required_document_type_id, source.document_code, source.document_name, source.allowed_file_extensions, source.required_for_coparmex, source.required_for_hr, source.required_for_applicant);
GO

MERGE dbo.fact_process_requirements AS target
USING (VALUES
    ('REQ-NEW-HIRE-CV', 'PROC_NEW_HIRE', 'RDT_CV', 1, 'Applicant'),
    ('REQ-NEW-HIRE-ID', 'PROC_NEW_HIRE', 'RDT_ID_INE', 1, 'Applicant'),
    ('REQ-NEW-HIRE-NDA', 'PROC_NEW_HIRE', 'RDT_NDA', 1, 'Applicant'),
    ('REQ-NEW-HIRE-SCHOOL', 'PROC_NEW_HIRE', 'RDT_SCHOOL_PROOF', 1, 'Applicant'),
    ('REQ-NEW-HIRE-FILE', 'PROC_NEW_HIRE', 'RDT_ACCEPTED_HIRES_FILE', 1, 'Process'),
    ('REQ-ALTA-REQ', 'PROC_ALTA', 'RDT_REQUISITION_FILE', 1, 'Process'),
    ('REQ-ALTA-HIRES', 'PROC_ALTA', 'RDT_ACCEPTED_HIRES_FILE', 1, 'Process'),
    ('REQ-ALTA-ID', 'PROC_ALTA', 'RDT_ID_INE', 1, 'Applicant'),
    ('REQ-ALTA-SCHOOL', 'PROC_ALTA', 'RDT_SCHOOL_PROOF', 1, 'Applicant'),
    ('REQ-EXT-CONVENIO', 'PROC_EXTENSION', 'RDT_CONVENIO', 1, 'Intern'),
    ('REQ-EXT-SUPPORT', 'PROC_EXTENSION', 'RDT_REQUISITION_FILE', 1, 'Process'),
    ('REQ-BAJA-SUPPORT', 'PROC_BAJA', 'RDT_BAJA_SUPPORT_FILE', 0, 'Process'),
    ('REQ-CURRENT-FILE', 'PROC_CURRENT_SYNC', 'RDT_CURRENT_INTERNS_FILE', 1, 'Process'),
    ('REQ-DOC-REFRESH-CONVENIO', 'PROC_DOCUMENT_REFRESH', 'RDT_CONVENIO', 1, 'Intern')
) AS source (requirement_id, process_type_id, required_document_type_id, is_required, requirement_scope)
ON target.requirement_id = source.requirement_id
WHEN NOT MATCHED THEN
    INSERT (requirement_id, process_type_id, required_document_type_id, is_required, requirement_scope)
    VALUES (source.requirement_id, source.process_type_id, source.required_document_type_id, source.is_required, source.requirement_scope);
GO

MERGE dbo.dim_recipient_groups AS target
USING (VALUES
    ('APPLICANT', 'Applicant / current intern', 'Correction and confirmation messages.'),
    ('HR', 'HR', 'Internal HR package and summary.'),
    ('COPARMEX', 'Coparmex', 'External package with required files only.'),
    ('REVIEWER', 'Reviewer', 'Manual review queue.')
) AS source (recipient_group_id, recipient_group_name, description)
ON target.recipient_group_id = source.recipient_group_id
WHEN NOT MATCHED THEN
    INSERT (recipient_group_id, recipient_group_name, description)
    VALUES (source.recipient_group_id, source.recipient_group_name, source.description);
GO

MERGE dbo.dim_communication_templates AS target
USING (VALUES
    ('TPL_CORRECTION', 'Correction request', 'APPLICANT'),
    ('TPL_APPLICANT_CONFIRMATION', 'Applicant confirmation', 'APPLICANT'),
    ('TPL_HR_PACKAGE', 'HR complete package', 'HR'),
    ('TPL_COPARMEX_PACKAGE', 'Coparmex package', 'COPARMEX')
) AS source (template_id, template_name, recipient_group_id)
ON target.template_id = source.template_id
WHEN NOT MATCHED THEN
    INSERT (template_id, template_name, recipient_group_id)
    VALUES (source.template_id, source.template_name, source.recipient_group_id);
GO

MERGE dbo.dim_canonical_fields AS target
USING (VALUES
    ('intern_id'), ('employee_number'), ('cemex_employee_number'), ('email'), ('full_name'), ('first_name'),
    ('paternal_last_name'), ('maternal_last_name'), ('curp'), ('rfc'), ('nss'), ('university'), ('career'),
    ('semester'), ('area'), ('position'), ('start_date'), ('end_date'), ('status'), ('oi_hc'), ('cc_hc'),
    ('vp_hc'), ('region_rh'), ('manager'), ('company'), ('salary'), ('gender'), ('age')
) AS source (canonical_field_id)
ON target.canonical_field_id = source.canonical_field_id
WHEN NOT MATCHED THEN
    INSERT (canonical_field_id, canonical_field_name)
    VALUES (source.canonical_field_id, source.canonical_field_id);
GO

MERGE dbo.dim_file_profiles AS target
USING (VALUES
    ('requisition_excel', 'Requisition Excel', 'PROC_REQUISITION', 'xlsx', 1),
    ('accepted_hires_excel', 'Accepted hires Excel', 'PROC_NEW_HIRE', 'xlsx', 1),
    ('accepted_hires_csv', 'Accepted hires CSV', 'PROC_NEW_HIRE', 'csv', 1),
    ('current_interns_excel', 'Current interns Excel', 'PROC_CURRENT_SYNC', 'xlsx', 1),
    ('current_interns_csv', 'Current interns CSV', 'PROC_CURRENT_SYNC', 'csv', 1),
    ('generic_excel', 'Generic Excel', 'PROC_DOCUMENT_REFRESH', 'xlsx', 1),
    ('generic_csv', 'Generic CSV', 'PROC_DOCUMENT_REFRESH', 'csv', 1),
    ('generic_pdf', 'Generic PDF', 'PROC_DOCUMENT_REFRESH', 'pdf', 0),
    ('generic_image', 'Generic image', 'PROC_DOCUMENT_REFRESH', 'png/jpg/jpeg', 0),
    ('unknown_file', 'Unknown file', 'PROC_UNKNOWN', NULL, 0)
) AS source (file_profile_id, profile_name, process_type_id, expected_extension, row_processable)
ON target.file_profile_id = source.file_profile_id
WHEN NOT MATCHED THEN
    INSERT (file_profile_id, profile_name, process_type_id, expected_extension, row_processable)
    VALUES (source.file_profile_id, source.profile_name, source.process_type_id, source.expected_extension, source.row_processable);
GO

MERGE dbo.dim_column_aliases AS target
USING (VALUES
    ('alias_full_name_nombrecompleto', 'full_name', 'NombreCompleto', 'nombrecompleto'),
    ('alias_full_name_nombre_completo', 'full_name', 'Nombre Completo', 'nombre completo'),
    ('alias_full_name_full_name', 'full_name', 'Full Name', 'full name'),
    ('alias_full_name_name', 'full_name', 'Name', 'name'),
    ('alias_email_email', 'email', 'Email', 'email'),
    ('alias_email_correo', 'email', 'Correo', 'correo'),
    ('alias_email_correo_practicante', 'email', 'Correo Practicante', 'correo practicante'),
    ('alias_email_e_mail', 'email', 'E-mail', 'e mail'),
    ('alias_oi_hc', 'oi_hc', 'OI HC', 'oi hc'),
    ('alias_oi', 'oi_hc', 'OI', 'oi'),
    ('alias_orden_interna', 'oi_hc', 'Orden Interna', 'orden interna'),
    ('alias_internal_order', 'oi_hc', 'Internal Order', 'internal order'),
    ('alias_cc_hc', 'cc_hc', 'CC HC', 'cc hc'),
    ('alias_cc', 'cc_hc', 'CC', 'cc'),
    ('alias_centro_costo', 'cc_hc', 'Centro de Costo', 'centro de costo'),
    ('alias_cost_center', 'cc_hc', 'Cost Center', 'cost center'),
    ('alias_fecha_ingreso_compact', 'start_date', 'FechadeIngreso', 'fechadeingreso'),
    ('alias_fecha_ingreso', 'start_date', 'Fecha de Ingreso', 'fecha de ingreso'),
    ('alias_start_date', 'start_date', 'Start Date', 'start date'),
    ('alias_fecha_inicio', 'start_date', 'Fecha Inicio', 'fecha inicio'),
    ('alias_fecha_contrato_vence', 'end_date', 'FechaContratoVence', 'fechacontratovence'),
    ('alias_fecha_fin', 'end_date', 'Fecha Fin', 'fecha fin'),
    ('alias_end_date', 'end_date', 'End Date', 'end date'),
    ('alias_vencimiento', 'end_date', 'Vencimiento', 'vencimiento'),
    ('alias_vp_hc', 'vp_hc', 'VP HC', 'vp hc'),
    ('alias_vp', 'vp_hc', 'VP', 'vp'),
    ('alias_vicepresidencia', 'vp_hc', 'Vicepresidencia', 'vicepresidencia'),
    ('alias_jefeinmediato', 'manager', 'JefeInmediato', 'jefeinmediato'),
    ('alias_jefe_inmediato', 'manager', 'Jefe Inmediato', 'jefe inmediato'),
    ('alias_manager', 'manager', 'Manager', 'manager'),
    ('alias_supervisor', 'manager', 'Supervisor', 'supervisor'),
    ('alias_jefe', 'manager', 'Jefe', 'jefe'),
    ('alias_universidad', 'university', 'Universidad', 'universidad'),
    ('alias_university', 'university', 'University', 'university'),
    ('alias_carrera', 'career', 'Carrera', 'carrera'),
    ('alias_career', 'career', 'Career', 'career'),
    ('alias_major', 'career', 'Major', 'major'),
    ('alias_estatus', 'status', 'Estatus', 'estatus'),
    ('alias_status', 'status', 'Status', 'status')
) AS source (column_alias_id, canonical_field_id, alias_name, normalized_alias_name)
ON target.column_alias_id = source.column_alias_id
WHEN NOT MATCHED THEN
    INSERT (column_alias_id, canonical_field_id, alias_name, normalized_alias_name, source_profile, confidence)
    VALUES (source.column_alias_id, source.canonical_field_id, source.alias_name, source.normalized_alias_name, 'default', 1.0);
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_pipeline_runs AS
SELECT
    pr.*
FROM dbo.fact_pipeline_runs pr;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_pipeline_summary AS
SELECT
    pr.run_id,
    pr.run_type,
    pr.status AS run_status,
    pr.started_at,
    pr.finished_at,
    pr.source_container,
    pr.source_blob_name,
    pr.archived_blob_name,
    pr.good_rows,
    pr.bad_rows,
    pr.total_rows,
    fc.detected_file_profile_id,
    fc.detected_process_type_id,
    fc.classification_confidence,
    fc.needs_review,
    pr.error_message
FROM dbo.fact_pipeline_runs pr
LEFT JOIN dbo.fact_file_classification fc
    ON pr.run_id = fc.run_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_file_classification AS
SELECT
    fc.*,
    fp.profile_name,
    lp.process_type_name
FROM dbo.fact_file_classification fc
LEFT JOIN dbo.dim_file_profiles fp
    ON fc.detected_file_profile_id = fp.file_profile_id
LEFT JOIN dbo.dim_lifecycle_processes lp
    ON fc.detected_process_type_id = lp.process_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_detected_columns AS
SELECT
    dc.*
FROM dbo.fact_detected_columns dc;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_missing_items AS
SELECT
    mi.*,
    lp.process_type_name
FROM dbo.fact_intern_missing_items mi
LEFT JOIN dbo.dim_lifecycle_processes lp
    ON mi.process_type_id = lp.process_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_lifecycle_events AS
SELECT
    le.*,
    i.nombre_completo,
    i.status_id,
    lp.process_type_name
FROM dbo.fact_intern_lifecycle_events le
LEFT JOIN dbo.dim_interns i
    ON le.intern_id = i.intern_id
LEFT JOIN dbo.dim_lifecycle_processes lp
    ON le.process_type_id = lp.process_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_document_status AS
SELECT
    ids.*,
    rdt.document_code,
    rdt.document_name,
    f.original_file_name,
    f.blob_container,
    f.blob_path
FROM dbo.fact_intern_document_status ids
LEFT JOIN dbo.dim_required_document_types rdt
    ON ids.document_type_id = rdt.required_document_type_id
    OR ids.document_type_id = rdt.document_code
LEFT JOIN dbo.fact_files f
    ON ids.file_id = f.file_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_communication_packages AS
SELECT
    cp.*,
    rg.recipient_group_name,
    c.subject,
    c.status AS communication_status
FROM dbo.fact_communication_packages cp
LEFT JOIN dbo.dim_recipient_groups rg
    ON cp.recipient_group_id = rg.recipient_group_id
LEFT JOIN dbo.fact_communications c
    ON cp.communication_id = c.communication_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_package_files AS
SELECT
    cpf.*,
    cp.communication_id,
    cp.process_type_id,
    f.original_file_name
FROM dbo.fact_communication_package_files cpf
LEFT JOIN dbo.fact_communication_packages cp
    ON cpf.package_id = cp.package_id
LEFT JOIN dbo.fact_files f
    ON cpf.file_id = f.file_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_interns_current AS
SELECT
    i.intern_id,
    i.num_empleado,
    i.num_empleado_cemex,
    i.nombre_completo,
    i.universidad,
    i.carrera,
    i.puesto,
    i.jefe_inmediato,
    i.cc_hc,
    i.oi_hc,
    i.vp_hc,
    i.cia_hc,
    i.area,
    i.status_id,
    i.fecha_de_ingreso,
    i.fecha_contrato_vence,
    CASE
        WHEN i.fecha_contrato_vence IS NOT NULL
         AND i.fecha_contrato_vence >= CAST(SYSUTCDATETIME() AS DATE)
         AND i.fecha_contrato_vence <= DATEADD(DAY, 30, CAST(SYSUTCDATETIME() AS DATE))
        THEN 1 ELSE 0
    END AS is_upcoming_expiration
FROM dbo.dim_interns i;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_validation_errors AS
SELECT
    v.*,
    f.original_file_name,
    f.blob_container,
    f.blob_path
FROM dbo.fact_validations v
LEFT JOIN dbo.fact_files f
    ON v.file_id = f.file_id
WHERE v.validation_result IN ('Failed', 'Needs Review')
   OR v.severity IN ('Error', 'Warning');
GO
