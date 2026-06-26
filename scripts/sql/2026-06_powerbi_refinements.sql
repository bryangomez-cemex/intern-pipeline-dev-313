/*
Power BI refinements (2026-06).

- capacity_status as a numeric percentage (not strings).
- contract_risk risk_bucket without numeric prefixes; inactivos -> "Realizar baja".
- exceptions carry a resolution state: data/field gaps the matching rules fill are
  reported as "Resuelta automaticamente"; only real blockers stay "Pendiente".
- graduated, Spanish severities (Critica/Alta/Media/Baja) instead of a single level.
- short, useful Spanish suggestions; all Power BI VALUES in Spanish.

Idempotent (CREATE OR ALTER). Views are ordered by dependency: the exceptions view
(which gains the `estado` column) is created before the views that reference it.
Apply after create_business_powerbi_views.sql and 2026-06_powerbi_no_dax_views.sql.
*/

-- ============================================================
-- 1. VP capacity: capacity_status becomes an integer percentage (0..N).
-- ============================================================
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
    -- capacity_status as a whole-number percentage (e.g. 75 = 75% ocupado).
    CASE
        WHEN c.allowed_practicantes = 0 THEN NULL
        ELSE CAST(ROUND(CAST(COALESCE(a.current_practicantes, 0) AS DECIMAL(18,4))
             / CAST(c.allowed_practicantes AS DECIMAL(18,4)) * 100, 0) AS INT)
    END AS capacity_status
FROM vp_capacity c
LEFT JOIN active_counts a
    ON a.vp_key = c.vp_key;
GO

-- ============================================================
-- 2. Business exceptions (created early: gains the `estado` column other views
--    reference). Spanish, graduated severity, resolution state, useful tips.
--    Data/field gaps the matching rules close are reported as resolved; documents
--    and contract issues stay pending.
-- ============================================================
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
    'Validacion de datos' AS issue_type,
    CASE
        WHEN v.validation_result = 'Failed' AND v.severity = 'Error' THEN 'Critica'
        WHEN v.severity = 'Error' THEN 'Alta'
        WHEN v.severity = 'Warning' THEN 'Media'
        ELSE 'Baja'
    END AS severity,
    v.validation_result AS issue_status,
    v.error_message AS issue_description,
    CASE
        WHEN v.validation_result = 'Failed'
            THEN 'Corregir ' + COALESCE(v.field_name, 'el dato') + ' en el archivo de origen y reenviar.'
        ELSE 'Sin accion: el sistema completo el dato por reglas de matching.'
    END AS suggested_fix,
    v.created_at,
    'Validacion' AS exception_source,
    CASE WHEN v.validation_result = 'Failed' THEN 'Pendiente'
         ELSE 'Resuelta automaticamente' END AS estado,
    CASE WHEN v.validation_result = 'Failed' THEN 'Corregir y reenviar'
         ELSE 'Sin accion' END AS next_action
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
    CASE
        WHEN mi.missing_type = 'Document' THEN 'Documento faltante'
        WHEN mi.missing_type = 'Validation' THEN 'Riesgo de contrato'
        WHEN mi.missing_type = 'BusinessRule' THEN 'Campo incompleto'
        ELSE 'Otra excepcion'
    END AS issue_type,
    CASE
        WHEN mi.missing_type = 'Validation' AND mi.missing_description LIKE '%expired%' THEN 'Critica'
        WHEN mi.missing_type = 'Validation' THEN 'Alta'
        WHEN mi.missing_type = 'Document' THEN 'Alta'
        WHEN mi.missing_type = 'BusinessRule' THEN 'Baja'
        ELSE 'Media'
    END AS severity,
    mi.status AS issue_status,
    CASE
        WHEN mi.missing_description LIKE 'Missing %' THEN 'Falta ' + SUBSTRING(mi.missing_description, 9, 200)
        WHEN mi.missing_description LIKE '%expired end date%' THEN 'Practicante activo con fecha de termino vencida.'
        WHEN mi.missing_description LIKE '%within 30 days%' THEN 'La fecha de termino vence en menos de 30 dias.'
        ELSE mi.missing_description
    END AS issue_description,
    CASE
        WHEN mi.missing_type = 'Document'
            THEN 'Solicitar al practicante el documento indicado.'
        WHEN mi.missing_type = 'Validation' AND mi.missing_description LIKE '%expired%'
            THEN 'Contrato vencido y activo: realizar baja o registrar la extension.'
        WHEN mi.missing_type = 'Validation'
            THEN 'Contrato por vencer: confirmar extension o baja con el area.'
        WHEN mi.missing_type = 'BusinessRule'
            THEN 'Sin accion: el sistema completo el campo por reglas de matching.'
        ELSE 'Revisar la excepcion en el expediente.'
    END AS suggested_fix,
    mi.created_at,
    'Item faltante' AS exception_source,
    CASE WHEN mi.missing_type = 'BusinessRule' THEN 'Resuelta automaticamente'
         ELSE 'Pendiente' END AS estado,
    CASE
        WHEN mi.missing_type = 'Document' THEN 'Solicitar documento'
        WHEN mi.missing_type = 'Validation' AND mi.missing_description LIKE '%expired%' THEN 'Realizar baja o extension'
        WHEN mi.missing_type = 'Validation' THEN 'Confirmar extension o baja'
        WHEN mi.missing_type = 'BusinessRule' THEN 'Sin accion'
        ELSE 'Revisar'
    END AS next_action
