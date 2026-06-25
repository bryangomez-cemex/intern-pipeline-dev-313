IF OBJECT_ID('dbo.dim_requisitions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_requisitions (
        requisition_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        requisition_type NVARCHAR(100) NULL,
        requisition_status NVARCHAR(100) NULL,
        requested_by NVARCHAR(255) NULL,
        vp_hc NVARCHAR(255) NULL,
        area NVARCHAR(255) NULL,
        manager NVARCHAR(255) NULL,
        oi_hc NVARCHAR(255) NULL,
        cc_hc NVARCHAR(255) NULL,
        company NVARCHAR(255) NULL,
        requested_start_date DATE NULL,
        requested_end_date DATE NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO

IF COL_LENGTH('dbo.dim_requisitions', 'requisition_type') IS NULL ALTER TABLE dbo.dim_requisitions ADD requisition_type NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'process_type_id') IS NULL ALTER TABLE dbo.dim_requisitions ADD process_type_id NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'requisition_status') IS NULL ALTER TABLE dbo.dim_requisitions ADD requisition_status NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'requested_by') IS NULL ALTER TABLE dbo.dim_requisitions ADD requested_by NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'vp') IS NULL ALTER TABLE dbo.dim_requisitions ADD vp NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'vp_hc') IS NULL ALTER TABLE dbo.dim_requisitions ADD vp_hc NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'area') IS NULL ALTER TABLE dbo.dim_requisitions ADD area NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'manager_name') IS NULL ALTER TABLE dbo.dim_requisitions ADD manager_name NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'manager') IS NULL ALTER TABLE dbo.dim_requisitions ADD manager NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'oi_hc') IS NULL ALTER TABLE dbo.dim_requisitions ADD oi_hc NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'cc_hc') IS NULL ALTER TABLE dbo.dim_requisitions ADD cc_hc NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'company') IS NULL ALTER TABLE dbo.dim_requisitions ADD company NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'puesto') IS NULL ALTER TABLE dbo.dim_requisitions ADD puesto NVARCHAR(300) NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'requested_start_date') IS NULL ALTER TABLE dbo.dim_requisitions ADD requested_start_date DATE NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'requested_end_date') IS NULL ALTER TABLE dbo.dim_requisitions ADD requested_end_date DATE NULL;
IF COL_LENGTH('dbo.dim_requisitions', 'created_at') IS NULL ALTER TABLE dbo.dim_requisitions ADD created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME();
IF COL_LENGTH('dbo.dim_requisitions', 'updated_at') IS NULL ALTER TABLE dbo.dim_requisitions ADD updated_at DATETIME2 NULL;
GO

IF OBJECT_ID('dbo.fact_hires', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_hires (
        hire_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        intern_id NVARCHAR(50) NULL,
        source_file_id NVARCHAR(50) NULL,
        process_type_id NVARCHAR(50) NULL,
        source_row_number INT NULL,
        hire_status NVARCHAR(100) NULL,
        onboarding_status NVARCHAR(100) NULL,
        accepted_at DATETIME2 NULL,
        start_date DATE NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF COL_LENGTH('dbo.fact_hires', 'intern_id') IS NULL ALTER TABLE dbo.fact_hires ADD intern_id NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.fact_hires', 'source_file_id') IS NULL ALTER TABLE dbo.fact_hires ADD source_file_id NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.fact_hires', 'process_type_id') IS NULL ALTER TABLE dbo.fact_hires ADD process_type_id NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.fact_hires', 'source_row_number') IS NULL ALTER TABLE dbo.fact_hires ADD source_row_number INT NULL;
IF COL_LENGTH('dbo.fact_hires', 'hire_status') IS NULL ALTER TABLE dbo.fact_hires ADD hire_status NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.fact_hires', 'onboarding_status') IS NULL ALTER TABLE dbo.fact_hires ADD onboarding_status NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.fact_hires', 'accepted_at') IS NULL ALTER TABLE dbo.fact_hires ADD accepted_at DATETIME2 NULL;
IF COL_LENGTH('dbo.fact_hires', 'start_date') IS NULL ALTER TABLE dbo.fact_hires ADD start_date DATE NULL;
IF COL_LENGTH('dbo.fact_hires', 'created_at') IS NULL ALTER TABLE dbo.fact_hires ADD created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME();
GO

