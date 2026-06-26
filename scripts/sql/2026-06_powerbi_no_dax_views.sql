/*
Power BI Service-friendly reporting views.

These views avoid custom DAX measures by pre-aggregating the metrics HR needs.
Use them when building reports directly in the Power BI web editor.
*/

CREATE OR ALTER VIEW dbo.vw_powerbi_dashboard_kpis AS
SELECT
    COUNT(CASE WHEN s.is_active = 1 THEN 1 END) AS hc_activos,
    COUNT(CASE WHEN s.is_inactive = 1 THEN 1 END) AS hc_inactivos,
    COUNT(CASE WHEN s.is_active = 1 AND s.days_until_contract_end BETWEEN 0 AND 30 THEN 1 END) AS terminacion_30_dias,
    COUNT(CASE WHEN s.is_active = 1 AND s.is_contract_expired = 1 THEN 1 END) AS contratos_vencidos_activos,
    CAST(SUM(CASE WHEN s.is_active = 1 THEN COALESCE(s.importe_total, 0) ELSE 0 END) AS DECIMAL(18,2)) AS importe_total_activos,
    CAST(AVG(CASE WHEN s.is_active = 1 THEN s.importe_total END) AS DECIMAL(18,2)) AS importe_promedio_activos,
    (SELECT COUNT(*) FROM dbo.vw_powerbi_vacantes) AS vacantes_abiertas,
    (
        SELECT COUNT(DISTINCT mi.intern_id)
        FROM dbo.fact_intern_missing_items mi
        WHERE mi.status = 'Open'
          AND mi.missing_type = 'Document'
          AND mi.intern_id IS NOT NULL
    ) AS practicantes_con_docs_faltantes,
    (
        SELECT COUNT(*)
        FROM dbo.vw_business_validation_exceptions
    ) AS excepciones_abiertas,
    (
        SELECT SUM(CASE WHEN remaining_practicantes > 0 THEN remaining_practicantes ELSE 0 END)
        FROM dbo.vw_powerbi_vp_capacity
    ) AS espacios_disponibles_vp,
    SYSUTCDATETIME() AS refreshed_at_utc
FROM dbo.vw_powerbi_interns_status s;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_vp_summary AS
WITH missing_docs AS (
    SELECT
        s.vp,
        COUNT(DISTINCT mi.intern_id) AS practicantes_con_docs_faltantes
    FROM dbo.fact_intern_missing_items mi
    INNER JOIN dbo.vw_powerbi_interns_status s
        ON mi.intern_id = s.intern_id
    WHERE mi.status = 'Open'
      AND mi.missing_type = 'Document'
    GROUP BY s.vp
),
exceptions AS (
    SELECT
        vp,
        COUNT(*) AS excepciones_abiertas
    FROM dbo.vw_business_validation_exceptions
    GROUP BY vp
),
intern_counts AS (
    SELECT
        vp,
        COUNT(CASE WHEN is_active = 1 THEN 1 END) AS hc_activos,
        COUNT(CASE WHEN is_inactive = 1 THEN 1 END) AS hc_inactivos,
        COUNT(CASE WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN 1 END) AS terminacion_30_dias,
        COUNT(CASE WHEN is_active = 1 AND is_contract_expired = 1 THEN 1 END) AS contratos_vencidos_activos,
        CAST(SUM(CASE WHEN is_active = 1 THEN COALESCE(importe_total, 0) ELSE 0 END) AS DECIMAL(18,2)) AS importe_total_activos,
        CAST(AVG(CASE WHEN is_active = 1 THEN importe_total END) AS DECIMAL(18,2)) AS importe_promedio_activos
    FROM dbo.vw_powerbi_interns_status
    GROUP BY vp
)
SELECT
    COALESCE(c.vp, i.vp) AS vp,
    COALESCE(c.allowed_practicantes, 0) AS allowed_practicantes,
    COALESCE(c.current_practicantes, i.hc_activos, 0) AS current_practicantes,
    COALESCE(c.remaining_practicantes, 0) AS remaining_practicantes,
    c.utilization_pct,
    COALESCE(c.capacity_status, 'No capacity configured') AS capacity_status,
    COALESCE(i.hc_activos, 0) AS hc_activos,
    COALESCE(i.hc_inactivos, 0) AS hc_inactivos,
    COALESCE(i.terminacion_30_dias, 0) AS terminacion_30_dias,
    COALESCE(i.contratos_vencidos_activos, 0) AS contratos_vencidos_activos,
    COALESCE(i.importe_total_activos, 0) AS importe_total_activos,
    i.importe_promedio_activos,
    COALESCE(md.practicantes_con_docs_faltantes, 0) AS practicantes_con_docs_faltantes,
    COALESCE(e.excepciones_abiertas, 0) AS excepciones_abiertas
