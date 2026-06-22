IF OBJECT_ID('dbo.fact_entity_matches', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_entity_matches (
        entity_match_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        run_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        source_file_id NVARCHAR(50) NULL,
        source_row_number INT NULL,
        source_entity_type NVARCHAR(100) NULL,
        matched_entity_type NVARCHAR(100) NULL,
        matched_entity_id NVARCHAR(100) NULL,
        match_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
        match_confidence NVARCHAR(50) NOT NULL,
        match_method NVARCHAR(255) NULL,
        evidence_used NVARCHAR(MAX) NULL,
        alternative_matches NVARCHAR(MAX) NULL,
        needs_review BIT NOT NULL DEFAULT 1,
        conflict_reason NVARCHAR(MAX) NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'Proposed',
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.fact_match_candidates', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_match_candidates (
        match_candidate_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        entity_match_id NVARCHAR(50) NULL,
        candidate_rank INT NULL,
        candidate_entity_type NVARCHAR(100) NULL,
        candidate_entity_id NVARCHAR(100) NULL,
        candidate_score DECIMAL(5, 2) NOT NULL DEFAULT 0,
        candidate_confidence NVARCHAR(50) NOT NULL,
        match_method NVARCHAR(255) NULL,
        evidence_used NVARCHAR(MAX) NULL,
        conflict_reason NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_match_conflicts', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_match_conflicts (
        match_conflict_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        entity_match_id NVARCHAR(50) NULL,
        run_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        source_file_id NVARCHAR(50) NULL,
        source_row_number INT NULL,
        conflict_type NVARCHAR(100) NOT NULL,
        source_entity_type NVARCHAR(100) NULL,
        conflicting_entity_type NVARCHAR(100) NULL,
        conflicting_entity_id NVARCHAR(100) NULL,
        conflict_reason NVARCHAR(MAX) NOT NULL,
        evidence_used NVARCHAR(MAX) NULL,
        severity NVARCHAR(50) NOT NULL DEFAULT 'Error',
        status NVARCHAR(50) NOT NULL DEFAULT 'Open',
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        resolved_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.fact_entity_matches', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.fact_entity_matches', 'source_file_id') IS NULL ALTER TABLE dbo.fact_entity_matches ADD source_file_id NVARCHAR(50) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'source_row_number') IS NULL ALTER TABLE dbo.fact_entity_matches ADD source_row_number INT NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'source_entity_type') IS NULL ALTER TABLE dbo.fact_entity_matches ADD source_entity_type NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'matched_entity_type') IS NULL ALTER TABLE dbo.fact_entity_matches ADD matched_entity_type NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'matched_entity_id') IS NULL ALTER TABLE dbo.fact_entity_matches ADD matched_entity_id NVARCHAR(100) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'evidence_used') IS NULL ALTER TABLE dbo.fact_entity_matches ADD evidence_used NVARCHAR(MAX) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'alternative_matches') IS NULL ALTER TABLE dbo.fact_entity_matches ADD alternative_matches NVARCHAR(MAX) NULL;
    IF COL_LENGTH('dbo.fact_entity_matches', 'needs_review') IS NULL ALTER TABLE dbo.fact_entity_matches ADD needs_review BIT NOT NULL DEFAULT 1;
    IF COL_LENGTH('dbo.fact_entity_matches', 'conflict_reason') IS NULL ALTER TABLE dbo.fact_entity_matches ADD conflict_reason NVARCHAR(MAX) NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_fact_entity_matches_review'
      AND object_id = OBJECT_ID('dbo.fact_entity_matches')
)
BEGIN
    CREATE INDEX IX_fact_entity_matches_review
        ON dbo.fact_entity_matches (needs_review, match_confidence, matched_entity_type, created_at);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_fact_match_conflicts_status'
      AND object_id = OBJECT_ID('dbo.fact_match_conflicts')
)
BEGIN
    CREATE INDEX IX_fact_match_conflicts_status
        ON dbo.fact_match_conflicts (status, severity, created_at);
END;
GO

CREATE OR ALTER VIEW dbo.vw_matching_engine_review_queue AS
SELECT
    em.entity_match_id,
    em.run_id,
    COALESCE(em.source_file_id, em.file_id) AS file_id,
    em.source_row_number,
    em.source_entity_type,
    em.matched_entity_type,
    em.matched_entity_id,
    em.match_score,
    em.match_confidence,
    em.match_method,
    em.needs_review,
    em.conflict_reason,
    em.status,
    em.created_at
FROM dbo.fact_entity_matches em
WHERE em.needs_review = 1
   OR em.match_confidence IN ('MEDIUM', 'LOW', 'CONFLICT');
GO

CREATE OR ALTER VIEW dbo.vw_matching_engine_conflicts AS
SELECT
    mc.match_conflict_id,
    mc.entity_match_id,
    mc.run_id,
    COALESCE(mc.source_file_id, mc.file_id) AS file_id,
    mc.source_row_number,
    mc.conflict_type,
    mc.source_entity_type,
    mc.conflicting_entity_type,
    mc.conflicting_entity_id,
    mc.conflict_reason,
    mc.severity,
    mc.status,
    mc.created_at,
    mc.resolved_at
FROM dbo.fact_match_conflicts mc
WHERE mc.status = 'Open';
GO
