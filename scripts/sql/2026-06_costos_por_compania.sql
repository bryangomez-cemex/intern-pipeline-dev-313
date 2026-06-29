/*
Costos por compania (2026-06).

"Costos por compania" = total company cost (ImporteTotal) grouped by RAZON SOCIAL HC
(the legal company name, e.g. "SERVICIOS PROFESIONALES CEMEX, S.A. DE C.V."), which
is distinct from CIA HC (a company code). Store RAZON SOCIAL HC on dim_interns and
report cost by it. Idempotent.
*/

IF COL_LENGTH('dbo.dim_interns', 'razon_social_hc') IS NULL
    ALTER TABLE dbo.dim_interns ADD razon_social_hc NVARCHAR(300) NULL;
GO

-- Costs grouped by company (razon social). Uses the real importe_total (company cost)
-- and importe (intern pay) from vw_powerbi_interns_status.
CREATE OR ALTER VIEW dbo.vw_powerbi_costos_por_compania AS
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(i.razon_social_hc)), ''), 'Sin compania') AS razon_social,
    COUNT(*) AS practicante_count,
    SUM(COALESCE(s.importe, 0)) AS importe_pagado_sum,
    SUM(COALESCE(s.importe_total, 0)) AS importe_total_sum,
    AVG(COALESCE(s.importe_total, 0)) AS importe_total_avg,
    MIN(s.importe_total) AS importe_total_min,
    MAX(s.importe_total) AS importe_total_max
FROM dbo.vw_powerbi_interns_status s
JOIN dbo.dim_interns i
    ON s.intern_id = i.intern_id
WHERE s.is_active = 1
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(i.razon_social_hc)), ''), 'Sin compania');
GO