INSERT INTO dbo.fact_hires (
    hire_id,
    intern_id,
    source_file_id,
    process_type_id,
    source_row_number,
    hire_status,
    onboarding_status,
    accepted_at,
    start_date,
    created_at
)
SELECT
    CONCAT('HIRE-BF-', LEFT(CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', i.intern_id), 2), 16)) AS hire_id,
    i.intern_id,
    NULL AS source_file_id,
    'PROC_NEW_HIRE' AS process_type_id,
    NULL AS source_row_number,
    'Accepted' AS hire_status,
    'Pending Documents' AS onboarding_status,
    SYSUTCDATETIME() AS accepted_at,
    i.fecha_de_ingreso AS start_date,
    SYSUTCDATETIME() AS created_at
FROM dbo.dim_interns i
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.fact_hires h
    WHERE h.intern_id = i.intern_id
);
GO

INSERT INTO dbo.fact_intern_missing_items (
    missing_item_id,
    intern_id,
    process_type_id,
    missing_type,
    missing_code,
    missing_description,
    severity,
    status,
    source_file_id
)
SELECT
    CONCAT(
        'MISS-BF-',
        LEFT(CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(i.intern_id, ':', rdt.document_code)), 2), 10),
        '-',
        LEFT(CONVERT(NVARCHAR(36), NEWID()), 4)
    ) AS missing_item_id,
    i.intern_id,
    pr.process_type_id,
    'Document' AS missing_type,
    rdt.document_code AS missing_code,
    CONCAT('Missing required document: ', rdt.document_name, '.') AS missing_description,
    'Error' AS severity,
    'Open' AS status,
    NULL AS source_file_id
FROM dbo.dim_interns i
INNER JOIN dbo.fact_process_requirements pr
    ON pr.process_type_id = 'PROC_NEW_HIRE'
   AND pr.is_required = 1
INNER JOIN dbo.dim_required_document_types rdt
    ON pr.required_document_type_id = rdt.required_document_type_id
WHERE pr.requirement_scope = 'Applicant'
  -- Only backfill missing applicant documents for real new-hire loads that have
  -- source-file provenance. The current-interns master DB is historical and
  -- should not be treated as an onboarding packet with every document missing.
  AND EXISTS (
      SELECT 1
      FROM dbo.fact_hires h
      WHERE h.intern_id = i.intern_id
        AND h.process_type_id = 'PROC_NEW_HIRE'
        AND h.source_file_id IS NOT NULL
  )
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.fact_intern_document_status ids
      WHERE ids.intern_id = i.intern_id
        AND (
            ids.document_type_id = rdt.required_document_type_id
            OR ids.document_type_id = rdt.document_code
        )
        AND ids.status IN ('Stored', 'Validated', 'Received')
  )
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.fact_intern_missing_items mi
      WHERE mi.intern_id = i.intern_id
        AND mi.process_type_id = pr.process_type_id
        AND mi.missing_code = rdt.document_code
        AND mi.status = 'Open'
  );
GO

