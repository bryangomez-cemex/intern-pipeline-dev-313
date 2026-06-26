/*
Open positions list ingestion (2026-06).

A "lista de posiciones actualmente abiertas" is NOT a requisition: it is the
current snapshot of open vacancies with recruiting status. Columns:
  #, Vacante, ID Vacante, Ubicacion, Promedio Dias Abierto, Responsable, AIRH,
  Jefe del Puesto, Estatus General

Each upload replaces the current snapshot (is_current = 1). Idempotent.
*/

IF OBJECT_ID('dbo.dim_open_positions', 'U') IS NULL
    CREATE TABLE dbo.dim_open_positions (
        position_row_id        NVARCHAR(50)  NOT NULL PRIMARY KEY,
        numero                 INT           NULL,
        vacante                NVARCHAR(300) NULL,
        id_vacante             NVARCHAR(50)  NULL,
        ubicacion              NVARCHAR(200) NULL,
        promedio_dias_abierto  INT           NULL,
        responsable            NVARCHAR(200) NULL,
        airh                   NVARCHAR(200) NULL,
        jefe_puesto            NVARCHAR(200) NULL,
        estatus_general        NVARCHAR(200) NULL,
        is_current             BIT           NOT NULL DEFAULT 1,
        source_blob            NVARCHAR(400) NULL,
        updated_at             DATETIME2     DEFAULT SYSUTCDATETIME()
    );
GO

-- Power BI view: currently open positions (Spanish values straight from the list).
CREATE OR ALTER VIEW dbo.vw_powerbi_posiciones_abiertas AS
SELECT
    numero,
    vacante,
    id_vacante,
    ubicacion,
    promedio_dias_abierto,
    responsable,
    airh,
    jefe_puesto,
    estatus_general,
    updated_at
FROM dbo.dim_open_positions
WHERE is_current = 1;
GO
