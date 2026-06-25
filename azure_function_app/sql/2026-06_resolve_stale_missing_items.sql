/*
Resolve stale missing-item warnings after enrichment/backfill.

These updates only close open missing items when the current canonical intern
record now has the value that the missing item complained about.
*/

UPDATE mi
SET
    status = 'Resolved',
    resolved_at = COALESCE(mi.resolved_at, SYSUTCDATETIME()),
    missing_description = CONCAT(mi.missing_description, ' Resolved automatically because current intern data now has OI HC.')
FROM dbo.fact_intern_missing_items mi
INNER JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open'
  AND mi.missing_code = 'OI_HC'
  AND i.oi_hc IS NOT NULL
  AND LTRIM(RTRIM(i.oi_hc)) <> '';
GO

UPDATE mi
SET
    status = 'Resolved',
    resolved_at = COALESCE(mi.resolved_at, SYSUTCDATETIME()),
    missing_description = CONCAT(mi.missing_description, ' Resolved automatically because current intern data now has CC HC.')
FROM dbo.fact_intern_missing_items mi
INNER JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open'
  AND mi.missing_code = 'CC_HC'
  AND i.cc_hc IS NOT NULL
  AND LTRIM(RTRIM(i.cc_hc)) <> '';
GO

UPDATE mi
SET
    status = 'Resolved',
    resolved_at = COALESCE(mi.resolved_at, SYSUTCDATETIME()),
    missing_description = CONCAT(mi.missing_description, ' Resolved automatically because current intern data now has VP HC.')
FROM dbo.fact_intern_missing_items mi
INNER JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open'
  AND mi.missing_code = 'VP_HC'
  AND i.vp_hc IS NOT NULL
  AND LTRIM(RTRIM(i.vp_hc)) <> '';
GO

UPDATE mi
SET
    status = 'Resolved',
    resolved_at = COALESCE(mi.resolved_at, SYSUTCDATETIME()),
    missing_description = CONCAT(mi.missing_description, ' Resolved automatically because current intern data now has CIA HC.')
FROM dbo.fact_intern_missing_items mi
INNER JOIN dbo.dim_interns i
    ON mi.intern_id = i.intern_id
WHERE mi.status = 'Open'
  AND mi.missing_code = 'CIA_HC'
  AND i.cia_hc IS NOT NULL
  AND LTRIM(RTRIM(i.cia_hc)) <> '';
GO