FROM dbo.vw_powerbi_vp_capacity c
FULL OUTER JOIN intern_counts i
    ON UPPER(LTRIM(RTRIM(COALESCE(c.vp, '')))) = UPPER(LTRIM(RTRIM(COALESCE(i.vp, ''))))
LEFT JOIN missing_docs md
    ON UPPER(LTRIM(RTRIM(COALESCE(md.vp, '')))) = UPPER(LTRIM(RTRIM(COALESCE(COALESCE(c.vp, i.vp), ''))))
LEFT JOIN exceptions e
    ON UPPER(LTRIM(RTRIM(COALESCE(e.vp, '')))) = UPPER(LTRIM(RTRIM(COALESCE(COALESCE(c.vp, i.vp), ''))));
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_location_summary AS
SELECT
    ubicacion_hc,
    estado_ubicacion_hc,
    cia_hc,
    vp,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) AS hc_activos,
    COUNT(CASE WHEN is_inactive = 1 THEN 1 END) AS hc_inactivos,
    COUNT(CASE WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN 1 END) AS terminacion_30_dias,
    COUNT(CASE WHEN is_active = 1 AND is_contract_expired = 1 THEN 1 END) AS contratos_vencidos_activos,
    CAST(SUM(CASE WHEN is_active = 1 THEN COALESCE(importe_total, 0) ELSE 0 END) AS DECIMAL(18,2)) AS importe_total_activos,
    CAST(AVG(CASE WHEN is_active = 1 THEN importe_total END) AS DECIMAL(18,2)) AS importe_promedio_activos
FROM dbo.vw_powerbi_interns_status
GROUP BY ubicacion_hc, estado_ubicacion_hc, cia_hc, vp;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_contract_risk AS
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
    days_until_contract_end,
    raw_status,
    is_active,
    is_inactive,
    is_contract_expired,
    CASE
        WHEN is_active = 1 AND is_contract_expired = 1 THEN '01 Vencido activo'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN '02 Termina 0-30 dias'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 31 AND 60 THEN '03 Termina 31-60 dias'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 61 AND 90 THEN '04 Termina 61-90 dias'
        WHEN is_active = 1 AND contract_end_date IS NULL THEN '05 Sin fecha de termino'
        WHEN is_active = 1 THEN '06 Sin riesgo cercano'
        WHEN is_inactive = 1 THEN '07 Inactivo'
        ELSE '08 Otro status'
    END AS risk_bucket,
    CASE
        WHEN is_active = 1 AND is_contract_expired = 1 THEN 'Actualizar baja/extension'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN 'Confirmar extension o baja'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 31 AND 90 THEN 'Monitorear vencimiento'
        WHEN is_active = 1 AND contract_end_date IS NULL THEN 'Capturar fecha de termino'
        ELSE 'Sin accion inmediata'
    END AS next_action