FROM dbo.fact_intern_missing_items mi
LEFT JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open';
GO

-- ============================================================
-- 3. VP summary: capacity_status is now numeric -> COALESCE to 0, not a string;
--    open exceptions count only the still-pending ones.
-- ============================================================
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
    WHERE estado = 'Pendiente'
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
    COALESCE(c.capacity_status, 0) AS capacity_status,
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

-- ============================================================
-- 4. Contract risk: de-enumerated, Spanish buckets; inactivos -> "Realizar baja".
-- ============================================================
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
        WHEN is_active = 1 AND is_contract_expired = 1 THEN 'Vencido activo'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN 'Termina en 0-30 dias'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 31 AND 60 THEN 'Termina en 31-60 dias'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 61 AND 90 THEN 'Termina en 61-90 dias'
        WHEN is_active = 1 AND contract_end_date IS NULL THEN 'Sin fecha de termino'
        WHEN is_active = 1 THEN 'Sin riesgo cercano'
        WHEN is_inactive = 1 THEN 'Inactivo'
        ELSE 'Otro estatus'
    END AS risk_bucket,
    CASE
        WHEN is_active = 1 AND is_contract_expired = 1 THEN 'Actualizar baja o extension'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 0 AND 30 THEN 'Confirmar extension o baja'
        WHEN is_active = 1 AND days_until_contract_end BETWEEN 31 AND 90 THEN 'Monitorear vencimiento'
        WHEN is_active = 1 AND contract_end_date IS NULL THEN 'Capturar fecha de termino'
        WHEN is_inactive = 1 THEN 'Realizar baja'
        ELSE 'Sin accion inmediata'
    END AS next_action
FROM dbo.vw_powerbi_interns_status;
GO

-- ============================================================
-- 5. HR actions today: Spanish category / severity / action, graduated levels.
-- ============================================================
CREATE OR ALTER VIEW dbo.vw_hr_actions_today AS
SELECT
    'Documento o dato faltante' AS action_category,
    intern_id, intern_name, vp, area, manager,
    missing_description AS action_description,
    CASE WHEN severity = 'Error' THEN 'Alta' WHEN severity = 'Warning' THEN 'Media' ELSE 'Baja' END AS severity,
    created_at AS action_created_at,
    'Solicitar documento o completar dato' AS next_action
FROM dbo.vw_full_mvp_missing_items
WHERE status = 'Open'
UNION ALL
SELECT
    'Excepcion de datos' AS action_category,
    intern_id, intern_name, vp, area, manager,
    issue_description AS action_description,
    severity,
    created_at AS action_created_at,
    next_action
FROM dbo.vw_business_validation_exceptions
WHERE estado = 'Pendiente'
UNION ALL
SELECT
    'Vencimiento de contrato' AS action_category,
    intern_id, intern_name, vp, area, manager,
    CONCAT('El contrato/convenio vence en ', days_until_contract_end, ' dias.') AS action_description,
    'Alta' AS severity,
    SYSUTCDATETIME() AS action_created_at,
    'Confirmar extension o baja' AS next_action
FROM dbo.vw_interns_current
WHERE is_expiring_soon = 1
UNION ALL
SELECT
    'Comunicacion' AS action_category,
    NULL AS intern_id, NULL AS intern_name, NULL AS vp, NULL AS area, NULL AS manager,
    subject AS action_description,
    'Baja' AS severity,
    created_at AS action_created_at,
    'Revisar comunicacion' AS next_action
FROM dbo.vw_communications_status
WHERE next_action <> 'No action';
GO

-- ============================================================
-- 6. HR action queue: Spanish category and severity; new risk_bucket values.
-- ============================================================
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
    'Riesgo de contrato' AS action_category,
    intern_id,
    intern_name,
    vp,
    CAST(NULL AS NVARCHAR(255)) AS area,
    manager,
    CONCAT(risk_bucket, ': ', COALESCE(CONVERT(NVARCHAR(30), contract_end_date, 23), 'sin fecha')) AS action_description,
    CASE
        WHEN risk_bucket = 'Vencido activo' THEN 'Critica'
        WHEN risk_bucket IN ('Termina en 0-30 dias', 'Sin fecha de termino') THEN 'Alta'
        ELSE 'Media'
    END AS severity,
    SYSUTCDATETIME() AS action_created_at,
    next_action
FROM dbo.vw_powerbi_contract_risk
WHERE risk_bucket IN ('Vencido activo', 'Termina en 0-30 dias', 'Sin fecha de termino');
GO

-- ============================================================
-- 7. Dashboard KPIs: open exceptions counts only the still-pending ones, and
--    expose how many were auto-resolved by the matching rules.
-- ============================================================
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
        WHERE estado = 'Pendiente'
    ) AS excepciones_abiertas,
    (
        SELECT COUNT(*)
        FROM dbo.vw_business_validation_exceptions
        WHERE estado = 'Resuelta automaticamente'
    ) AS excepciones_resueltas,
    (
        SELECT SUM(CASE WHEN remaining_practicantes > 0 THEN remaining_practicantes ELSE 0 END)
        FROM dbo.vw_powerbi_vp_capacity
    ) AS espacios_disponibles_vp,
    SYSUTCDATETIME() AS refreshed_at_utc
FROM dbo.vw_powerbi_interns_status s;
GO