CREATE OR ALTER VIEW dbo.vw_interns_current AS
WITH missing AS (
    SELECT intern_id, COUNT(*) AS missing_document_count
    FROM dbo.fact_intern_missing_items
    WHERE status = 'Open'
      AND missing_type = 'Document'
    GROUP BY intern_id
),
issues AS (
    SELECT intern_id, COUNT(*) AS validation_issue_count
    FROM dbo.fact_validations
    WHERE intern_id IS NOT NULL
      AND (
          validation_result IN ('Failed', 'Needs Review')
          OR severity IN ('Error', 'Warning')
      )
    GROUP BY intern_id
)
SELECT
    i.intern_id,
    i.num_empleado AS employee_number,
    i.num_empleado_cemex AS cemex_employee_number,
    i.nombre_completo AS intern_name,
    i.universidad AS university,
    i.carrera AS career,
    i.semestre AS semester,
    i.puesto AS position,
    i.jefe_inmediato AS manager,
    i.area,
    i.vp_hc AS vp,
    i.region_rh AS hr_region,
    i.oi_hc,
    i.cc_hc,
    i.cia_hc AS company,
    i.salario_mensual AS monthly_salary,
    i.fecha_de_ingreso AS start_date,
    i.fecha_contrato_vence AS contract_end_date,
    i.status_id AS intern_status,
    DATEDIFF(DAY, CAST(SYSUTCDATETIME() AS DATE), i.fecha_contrato_vence) AS days_until_contract_end,
    CASE
        WHEN i.fecha_contrato_vence IS NOT NULL
         AND i.fecha_contrato_vence >= CAST(SYSUTCDATETIME() AS DATE)
         AND i.fecha_contrato_vence <= DATEADD(DAY, 30, CAST(SYSUTCDATETIME() AS DATE))
        THEN 1 ELSE 0
    END AS is_expiring_soon,
    COALESCE(missing.missing_document_count, 0) AS missing_document_count,
    COALESCE(issues.validation_issue_count, 0) AS validation_issue_count,
    CASE
        WHEN COALESCE(missing.missing_document_count, 0) > 0 THEN 'Request missing documents'
        WHEN COALESCE(issues.validation_issue_count, 0) > 0 THEN 'Review business exceptions'
        WHEN i.fecha_contrato_vence IS NOT NULL
         AND i.fecha_contrato_vence <= DATEADD(DAY, 30, CAST(SYSUTCDATETIME() AS DATE)) THEN 'Review extension or baja'
        ELSE 'Monitor'
    END AS next_action
FROM dbo.dim_interns i
LEFT JOIN missing
    ON i.intern_id = missing.intern_id
LEFT JOIN issues
    ON i.intern_id = issues.intern_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_interns_current AS
SELECT *
FROM dbo.vw_interns_current;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_document_status AS
SELECT
    ids.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    COALESCE(rdt.document_code, ids.document_type_id) AS document_code,
    COALESCE(rdt.document_name, ids.document_type_id) AS document_name,
    ids.status AS document_status,
    ids.validation_status,
    ids.is_required,
    ids.is_missing,
    ids.is_expired,
    ids.expires_at,
    ids.reviewed_at,
    CASE
        WHEN ids.is_missing = 1 THEN 'Request document'
        WHEN ids.is_expired = 1 THEN 'Request refreshed document'
        WHEN ids.validation_status IN ('Needs Review', 'Validation Failed') THEN 'Review document'
        ELSE 'No action'
    END AS next_action
FROM dbo.fact_intern_document_status ids
LEFT JOIN dbo.dim_interns i
    ON ids.intern_id = i.intern_id
LEFT JOIN dbo.dim_required_document_types rdt
    ON ids.document_type_id = rdt.required_document_type_id
    OR ids.document_type_id = rdt.document_code;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_missing_items AS
SELECT
    mi.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    i.cia_hc AS company,
    lp.process_type_name AS process_type,
    mi.missing_type,
    mi.missing_code,
    mi.missing_description,
    mi.severity,
    mi.status,
    mi.created_at,
    mi.resolved_at,
    CASE
        WHEN mi.status = 'Open' AND mi.missing_type = 'Document' THEN 'Request missing document'
        WHEN mi.status = 'Open' THEN 'Resolve missing item'
        ELSE 'No action'
    END AS next_action
FROM dbo.fact_intern_missing_items mi
LEFT JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
LEFT JOIN dbo.dim_lifecycle_processes lp
    ON mi.process_type_id = lp.process_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_full_mvp_lifecycle_events AS