FROM dbo.vw_powerbi_interns_status;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_document_status AS
WITH missing_items AS (
    SELECT
        mi.intern_id,
        mi.process_type_id,
        mi.missing_code AS document_code,
        mi.missing_description AS document_name,
        mi.severity,
        mi.status,
        mi.created_at,
        mi.resolved_at,
        mi.missing_item_id
    FROM dbo.fact_intern_missing_items mi
    WHERE mi.missing_type = 'Document'
),
document_rows AS (
    SELECT
        cd.source_table,
        cd.canonical_document_id,
        cd.intern_id,
        cd.process_type_id,
        cd.stage,
        cd.document_code,
        cd.document_name,
        cd.file_name,
        cd.blob_path,
        cd.status,
        cd.validation_status,
        cd.is_required,
        cd.is_missing,
        cd.is_expired,
        cd.expires_at,
        cd.reviewed_at,
        cd.notes,
        cd.created_at,
        cd.updated_at,
        CAST(NULL AS NVARCHAR(50)) AS missing_item_id,
        CAST(NULL AS NVARCHAR(50)) AS severity,
        CAST(NULL AS DATETIME2) AS resolved_at
    FROM dbo.vw_canonical_intern_documents cd
    UNION ALL
    SELECT
        'fact_intern_missing_items' AS source_table,
        mi.missing_item_id AS canonical_document_id,
        mi.intern_id,
        mi.process_type_id,
        CAST(NULL AS NVARCHAR(30)) AS stage,
        mi.document_code,
        mi.document_name,
        CAST(NULL AS NVARCHAR(300)) AS file_name,
        CAST(NULL AS NVARCHAR(400)) AS blob_path,
        mi.status,
        CAST(NULL AS NVARCHAR(100)) AS validation_status,
        CAST(1 AS BIT) AS is_required,
        CASE WHEN mi.status = 'Open' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_missing,
        CAST(0 AS BIT) AS is_expired,
        CAST(NULL AS DATETIME2) AS expires_at,
        CAST(NULL AS DATETIME2) AS reviewed_at,
        mi.document_name AS notes,
        mi.created_at,
        CAST(NULL AS DATETIME2) AS updated_at,
        mi.missing_item_id,
        mi.severity,
        mi.resolved_at
    FROM missing_items mi
)
SELECT
    dr.source_table,
    dr.canonical_document_id,
    dr.intern_id,
    s.intern_name,
    s.employee_number,
    s.cemex_employee_number,
    s.manager,
    s.vp,
    s.ubicacion_hc,
    s.estado_ubicacion_hc,
    s.cia_hc,
    s.oi_hc,
    s.cc_hc,
    dr.process_type_id,
    dr.stage,
    dr.document_code,
    dr.document_name,
    dr.file_name,
    dr.blob_path,
    dr.status,
    dr.validation_status,
    dr.is_required,
    dr.is_missing,
    dr.is_expired,
    dr.severity,
    dr.expires_at,
    dr.reviewed_at,
    dr.resolved_at,
    dr.notes,
    dr.created_at,
    dr.updated_at,
    CASE
        WHEN dr.is_missing = 1 THEN 'Faltante'
        WHEN dr.is_expired = 1 THEN 'Vencido'
        WHEN dr.validation_status IN ('Needs Review', 'Validation Failed') THEN 'Revision'
        WHEN dr.status IN ('Stored', 'Validated', 'Received') THEN 'Recibido'
        ELSE COALESCE(dr.status, 'Sin status')
    END AS document_status_label,
    CASE
        WHEN dr.is_missing = 1 THEN 'Solicitar documento'
        WHEN dr.is_expired = 1 THEN 'Solicitar documento actualizado'
        WHEN dr.validation_status IN ('Needs Review', 'Validation Failed') THEN 'Revisar documento'
        ELSE 'Sin accion inmediata'
    END AS next_action
FROM document_rows dr
LEFT JOIN dbo.vw_powerbi_interns_status s
    ON dr.intern_id = s.intern_id;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_document_summary AS
SELECT
    document_code,
    document_name,
    document_status_label,
    vp,
    COUNT(*) AS document_rows,
    COUNT(DISTINCT intern_id) AS practicante_count,
    COUNT(CASE WHEN is_missing = 1 THEN 1 END) AS missing_rows,
    COUNT(CASE WHEN is_expired = 1 THEN 1 END) AS expired_rows,
    COUNT(CASE WHEN validation_status IN ('Needs Review', 'Validation Failed') THEN 1 END) AS needs_review_rows
FROM dbo.vw_powerbi_document_status
GROUP BY document_code, document_name, document_status_label, vp;
GO

CREATE OR ALTER VIEW dbo.vw_powerbi_hr_action_queue AS
SELECT
    action_category,
    intern_id,
    intern_name,
    vp,
    area,
    manager,
    action_description,
    severity,
    action_created_at,
    next_action
FROM dbo.vw_hr_actions_today
UNION ALL
SELECT
    'Contract Risk' AS action_category,
    intern_id,
    intern_name,
    vp,
    CAST(NULL AS NVARCHAR(255)) AS area,
    manager,
    CONCAT(risk_bucket, ': ', COALESCE(CONVERT(NVARCHAR(30), contract_end_date, 23), 'sin fecha')) AS action_description,
    CASE
        WHEN risk_bucket = '01 Vencido activo' THEN 'Error'
        WHEN risk_bucket IN ('02 Termina 0-30 dias', '05 Sin fecha de termino') THEN 'Warning'
        ELSE 'Info'
    END AS severity,
    SYSUTCDATETIME() AS action_created_at,
    next_action
FROM dbo.vw_powerbi_contract_risk
WHERE risk_bucket IN ('01 Vencido activo', '02 Termina 0-30 dias', '05 Sin fecha de termino');
GO
