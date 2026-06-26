/*
Cost model (2026-06).

The roster carries two distinct amounts:
  - Importe (= ImporteSinComision) = lo que se paga al practicante (intern pay).
  - ImporteTotal = costo total para la compania (intern pay x comision factor).

Store both on dim_interns and report them separately. `importe_total` in the
Power BI views now uses the real ImporteTotal (falling back to the salary-derived
value only for rows not yet re-synced). Idempotent.
*/

IF COL_LENGTH('dbo.dim_interns', 'importe') IS NULL
    ALTER TABLE dbo.dim_interns ADD importe NVARCHAR(50) NULL;
GO
IF COL_LENGTH('dbo.dim_interns', 'importe_total') IS NULL
    ALTER TABLE dbo.dim_interns ADD importe_total NVARCHAR(50) NULL;
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
        i.importe AS importe_raw,
        i.importe_total AS importe_total_raw,
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
    -- Intern pay (lo que se paga al practicante) = Importe / ImporteSinComision.
    -- Fall back to salario_mensual for rows not yet re-synced with the cost columns.
    COALESCE(
        TRY_CONVERT(DECIMAL(18,2),
            REPLACE(REPLACE(REPLACE(CAST(importe_raw AS NVARCHAR(100)), '$', ''), ',', ''), ' ', '')),
        TRY_CONVERT(DECIMAL(18,2),
            REPLACE(REPLACE(REPLACE(CAST(salario_mensual AS NVARCHAR(100)), '$', ''), ',', ''), ' ', ''))
    ) AS importe,
    -- Total company cost = ImporteTotal. For rows not yet re-synced with the cost
    -- columns, approximate it as salary x the comision factor (1.1 in the roster);
    -- the exact value lands once the full roster is re-uploaded.
    COALESCE(
        TRY_CONVERT(DECIMAL(18,2),
            REPLACE(REPLACE(REPLACE(CAST(importe_total_raw AS NVARCHAR(100)), '$', ''), ',', ''), ' ', '')),
        TRY_CONVERT(DECIMAL(18,2),
            REPLACE(REPLACE(REPLACE(CAST(salario_mensual AS NVARCHAR(100)), '$', ''), ',', ''), ' ', '')) * 1.1
    ) AS importe_total
FROM base;
GO

-- Costos: expose both the intern pay and the total company cost.
CREATE OR ALTER VIEW dbo.vw_powerbi_costos_practicantes AS
SELECT
    vp,
    ubicacion_hc,
    estado_ubicacion_hc,
    cia_hc,
    COUNT(*) AS practicante_count,
    SUM(COALESCE(importe, 0)) AS importe_pagado_sum,
    AVG(COALESCE(importe, 0)) AS importe_pagado_avg,
    SUM(COALESCE(importe_total, 0)) AS importe_total_sum,
    AVG(COALESCE(importe_total, 0)) AS importe_total_avg,
    MIN(importe_total) AS importe_total_min,
    MAX(importe_total) AS importe_total_max
FROM dbo.vw_powerbi_interns_status
WHERE is_active = 1
GROUP BY vp, ubicacion_hc, estado_ubicacion_hc, cia_hc;
GO