SELECT
    le.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    lp.process_type_name AS process_type,
    le.event_type,
    le.event_status,
    le.event_date,
    le.old_status,
    le.new_status,
    le.message,
    le.needs_review,
    CASE
        WHEN le.needs_review = 1 THEN 'Review lifecycle event'
        WHEN le.event_type IN ('upcoming_expiration', 'contract_alert') THEN 'Review extension or baja'
        ELSE 'No action'
    END AS next_action
FROM dbo.fact_intern_lifecycle_events le
LEFT JOIN dbo.dim_interns i
    ON le.intern_id = i.intern_id
LEFT JOIN dbo.dim_lifecycle_processes lp
    ON le.process_type_id = lp.process_type_id;
GO

CREATE OR ALTER VIEW dbo.vw_business_validation_exceptions AS
SELECT
    v.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    i.cia_hc AS company,
    v.field_name AS issue_field,
    v.validation_type AS issue_type,
    v.severity,
    v.validation_result AS issue_status,
    v.error_message AS issue_description,
    v.suggested_fix,
    v.created_at,
    'Validation' AS exception_source,
    CASE
        WHEN v.validation_result IN ('Failed', 'Needs Review') THEN 'Review and correct data'
        ELSE 'Monitor'
    END AS next_action
FROM dbo.fact_validations v
LEFT JOIN dbo.dim_interns i
    ON v.intern_id = i.intern_id
WHERE v.intern_id IS NOT NULL
  AND (
      v.validation_result IN ('Failed', 'Needs Review')
      OR v.severity IN ('Error', 'Warning')
  )
UNION ALL
SELECT
    mi.intern_id,
    i.nombre_completo AS intern_name,
    i.num_empleado AS employee_number,
    i.vp_hc AS vp,
    i.area,
    i.jefe_inmediato AS manager,
    i.oi_hc,
    i.cc_hc,
    i.cia_hc AS company,
    mi.missing_code AS issue_field,
    mi.missing_type AS issue_type,
    mi.severity,
    mi.status AS issue_status,
    mi.missing_description AS issue_description,
    'Provide or correct the missing item.' AS suggested_fix,
    mi.created_at,
    'Missing Item' AS exception_source,
    CASE
        WHEN mi.status = 'Open' AND mi.missing_type = 'Document' THEN 'Request missing document'
        WHEN mi.status = 'Open' THEN 'Resolve missing item'
        ELSE 'Monitor'
    END AS next_action
FROM dbo.fact_intern_missing_items mi
LEFT JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open';
GO

CREATE OR ALTER VIEW dbo.vw_requisitions_status AS
SELECT
    r.requisition_id,
    r.requisition_type,
    r.requisition_status,
    r.requested_by,
    r.vp_hc AS vp,
    r.area,
    r.manager,
    r.oi_hc,
    r.cc_hc,
    r.company,
    r.requested_start_date,
    r.requested_end_date,
    r.created_at,
    CASE
        WHEN r.requisition_status IS NULL OR r.requisition_status IN ('Pending', 'Needs Review') THEN 'Review requisition'
        WHEN r.requisition_status IN ('Approved') THEN 'Proceed with hire/package'
        ELSE 'Monitor'
    END AS next_action
FROM dbo.dim_requisitions r;
GO

CREATE OR ALTER VIEW dbo.vw_communications_status AS
SELECT
    c.communication_id,
    c.communication_type,
    c.recipient_group,
    c.subject,
    c.status AS communication_status,
    c.communication_status AS detailed_status,
    c.created_at,
    c.sent_at,
    c.last_attempt_at,
    c.send_attempts,
    CASE
        WHEN c.status = 'Prepared' THEN 'Send or simulate communication'
        WHEN c.status LIKE 'Failed%' THEN 'Review failed communication'
        ELSE 'No action'
    END AS next_action
FROM dbo.fact_communications c;
GO

CREATE OR ALTER VIEW dbo.vw_hr_actions_today AS
SELECT
    'Missing Item' AS action_category,
    intern_id,
    intern_name,
    vp,
    area,
    manager,
    missing_description AS action_description,
    severity,
    created_at AS action_created_at,
    next_action
FROM dbo.vw_full_mvp_missing_items
WHERE status = 'Open'
UNION ALL
SELECT
    'Business Exception' AS action_category,
    intern_id,
    intern_name,
    vp,
    area,
    manager,
    issue_description AS action_description,
    severity,
    created_at AS action_created_at,
    next_action
FROM dbo.vw_business_validation_exceptions
UNION ALL
SELECT
    'Contract Expiration' AS action_category,
    intern_id,
    intern_name,
    vp,
    area,
    manager,
    CONCAT('Contract/convenio ends in ', days_until_contract_end, ' days.') AS action_description,
    'Warning' AS severity,
    SYSUTCDATETIME() AS action_created_at,
    next_action
FROM dbo.vw_interns_current
WHERE is_expiring_soon = 1
UNION ALL
SELECT
    'Communication' AS action_category,
    NULL AS intern_id,
    NULL AS intern_name,
    NULL AS vp,
    NULL AS area,
    NULL AS manager,
    subject AS action_description,
    'Info' AS severity,
    created_at AS action_created_at,
    next_action
FROM dbo.vw_communications_status
WHERE next_action <> 'No action';
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_vacantes AS
SELECT
    r.requisition_id,
    COALESCE(r.puesto, r.requisition_type, 'Vacante sin puesto') AS position_name,
    COALESCE(r.vp_hc, r.vp) AS vp,
    r.area,
    COALESCE(r.manager, r.manager_name) AS manager,
    r.oi_hc,
    r.cc_hc,
    r.company AS cia_hc,
    r.requisition_status,
    r.requested_start_date,
    r.requested_end_date,
    r.created_at,
    DATEDIFF(DAY, CAST(r.created_at AS DATE), CAST(SYSUTCDATETIME() AS DATE)) AS days_open,
    'Asignar practicante' AS next_action
FROM dbo.dim_requisitions r
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.dim_interns i
    WHERE i.requisition_id = r.requisition_id
)
AND COALESCE(r.requisition_status, 'Open') NOT IN (
    'Closed', 'Cerrada', 'Cancelada', 'Cancelled', 'Filled', 'Cubierta'
);
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_interns_status AS
WITH latest_lifecycle AS (
    SELECT
        le.intern_id,
        le.new_status,
        le.event_date,
        ROW_NUMBER() OVER (
            PARTITION BY le.intern_id
            ORDER BY le.event_date DESC, le.created_at DESC
        ) AS rn
    FROM dbo.fact_intern_lifecycle_events le
    WHERE le.new_status IS NOT NULL
),
base AS (
    SELECT
        i.intern_id,
        i.num_empleado AS employee_number,
        i.num_empleado_cemex AS cemex_employee_number,
        i.nombre_completo AS intern_name,
        i.puesto AS position_name,
        i.jefe_inmediato AS manager,
        i.vp_hc AS vp,
        i.ubicacion_hc,
        i.estado_ubicacion_hc,
        i.cia_hc,
        i.oi_hc,
        i.cc_hc,
        i.fecha_de_ingreso AS start_date,
        i.fecha_contrato_vence AS contract_end_date,
        i.salario_mensual,
        COALESCE(ll.new_status, i.status_id) AS raw_status,
        ll.event_date AS latest_status_event_date
    FROM dbo.dim_interns i
    LEFT JOIN latest_lifecycle ll
        ON i.intern_id = ll.intern_id
       AND ll.rn = 1
)
SELECT
    *,
    LOWER(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(COALESCE(raw_status, ''))),
            'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')
    ) AS normalized_status,
    CASE
        WHEN LOWER(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(COALESCE(raw_status, ''))),
                'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')
        ) IN ('activo', 'active', 'st002') THEN 1
        ELSE 0
    END AS is_active,
    CASE
        WHEN LOWER(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(COALESCE(raw_status, ''))),
                'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')
        ) IN ('baja', 'inactivo', 'inactive') THEN 1
        ELSE 0
    END AS is_inactive,
    CASE
        WHEN contract_end_date IS NOT NULL
         AND contract_end_date < CAST(SYSUTCDATETIME() AS DATE) THEN 1
        ELSE 0
    END AS is_contract_expired,
    DATEDIFF(DAY, CAST(SYSUTCDATETIME() AS DATE), contract_end_date) AS days_until_contract_end,
    TRY_CONVERT(DECIMAL(18,2),
        REPLACE(REPLACE(REPLACE(CAST(salario_mensual AS NVARCHAR(100)), '$', ''), ',', ''), ' ', '')
    ) AS importe_total
FROM base;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_costos_practicantes AS
SELECT
    vp,
    ubicacion_hc,
    estado_ubicacion_hc,
    cia_hc,
    COUNT(*) AS practicante_count,
    SUM(COALESCE(importe_total, 0)) AS importe_total_sum,
    AVG(COALESCE(importe_total, 0)) AS importe_total_avg,
    MIN(importe_total) AS importe_total_min,
    MAX(importe_total) AS importe_total_max
FROM dbo.vw_powerbi_interns_status
WHERE is_active = 1
GROUP BY vp, ubicacion_hc, estado_ubicacion_hc, cia_hc;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_expired_active_contracts AS
SELECT
    intern_id,
    employee_number,
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
    days_until_contract_end,
    raw_status,
    'Contrato vencido y sigue activo' AS alert_label
FROM dbo.vw_powerbi_interns_status
WHERE is_active = 1
  AND is_contract_expired = 1;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_inactive_interns AS
SELECT
    intern_id,
    employee_number,
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
    latest_status_event_date
FROM dbo.vw_powerbi_interns_status
WHERE is_inactive = 1;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_vp_capacity AS
WITH vp_capacity AS (
    SELECT
        vp,
        allowed_practicantes,
        UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(vp,
            'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')) AS vp_key
    FROM (VALUES
        ('CONCRETO Y CONSTRUCCION', 130),
        ('CADENA DE SUMINISTRO', 127),
        ('OPERACIONES-TECNICA', 86),
        ('SEGMENTO DISTRIBUCION', 51),
        ('GLOBAL ENTERPRISE SERVICES', 50),
        ('RECURSOS HUMANOS', 25),
        ('SEGMENTO INDUSTRIAL', 23),
        ('SEGURIDAD INDUSTRIAL Y BIENESTAR', 16),
        ('ASUNTOS CORPORATIVOS, SOSTENIBILIDAD Y COMUNICACIÓN', 13),
        ('LEGAL', 6),
        ('PLANEACION', 3),
        ('SUPPLY CHAIN', 2),
        ('CEMENT OPERATIONS', 1),
        ('PLANNING', 1),
        ('PRESIDENCIA MEXICO', 1)
    ) AS v(vp, allowed_practicantes)
),
active_counts AS (
    SELECT
        UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(vp,
            'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')) AS vp_key,
        COUNT(*) AS current_practicantes
    FROM dbo.vw_powerbi_interns_status
    WHERE is_active = 1
    GROUP BY UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(vp,
        'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U'))
)
SELECT
    c.vp,
    c.allowed_practicantes,
    COALESCE(a.current_practicantes, 0) AS current_practicantes,
    c.allowed_practicantes - COALESCE(a.current_practicantes, 0) AS remaining_practicantes,
    CASE
        WHEN c.allowed_practicantes = 0 THEN NULL
        ELSE CAST(COALESCE(a.current_practicantes, 0) AS DECIMAL(18,4))
             / CAST(c.allowed_practicantes AS DECIMAL(18,4))
    END AS utilization_pct,
    CASE
        WHEN COALESCE(a.current_practicantes, 0) > c.allowed_practicantes THEN 'Over capacity'
        WHEN c.allowed_practicantes - COALESCE(a.current_practicantes, 0) <= 5 THEN 'Near full'
        ELSE 'Available'
    END AS capacity_status
FROM vp_capacity c
LEFT JOIN active_counts a
    ON a.vp_key = c.vp_key;
GO
